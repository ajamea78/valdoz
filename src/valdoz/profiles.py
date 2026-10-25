"""ValdoZ Profiles Engine: Multi-Account Git & GitHub Identity Management.

Manages:
- Global developer profile registry (~/.valdoz/profiles.json)
- Per-project profile binding and local git configuration enforcement
- Git credential isolation via credential.useHttpPath
- SSH key scoping per profile
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field


class Profile(BaseModel):
    name: str
    email: str
    github_username: Optional[str] = None
    ssh_key: Optional[str] = None
    signing_key: Optional[str] = None


class ProfilesConfig(BaseModel):
    default: Optional[str] = None
    profiles: Dict[str, Profile] = Field(default_factory=dict)


def get_profiles_path() -> Path:
    """Returns the path to profiles.json, respecting VALDOZ_PROFILES_PATH if set."""
    custom = os.environ.get("VALDOZ_PROFILES_PATH")
    if custom:
        return Path(custom).resolve()
    return Path.home() / ".valdoz" / "profiles.json"


def load_profiles() -> ProfilesConfig:
    """Loads profiles from ~/.valdoz/profiles.json or returns default empty config."""
    path = get_profiles_path()
    if not path.exists():
        return ProfilesConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProfilesConfig.model_validate(data)
    except Exception:
        return ProfilesConfig()


def save_profiles(config: ProfilesConfig) -> None:
    """Saves profiles to ~/.valdoz/profiles.json with secure directory creation."""
    path = get_profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")


def get_profile(profile_id: str) -> Optional[Profile]:
    """Retrieves a profile by key."""
    cfg = load_profiles()
    return cfg.profiles.get(profile_id)


def add_profile(profile_id: str, profile: Profile, set_default: bool = False) -> None:
    """Adds or updates a profile in the registry."""
    cfg = load_profiles()
    cfg.profiles[profile_id] = profile
    if set_default or not cfg.default:
        cfg.default = profile_id
    save_profiles(cfg)


def remove_profile(profile_id: str) -> bool:
    """Removes a profile from the registry."""
    cfg = load_profiles()
    if profile_id in cfg.profiles:
        del cfg.profiles[profile_id]
        if cfg.default == profile_id:
            cfg.default = next(iter(cfg.profiles.keys()), None)
        save_profiles(cfg)
        return True
    return False


def _run_git(args: list[str], cwd: Path) -> tuple[int, str]:
    """Helper to run git command safely."""
    res = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode, res.stdout.strip()


def get_repo_git_identity(project_root: Path) -> dict[str, Optional[str]]:
    """Inspects the local and global Git configuration for the repository."""
    info: dict[str, Optional[str]] = {
        "local_name": None,
        "local_email": None,
        "global_name": None,
        "global_email": None,
        "use_http_path": None,
        "ssh_command": None,
        "remote_origin": None,
    }

    _, local_name = _run_git(["config", "--local", "user.name"], project_root)
    _, local_email = _run_git(["config", "--local", "user.email"], project_root)
    _, global_name = _run_git(["config", "--global", "user.name"], project_root)
    _, global_email = _run_git(["config", "--global", "user.email"], project_root)
    _, use_http_path = _run_git(["config", "--local", "credential.useHttpPath"], project_root)
    _, ssh_command = _run_git(["config", "--local", "core.sshCommand"], project_root)
    _, remote_origin = _run_git(["config", "--get", "remote.origin.url"], project_root)

    info["local_name"] = local_name if local_name else None
    info["local_email"] = local_email if local_email else None
    info["global_name"] = global_name if global_name else None
    info["global_email"] = global_email if global_email else None
    info["use_http_path"] = use_http_path if use_http_path else None
    info["ssh_command"] = ssh_command if ssh_command else None
    info["remote_origin"] = remote_origin if remote_origin else None

    return info


def apply_profile_to_repo(project_root: Path, profile_id: str) -> Profile:
    """Applies a profile's Git configuration to the repository locally."""
    profile = get_profile(profile_id)
    if not profile:
        raise ValueError(f"Profile '{profile_id}' not found in registry.")

    git_dir = project_root / ".git"
    if not git_dir.exists():
        raise RuntimeError("Not a git repository (missing .git directory).")

    # 1. Author Name & Email (Local)
    _run_git(["config", "--local", "user.name", profile.name], project_root)
    _run_git(["config", "--local", "user.email", profile.email], project_root)

    # 2. HTTP Credential Isolation
    _run_git(["config", "--local", "credential.useHttpPath", "true"], project_root)

    # 3. SSH Command Scoping
    if profile.ssh_key:
        ssh_expanded = str(Path(profile.ssh_key).expanduser())
        _run_git(["config", "--local", "core.sshCommand", f"ssh -i {ssh_expanded} -o IdentitiesOnly=yes"], project_root)

    # 4. Signing Key (if configured)
    if profile.signing_key:
        _run_git(["config", "--local", "user.signingkey", profile.signing_key], project_root)
        _run_git(["config", "--local", "commit.gpgsign", "true"], project_root)

    return profile
