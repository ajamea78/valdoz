"""Integration and end-to-end lifecycle dry-run tests for ValdoZ Protocol."""

import subprocess
import pytest
from pathlib import Path
from valdoz.approval import approve_phase
from valdoz.gates import run_phase_gate_checks
from valdoz.integration import install_ci_workflow, install_git_hook
from valdoz.logs import add_decision, pre_log_research_intent
from valdoz.phases import advance_phase
from valdoz.slices import approve_slice, done_slice, start_slice
from valdoz.state import (
    ValdozState,
    get_state_path,
    is_write_protected,
    load_state,
    save_state,
)
from valdoz.sync import sync_all_runtimes


@pytest.fixture
def git_project(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Lead Architect"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "lead@example.com"], cwd=str(tmp_path), check=True)
    return tmp_path


def test_git_hook_and_ci_generation(git_project: Path):
    # 1. Install Git pre-commit and pre-push hooks
    hook_file = install_git_hook(git_project)
    assert hook_file.exists()
    import stat
    mode = hook_file.stat().st_mode
    assert bool(mode & stat.S_IXUSR)  # Executable

    pre_push_file = git_project / ".git" / "hooks" / "pre-push"
    assert pre_push_file.exists()
    mode_p = pre_push_file.stat().st_mode
    assert bool(mode_p & stat.S_IXUSR)  # Executable
    assert "ValdoZ Push Protection Error" in pre_push_file.read_text(encoding="utf-8")

    # 2. Generate CI workflow
    ci_file = install_ci_workflow(git_project)
    assert ci_file.exists()
    ci_text = ci_file.read_text()
    assert "uv tool install valdoz-protocol@3.0.0" in ci_text
    assert "valdoz gate check --ci" in ci_text
    assert "valdoz audit --strict --no-network" in ci_text


def test_pre_push_hook_blocks_main_in_early_phases(git_project: Path):
    install_git_hook(git_project)
    pre_push_file = git_project / ".git" / "hooks" / "pre-push"

    # Set up ValdoZ state at Phase 6 (Build)
    state = ValdozState(project_name="push-guard-test", current_phase=6)
    save_state(git_project, state)

    # Simulate git passing push refs for 'main' on stdin:
    stdin_data = "refs/heads/main 1111111 refs/heads/main 0000000\n"
    res = subprocess.run(
        [str(pre_push_file), "origin", "https://github.com/example/repo.git"],
        input=stdin_data,
        cwd=str(git_project),
        text=True,
        capture_output=True,
    )
    # Must fail and block push to main in Phase 6
    assert res.returncode != 0
    assert "Direct push to production-linked branch 'main' is BLOCKED" in res.stdout

    # Pushing to a feature branch is allowed
    stdin_feature = "refs/heads/slice/01-auth 1111111 refs/heads/slice/01-auth 0000000\n"
    res_feature = subprocess.run(
        [str(pre_push_file), "origin", "https://github.com/example/repo.git"],
        input=stdin_feature,
        cwd=str(git_project),
        text=True,
        capture_output=True,
    )
    assert res_feature.returncode == 0

    # Advance to Phase 8 (Deploy) -> push to main is permitted
    state.current_phase = 8
    save_state(git_project, state)
    res_phase8 = subprocess.run(
        [str(pre_push_file), "origin", "https://github.com/example/repo.git"],
        input=stdin_data,
        cwd=str(git_project),
        text=True,
        capture_output=True,
    )
    assert res_phase8.returncode == 0


def test_full_project_lifecycle_dry_run(git_project: Path):
    """End-to-end dry run through the full lifecycle from brief to build."""
    # 1. Phase 0: Project Init
    state = ValdozState(project_name="e2e-client-project", language="ar", current_phase=0, packs=["base", "web-app"])
    save_state(git_project, state)
    sync_all_runtimes(git_project)

    # Approve Phase 0 and advance to Phase 1
    approve_phase(git_project, phase_num=0, enforce_tty=False, confirmation_input="init")
    p1 = advance_phase(git_project)
    assert p1 == 1

    # 2. Phase 1: Intake (Bilingual Arabic)
    intake_doc = git_project / "docs" / "01-intake.md"
    intake_doc.parent.mkdir(parents=True, exist_ok=True)
    intake_doc.write_text("""# موجز المشروع
## موجز العميل
العميل يطلب نظام إدارة الحجوزات مع دعم الدفع عبر بوابة سترايب https://stripe.com
## الافتراضات
النظام سيعمل سحابياً.
## المخاطر
تأخير موافقة بوابة الدفع.
## أصحاب المصلحة
المدير التنفيذي والمهندس المسؤول.
""")

    # Pre-log research intent before gate
    pre_log_research_intent(git_project, url="https://stripe.com", claim="Stripe API", phase=1)

    # Gate check must pass
    report_p1 = run_phase_gate_checks(git_project, phase_num=1)
    assert report_p1.passed is True

    # Human approval
    approve_phase(git_project, phase_num=1, enforce_tty=False, confirmation_input="intake", approver_name="lead")
    assert is_write_protected(get_state_path(git_project))

    # Advance to Phase 2: Requirements
    p2 = advance_phase(git_project)
    assert p2 == 2

    req_doc = git_project / "docs" / "02-requirements.md"
    req_doc.write_text("""# المتطلبات
## المتطلبات الوظيفية
تسجيل المستخدمين، حجز المواعيد.
## المتطلبات غير الوظيفية
زمن الاستجابة أقل من 200 مللي ثانية.
## معايير القبول
اجتياز كافة الاختبارات الآلية.
## خارج النطاق
تطبيق الساعات الذكية.
""")
    report_p2 = run_phase_gate_checks(git_project, phase_num=2)
    assert report_p2.passed is True
    approve_phase(git_project, phase_num=2, enforce_tty=False, confirmation_input="requirements")

    # Advance to Phase 3: Stack Decision
    p3 = advance_phase(git_project)
    assert p3 == 3
    add_decision(
        git_project,
        question="Frontend framework?",
        choice="Next.js with React 19",
        rationale="SSR and SEO requirements",
        phase=3,
    )
    stack_doc = git_project / "docs" / "03-stack-decision.md"
    stack_doc.write_text("""# قرار المكدس التقني
## الخيارات المقيمة
Next.js vs Remix.
## التوصية
Next.js.
## القرار
Next.js.
## الإصدارات المثبتة
Next 15, React 19.
""")
    report_p3 = run_phase_gate_checks(git_project, phase_num=3)
    assert report_p3.passed is True
    approve_phase(git_project, phase_num=3, enforce_tty=False, confirmation_input="stack-decision")

    # Fast-forward to Phase 6 (Build)
    loaded = load_state(git_project)
    loaded.current_phase = 6
    loaded.phases["6"].status = "in_progress"
    save_state(git_project, loaded)

    # Slice 01: Core Auth
    slice_spec = git_project / "docs" / "slices" / "01-auth.md"
    slice_spec.parent.mkdir(parents=True, exist_ok=True)
    slice_spec.write_text("""# Slice 01: Auth
## Summary
Authentication flow.
## Acceptance Criteria
Token generated.
## Test Plan
Run auth tests.
## File Manifest
`src/auth.py`
""")

    start_slice(git_project, "01-auth")
    done_slice(git_project, "01-auth", pre_existing_tests_pass=True, new_tests_pass=True, coverage_delta=0.0)
    approve_slice(git_project, "01-auth", enforce_tty=False, confirmation_input="01-auth")

    # Verify state integrity
    reloaded = load_state(git_project)
    assert reloaded.phases["1"].status == "approved"
    assert reloaded.phases["2"].status == "approved"
    assert reloaded.phases["3"].status == "approved"
    assert is_write_protected(get_state_path(git_project))
