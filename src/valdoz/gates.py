"""ValdoZ Gate Engine.

Validates deliverables, placeholders, headings, research citations, and prior phase integrity.
Supports bilingual validation (Arabic and English).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from valdoz.logs import check_research_staleness, load_research
from valdoz.phases import (
    PHASE_DELIVERABLES,
    PHASE_NAMES,
    get_required_deliverables,
    verify_audit_log_integrity,
)
from valdoz.state import (
    ValdozState,
    load_state,
    verify_phase_integrity,
)

# ── Heading Localization Map ────────────────────────────────────────────────
REQUIRED_HEADINGS: Dict[str, Dict[str, List[str]]] = {
    "01-intake.md": {
        "en": ["Client Brief", "Assumptions", "Risks", "Stakeholders"],
        "ar": ["موجز العميل", "الافتراضات", "المخاطر", "أصحاب المصلحة"],
    },
    "02-requirements.md": {
        "en": ["Functional Requirements", "Non-Functional Requirements", "Acceptance Criteria", "Out of Scope"],
        "ar": ["المتطلبات الوظيفية", "المتطلبات غير الوظيفية", "معايير القبول", "خارج النطاق"],
    },
    "03-stack-decision.md": {
        "en": ["Evaluated Options", "Recommendation", "Decision", "Pinned Versions"],
        "ar": ["الخيارات المقيمة", "التوصية", "القرار", "الإصدارات المثبتة"],
    },
    "04-architecture.md": {
        "en": ["Data Model", "API Contracts", "Authentication", "Integration Points"],
        "ar": ["نموذج البيانات", "عقود واجهة برمجة التطبيقات", "المصادقة", "نقاط التكامل"],
    },
    "04-plan.md": {
        "en": ["Milestones", "Slice Breakdown", "Dependencies"],
        "ar": ["المعالم الرئيسية", "تقسيم الشرائح", "التبعيات"],
    },
    "07-verification.md": {
        "en": ["Test Results", "Security Checklist", "Performance Budget", "Acceptance Walkthrough"],
        "ar": ["نتائج الاختبارات", "قائمة فحص الأمان", "ميزانية الأداء", "جولة القبول"],
    },
    "08-deploy.md": {
        "en": ["Environments", "Deployment Steps", "Liveness Proof", "Rollback Plan"],
        "ar": ["بيئات التشغيل", "خطوات النشر", "إثبات الجاهزية", "خطة التراجع"],
    },
    "09-handover.md": {
        "en": ["Runbook", "Access Transfer", "Known Issues", "Sign-Off"],
        "ar": ["دليل التشغيل", "نقل الصلاحيات", "المشكلات المعروفة", "الموافقة النهائية"],
    },
}

PLACEHOLDER_REGEXES = [
    (re.compile(r"\bTODO\b"), "TODO placeholder"),
    (re.compile(r"\bTBD\b"), "TBD placeholder"),
    (re.compile(r"\blorem ipsum\b", re.IGNORECASE), "Lorem Ipsum text"),
    (re.compile(r"\bFIXME\b"), "FIXME placeholder"),
    (re.compile(r"\bXXX\b"), "XXX placeholder"),
]

URL_PATTERN = re.compile(r"https?://[^\s)\]\">]+")


class GateCheck(BaseModel):
    id: str
    name: str
    severity: str = "blocking"  # blocking or warning
    passed: bool
    message: str


class GateReport(BaseModel):
    phase: int
    phase_name: str
    passed: bool
    checks: List[GateCheck] = Field(default_factory=list)


def extract_headings(markdown_text: str) -> List[str]:
    """Extracts all markdown headings (# Heading)."""
    headings = []
    for line in markdown_text.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("#"):
            title = re.sub(r"^#+\s*", "", line_clean).strip()
            headings.append(title)
    return headings


def scan_placeholders(file_path: Path) -> List[str]:
    """Scans a file for unresolved placeholder markers."""
    findings = []
    text = file_path.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), start=1):
        for pattern, label in PLACEHOLDER_REGEXES:
            if pattern.search(line):
                findings.append(f"Line {i}: {label} found ('{line.strip()[:60]}')")
    return findings


def validate_deliverable_headings(
    file_path: Path,
    lang: str = "en",
) -> Tuple[bool, List[str]]:
    """Checks that required headings exist in deliverable markdown file."""
    fname = file_path.name
    if fname not in REQUIRED_HEADINGS:
        return True, []  # No specific heading schema required

    expected_dict = REQUIRED_HEADINGS[fname]
    target_lang = lang if lang in expected_dict else "en"
    required = expected_dict[target_lang]
    fallback_required = expected_dict.get("en", [])

    text = file_path.read_text(encoding="utf-8", errors="replace")
    found_headings = extract_headings(text)

    missing = []
    for req in required:
        # Match if either localized heading or English fallback heading exists
        matched = any(req.lower() in h.lower() for h in found_headings)
        if not matched and target_lang != "en":
            # Check English fallback
            en_idx = required.index(req)
            if en_idx < len(fallback_required):
                en_req = fallback_required[en_idx]
                matched = any(en_req.lower() in h.lower() for h in found_headings)

        if not matched:
            missing.append(req)

    return len(missing) == 0, missing


