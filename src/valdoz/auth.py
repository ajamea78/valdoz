"""ValdoZ Project-Scoped Credential Vault Engine.

Provides strict, zero-global-pollution authentication isolation:
- Per-project Git credential helper: `credential.helper = store --file .valdoz/.git-credentials`
- Chmod 600 file permissions (owner read/write only)
- Defense-in-depth gitignore and untracked verification
- In-Antigravity credential configuration and inspection
"""

from __future__ import annotations

import os
import stat
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional


def get_project_vault_path(project_root: Path) -> Path:
    """Returns the path to the project's isolated credential vault."""
    return project_root / ".valdoz" / ".git-credentials"


def ensure_vault_gitignored(project_root: Path) -> bool:
    """Ensures .valdoz/.git-credentials is listed in .gitignore."""
    gitignore_path = project_root / ".gitignore"
    entry = ".valdoz/.git-credentials"

    content = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    lines = [line.strip() for line in content.splitlines()]

    if entry not in lines and ".valdoz/*" not in lines and ".valdoz/" not in lines:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write(f"{entry}\n")
        return True
    return False


def setup_project_vault(
    project_root: Path,
    username: str,
    token: str,
    host: str = "github.com",
) -> Path:
    """Sets up an isolated, project-scoped Git credential store."""
    git_dir = project_root / ".git"
    if not git_dir.exists():
        raise RuntimeError("Not a git repository (missing .git directory).")

    valdoz_dir = project_root / ".valdoz"
    valdoz_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ensure gitignored
    ensure_vault_gitignored(project_root)

    # 2. Reset local credential helper chain to override global ~/.gitconfig helpers
    vault_file = get_project_vault_path(project_root)
    rel_or_abs = str(vault_file.resolve())
    subprocess.run(["git", "config", "--local", "credential.helper", ""], cwd=project_root, check=True)
    subprocess.run(["git", "config", "--local", "--add", "credential.helper", f"store --file {rel_or_abs}"], cwd=project_root, check=True)
    subprocess.run(["git", "config", "--local", "credential.useHttpPath", "true"], cwd=project_root, check=True)

    # 3. Extract remote path if available (e.g. ajamea78/valdoz.git)
    res_url = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    remote_path = ""
    origin_url = res_url.stdout.strip()
    if origin_url:
        import re
        m = re.search(r"github\.com[:/](.+)$", origin_url)
        if m:
            remote_path = m.group(1).lstrip("/")

    clean_user = urllib.parse.quote(username.strip(), safe="")
    clean_token = urllib.parse.quote(token.strip(), safe="")
    clean_host = host.strip()

    # 4. Write isolated credential path variants
    lines = []
    if remote_path:
        lines.append(f"https://{clean_user}:{clean_token}@{clean_host}/{remote_path}")
        lines.append(f"https://{clean_token}@{clean_host}/{remote_path}")
    lines.append(f"https://{clean_user}:{clean_token}@{clean_host}")
    lines.append(f"https://{clean_token}@{clean_host}")
    vault_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 5. Lock permissions to 0o600 (owner read/write only)
    if vault_file.exists():
        os.chmod(vault_file, stat.S_IRUSR | stat.S_IWUSR)

    return vault_file


def clear_project_vault(project_root: Path) -> bool:
    """Securely deletes project credentials and unsets local credential helper."""
    vault_file = get_project_vault_path(project_root)
    deleted = False

    if vault_file.exists():
        # Overwrite with zeros before deleting
        try:
            vault_file.write_bytes(b"\x00" * vault_file.stat().st_size)
            vault_file.unlink()
            deleted = True
        except Exception:
            if vault_file.exists():
                vault_file.unlink()
                deleted = True

    # Unset local credential configs
    if (project_root / ".git").exists():
        subprocess.run(["git", "config", "--local", "--unset-all", "credential.helper"], cwd=project_root, check=False)

    return deleted


def get_project_vault_status(project_root: Path) -> Dict[str, Any]:
    """Inspects project-level vault health, permissions, and git configuration."""
    vault_file = get_project_vault_path(project_root)
    status: Dict[str, Any] = {
        "vault_exists": vault_file.exists(),
        "vault_path": str(vault_file),
        "permissions_secure": False,
        "is_gitignored": False,
        "is_untracked": True,
        "credential_helper_configured": False,
        "credential_use_http_path": False,
        "username": None,
        "token_masked": None,
        "host": None,
    }

    # 1. Permissions check
    if vault_file.exists():
        mode = vault_file.stat().st_mode & 0o777
        status["permissions_secure"] = (mode == 0o600 or mode == 0o400)

        # Parse masked credentials
        try:
            content = vault_file.read_text(encoding="utf-8").strip()
            if content:
                parsed = urllib.parse.urlparse(content)
                status["host"] = parsed.hostname
                user = urllib.parse.unquote(parsed.username or "")
                status["username"] = user
                passwd = urllib.parse.unquote(parsed.password or "")
                if passwd:
                    if len(passwd) > 8:
                        status["token_masked"] = f"{passwd[:4]}...{passwd[-4:]}"
                    else:
                        status["token_masked"] = "***"
        except Exception:
            pass

    # 2. Git ignore check
    if (project_root / ".git").exists():
        res_ign = subprocess.run(
            ["git", "check-ignore", "-q", str(vault_file)],
            cwd=project_root,
            capture_output=True,
            check=False,
        )
        status["is_gitignored"] = (res_ign.returncode == 0)

        # 3. Git untracked check
        res_ls = subprocess.run(
            ["git", "ls-files", str(vault_file)],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        status["is_untracked"] = (len(res_ls.stdout.strip()) == 0)

        # 4. Helper config check
        res_h = subprocess.run(
            ["git", "config", "--local", "credential.helper"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        helper_val = res_h.stdout.strip()
        status["credential_helper_configured"] = bool(
            helper_val and f"store --file {vault_file.resolve()}" in helper_val
        )

        res_u = subprocess.run(
            ["git", "config", "--local", "credential.useHttpPath"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        status["credential_use_http_path"] = (res_u.stdout.strip() == "true")

    return status
