from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPO_ROOT / "agents" / "cerribro" / "cerribrobaddan.md"
README_PATH = REPO_ROOT / "agents" / "cerribro" / "README.md"
PROTOCOL_PATH = REPO_ROOT / "agents" / "cerribro" / "coordination-protocol.md"
CHECKLIST_PATH = REPO_ROOT / "agents" / "cerribro" / "qc-cybersecurity-checklist.md"
RUBRIC_PATH = REPO_ROOT / "agents" / "cerribro" / "auto-review-rubric.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cerribrobaddan_profile_identity_and_relationship() -> None:
    content = _read(PROFILE_PATH)

    assert PROFILE_PATH.exists()
    assert "# cerribrobaddan Agent Profile" in content
    assert "- **Name:** cerribrobaddan" in content
    assert "- **Relationship:** Brother agent to `cerribro`" in content


def test_cerribrobaddan_mission_and_responsibilities_are_documented() -> None:
    content = _read(PROFILE_PATH)

    assert "## Primary Mission" in content
    assert "second-line quality and defense agent" in content
    assert "1. **Quality Control (Primary Role)**" in content
    assert "2. **Mistake Correction**" in content
    assert "3. **Defensive Backstop**" in content
    assert "4. **Coding Assistance & Bad Code Removal**" in content
    assert "5. **Cybersecurity Support**" in content


def test_cerribrobaddan_operating_principles_are_present() -> None:
    content = _read(PROFILE_PATH)

    assert "## Operating Principles" in content
    assert "- Be precise, objective, and actionable." in content
    assert "- Prioritize safety and correctness over speed." in content
    assert "- Document corrections clearly." in content
    assert "- Leave systems better than found: cleaner, safer, and easier to maintain." in content


def test_cerribrobaddan_collaboration_protocol_covers_roles_and_decisions() -> None:
    content = _read(PROTOCOL_PATH)

    assert "cerribro (Primary Orchestrator)" in content
    assert "cerribrobaddan (Quality & Defense Backstop)" in content
    assert "**Approve:** Ship as-is." in content
    assert "**Revise:** Return actionable corrections to `cerribro`." in content
    assert "**Block:** Stop release if critical risk or unsafe behavior is detected." in content


def test_cerribrobaddan_quality_artifacts_are_linked_and_complete() -> None:
    readme = _read(README_PATH)
    checklist = _read(CHECKLIST_PATH)
    rubric = _read(RUBRIC_PATH)

    assert "`cerribrobaddan.md`" in readme
    assert "## B) Bad Code Detection & Cleanup" in checklist
    assert "## C) Security Checks" in checklist
    assert "## Decision Rules" in rubric
    assert "Final decision: APPROVE / REVISE / BLOCK" in rubric