def extract_external_urls(text: str) -> List[str]:
    """Extracts non-local external URLs from markdown text."""
    urls = []
    for u in URL_PATTERN.findall(text):
        u_clean = u.rstrip(".,;:")
        # Filter out localhost and test fixtures
        if "localhost" not in u_clean and "127.0.0.1" not in u_clean and "example.com" not in u_clean:
            urls.append(u_clean)
    return list(dict.fromkeys(urls))  # deduplicate


def check_research_citations(project_root: Path, file_path: Path) -> Tuple[bool, List[str]]:
    """Checks that all external URLs in a deliverable are pre-logged in research.jsonl."""
    text = file_path.read_text(encoding="utf-8", errors="replace")
    cited_urls = extract_external_urls(text)
    if not cited_urls:
        return True, []

    logged_research = load_research(project_root)
    logged_urls = {r.url.strip() for r in logged_research}

    unlogged = []
    for u in cited_urls:
        if u not in logged_urls:
            unlogged.append(u)

    return len(unlogged) == 0, unlogged


def run_phase_gate_checks(
    project_root: Path,
    phase_num: Optional[int] = None,
    ci_mode: bool = False,
) -> GateReport:
    """Runs all gate checks for the current or specified phase."""
    state = load_state(project_root)
    target_phase = phase_num if phase_num is not None else state.current_phase
    phase_name = PHASE_NAMES.get(target_phase, f"Phase {target_phase}")

    checks: List[GateCheck] = []

    # 0. Global Hash-Chained Audit Log Integrity
    chain_valid, chain_errs = verify_audit_log_integrity(project_root)
    checks.append(
        GateCheck(
            id="audit-log-integrity",
            name="Cryptographic Audit Log Hash Chain",
            severity="blocking",
            passed=chain_valid,
            message="Audit log hash chain is cryptographically intact" if chain_valid else f"Audit log compromised: {'; '.join(chain_errs)}",
        )
    )

    # 1. Prior phases integrity check
    for p in range(0, target_phase):
        p_state = state.phases[str(p)]
        if p_state.status == "approved":
            is_valid, violations = verify_phase_integrity(project_root, p)
            checks.append(
                GateCheck(
                    id=f"integrity-phase-{p}",
                    name=f"Phase {p} Deliverables Integrity",
                    severity="blocking",
                    passed=is_valid,
                    message="All deliverables match approved hashes" if is_valid else "; ".join(violations),
                )
            )

    # 2. Required deliverables existence check
    req_files = get_required_deliverables(target_phase)
    missing_files = []
    for rel_path in req_files:
        full_path = project_root / rel_path
        if not full_path.exists():
            missing_files.append(rel_path)

    deliverables_exist = len(missing_files) == 0
    checks.append(
        GateCheck(
            id=f"deliverables-exist-phase-{target_phase}",
            name=f"Phase {target_phase} Deliverables Existence",
            severity="blocking",
            passed=deliverables_exist,
            message="All required deliverables exist" if deliverables_exist else f"Missing: {', '.join(missing_files)}",
        )
    )

    # 3. Heading and Placeholder and Citation checks on existing deliverables
    for rel_path in req_files:
        full_path = project_root / rel_path
        if not full_path.exists():
            continue

        # Placeholder scan
        placeholders = scan_placeholders(full_path)
        no_placeholders = len(placeholders) == 0
        checks.append(
            GateCheck(
                id=f"placeholders-{rel_path}",
                name=f"No Placeholders in {rel_path}",
                severity="blocking",
                passed=no_placeholders,
                message="Clean of placeholder text" if no_placeholders else f"Found placeholders: {'; '.join(placeholders[:3])}",
            )
        )

        # Headings check
        headings_ok, missing_hdgs = validate_deliverable_headings(full_path, lang=state.language)
        checks.append(
            GateCheck(
                id=f"headings-{rel_path}",
                name=f"Required Headings in {rel_path} ({state.language})",
                severity="blocking",
                passed=headings_ok,
                message="All required headings present" if headings_ok else f"Missing headings: {', '.join(missing_hdgs)}",
            )
        )

        # Research citations cross-check (Gap 4 defense)
        citations_ok, unlogged_urls = check_research_citations(project_root, full_path)
        checks.append(
            GateCheck(
                id=f"research-citations-{rel_path}",
                name=f"Research Pre-Logging for {rel_path}",
                severity="blocking",
                passed=citations_ok,
                message="All external URLs pre-logged" if citations_ok else f"Uncited URLs (pre-logging required): {', '.join(unlogged_urls)}",
            )
        )

    # 4. Research staleness warning
    stale_items = check_research_staleness(project_root)
    has_stale = len(stale_items) > 0
    checks.append(
        GateCheck(
            id="research-staleness",
            name="Research Staleness Audit",
            severity="warning",
            passed=not has_stale,
            message="Research claims are current" if not has_stale else f"{len(stale_items)} citations exceeded valid_for_days threshold",
        )
    )

    # Overall pass: all blocking checks must pass
    all_passed = all(c.passed for c in checks if c.severity == "blocking")

    return GateReport(
        phase=target_phase,
        phase_name=phase_name,
        passed=all_passed,
        checks=checks,
    )
