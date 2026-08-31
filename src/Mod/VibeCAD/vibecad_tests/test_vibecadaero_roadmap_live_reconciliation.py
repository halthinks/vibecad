# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest


def _find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "docs" / "vibecadaero-roadmap.md").is_file()
            and (candidate / ".github" / "workflows" / "c-cpp.yml").is_file()
        ):
            return candidate
    raise RuntimeError("Unable to locate the VibeCAD source checkout")


REPO_ROOT = _find_repo_root()
AERO_ROADMAP = REPO_ROOT / "docs" / "vibecadaero-roadmap.md"
GOVERNED_ROADMAP = REPO_ROOT / "docs" / "vibecad-governed-engineering-roadmap.md"
G0_FREEZE_RECORD = REPO_ROOT / "docs" / "vibecad-g0-freeze-20260831.md"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "c-cpp.yml"

BEGIN = "<!-- VIBECADAERO-LIVE-RECONCILIATION:BEGIN -->"
END = "<!-- VIBECADAERO-LIVE-RECONCILIATION:END -->"
BASELINE_EVIDENCE_BEGIN = "<!-- VIBECADAERO-BASELINE-EVIDENCE:BEGIN -->"
BASELINE_EVIDENCE_END = "<!-- VIBECADAERO-BASELINE-EVIDENCE:END -->"
CONCURRENT_REPORT_BEGIN = "<!-- VIBECADAERO-CONCURRENT-REPORT:BEGIN -->"
CONCURRENT_REPORT_END = "<!-- VIBECADAERO-CONCURRENT-REPORT:END -->"

PREVIOUS_BASELINE_SHA = "8611ac881a67b77b777c38f1749880527d2cc956"
BASELINE_SHA = "d8bde1ba3f97a861b096ca8bb92a86b5306551e3"
BASELINE_SHORT_SHA = BASELINE_SHA[:8]
BASELINE_TREE = "a6fa0ec77dd4b36aadd2f7bdd32576046124af82"
BASELINE_COMMIT_TIME = "2026-08-31T08:23:49-07:00"
DRIFT_PATH_COUNT = 26
DRIFT_PATH_MANIFEST_SHA256 = (
    "2ad30026c41466f2720381dff936bd5643cd2409f34b0fe0bec6ca4529f0884a"
)
ROOT_LOCK_SHA256 = (
    "45cb657fc0d8d7e320673c559918ffabae582ffdfb2ab69e4ade271eada568b2"
)
PACKAGE_LOCK_SHA256 = (
    "f5cf92da6ec353ae450cdf613180a3fb7e7d74418a337577602f30d14c94d48d"
)
PACKAGE_RECIPE_SHA256 = (
    "c0e7a45efeef5e43f9e551aeaeeb0429aa5bc0cf0568782ad13406981757c287"
)
FASTENERS_SUBMODULE_SHA = "033225ae84d65cfde0a39c2750dfa8e549a10cab"

EXPECTED_METADATA = {
    "Accepted implementation baseline": f"`halthinks/vibecad@{BASELINE_SHA}`",
    "Baseline source ref at audit": (
        "`origin/codex/vibecad-full-roadmap-20260830`"
    ),
    "Baseline tree": f"`{BASELINE_TREE}`",
    "Baseline commit time": f"`{BASELINE_COMMIT_TIME}`",
    "Audit date": "`2026-08-31`",
    "Last revalidated": "`2026-08-31`",
    "Roadmap audit branch": (
        "`codex/g0-native-fem-clarification-20260831`"
    ),
    "Previous accepted baseline": f"`{PREVIOUS_BASELINE_SHA}`",
    "Accepted-baseline drift": (
        f"`{DRIFT_PATH_COUNT}` paths; canonical path-manifest SHA-256 "
        f"`{DRIFT_PATH_MANIFEST_SHA256}`"
    ),
    "Dependency freeze": (
        f"root `pixi.lock` SHA-256 `{ROOT_LOCK_SHA256}`; package lock SHA-256 "
        f"`{PACKAGE_LOCK_SHA256}`; recipe SHA-256 `{PACKAGE_RECIPE_SHA256}`; "
        f"Fasteners gitlink `{FASTENERS_SUBMODULE_SHA}`"
    ),
    "Parallel-work census": (
        "`17` registered worktrees: `12` clean, `5` dirty, `5` with committed "
        "heads not reachable from the accepted baseline; all preserved pending "
        "separate reconciliation"
    ),
    "CI event-base rule": (
        "Pull-request runs require the recorded baseline to equal the event base "
        "SHA; pushes to main require it to equal the event before SHA. Manual "
        "dispatch and local runs are explicitly skipped as event-base "
        "enforcement unavailable."
    ),
    "Credit rule": (
        "Only exact blobs and behavior in the accepted implementation commit "
        "receive integrated completion credit; every tracked modification, "
        "untracked addition, or ignored artifact outside that tree receives "
        "zero credit until committed, reviewed, packaged, and rerun."
    ),
}

INTEGRATED_EVIDENCE = (
    ".github/workflows/c-cpp.yml",
    "Invoke-VibeCAD-VisibleTour.ps1",
    "Launch-VibeCAD-Dev.cmd",
    "Launch-VibeCAD-Dev.ps1",
    "README.md",
    "RUN-VIBECAD-DEV.cmd",
    "docs/developer-launch-windows.md",
    "docs/vibecad-agent-control.md",
    "src/Mod/VibeCAD/CMakeLists.txt",
    "src/Mod/VibeCAD/InitGui.py",
    "src/Mod/VibeCAD/VibeCADAgentCli.py",
    "src/Mod/VibeCAD/VibeCADAgentControl.py",
    "src/Mod/VibeCAD/tool_impl/analysis_persistence.py",
    "src/Mod/VibeCAD/tool_impl/engineering_contracts.py",
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "analysis_fem_installed_lifecycle_integration.py"
    ),
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "analysis_fem_installed_publication_integration.py"
    ),
    "src/Mod/VibeCAD/vibecad_tests/test_agent_control.py",
    "src/Mod/VibeCAD/vibecad_tests/test_agent_control_grok_bot.py",
    "src/Mod/VibeCAD/vibecad_tests/test_analysis_persistence.py",
    "src/Mod/VibeCAD/vibecad_tests/test_branding_contract.py",
    "src/Mod/VibeCAD/vibecad_tests/test_dev_launcher_contract.py",
    "src/Mod/VibeCAD/vibecad_tests/test_engineering_contracts.py",
    "src/Mod/VibeCAD/vibecad_tests/test_visible_operator_contract.py",
)

POST_BASELINE_TRACKED_EVIDENCE = (
    "docs/direct-geometry/VIBECAD_DIRECT_GEOMETRY_RECONCILIATION_ADDENDUM.md",
    "docs/vibecad-g0-freeze-20260831.md",
    "docs/vibecad-governed-engineering-roadmap.md",
    "docs/vibecadaero-roadmap.md",
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "test_cross_repository_roadmap_assignments.py"
    ),
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "test_vibecadaero_roadmap_live_reconciliation.py"
    ),
)

REPORTED_ONLY_FEM_EVIDENCE = (
    "src/Mod/VibeCAD/VibeCADAnalysisFEMPublication.py",
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "analysis_fem_installed_active_close_integration.py"
    ),
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "analysis_fem_installed_physical_calculix_integration.py"
    ),
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "analysis_fem_installed_verified_publication_integration.py"
    ),
    "tools/run_analysis_fem_installed_active_close.py",
    "tools/run_analysis_fem_installed_physical_calculix.py",
    "tools/run_analysis_fem_installed_verified_publication.py",
)

CONCURRENT_ZERO_CREDIT_EVIDENCE = tuple(
    sorted((*POST_BASELINE_TRACKED_EVIDENCE, *REPORTED_ONLY_FEM_EVIDENCE))
)

ROADMAP_CI_TESTS = (
    (
        "src/Mod/VibeCAD/vibecad_tests/"
        "test_vibecadaero_roadmap_live_reconciliation.py"
    ),
    "src/Mod/VibeCAD/vibecad_tests/test_cross_repository_roadmap_assignments.py",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _reconciliation_section(text: str) -> str:
    return _bounded_section(text, BEGIN, END)


def _bounded_section(text: str, begin: str, end: str) -> str:
    assert text.count(begin) == 1, begin
    assert text.count(end) == 1, end
    return text.split(begin, 1)[1].split(end, 1)[0]


def _heading_section(text: str, heading: str, next_heading: str) -> str:
    assert text.count(heading) == 1, heading
    assert text.count(next_heading) == 1, next_heading
    return text.split(heading, 1)[1].split(next_heading, 1)[0]


def _metadata_rows(section: str) -> dict[str, str]:
    lines = [line.strip() for line in section.splitlines() if line.startswith("|")]
    assert len(lines) >= 3
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    assert header == ["Field", "Value"]

    rows: dict[str, str] = {}
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 2, line
        field, value = cells
        assert field not in rows, field
        rows[field] = value
    return rows


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"git {' '.join(args)} failed with {completed.returncode}: "
        f"{completed.stderr.strip()}"
    )
    return completed.stdout.strip()


def _baseline_tree_paths() -> set[str]:
    return set(_git("ls-tree", "-r", "--name-only", BASELINE_SHA).splitlines())


def _bullet_paths(section: str) -> tuple[str, ...]:
    paths = tuple(re.findall(r"(?m)^- `([^`\r\n]+)`[.;]$", section))
    assert len(paths) == len(set(paths)), "duplicate evidence path"
    return paths


def _validate_ci_event_base(event_name: str, event_base_sha: str) -> bool:
    if event_name in {"pull_request", "push"}:
        assert re.fullmatch(r"[0-9a-f]{40}", event_base_sha), (
            f"{event_name} requires a full event-base SHA"
        )
        assert event_base_sha == BASELINE_SHA, (
            f"Recorded baseline {BASELINE_SHA} does not match the "
            f"{event_name} event base {event_base_sha}; repeat G0/Step 0 for "
            "this implementation tranche before claiming roadmap credit."
        )
        return True

    if event_name in {"", "workflow_dispatch"}:
        assert event_base_sha == "", (
            f"{event_name or 'local'} runs must not imply an authoritative "
            "event-base binding"
        )
        return False

    raise AssertionError(f"Unsupported CI event for roadmap reconciliation: {event_name}")


def test_live_reconciliation_pins_the_accepted_fork_baseline() -> None:
    aero = _text(AERO_ROADMAP)
    governed = _text(GOVERNED_ROADMAP)
    section = _reconciliation_section(aero)

    assert _metadata_rows(section) == EXPECTED_METADATA
    assert (
        f"**Status: Verified complete for accepted source baseline "
        f"`{BASELINE_SHA}` on 2026-08-31; repeat per tranche.**"
    ) in governed
    assert (
        f"| 0 — live reconciliation | **ACTIVE** | **Verified complete at "
        f"accepted baseline `{BASELINE_SHORT_SHA}`; repeat per tranche** |"
    ) in aero
    step_zero = _heading_section(
        aero,
        "### Step 0 — live re-reconciliation",
        "### Step 1 — characterize current FEM/background behavior",
    )
    assert (
        f"**Status: Verified complete for accepted source baseline "
        f"`{BASELINE_SHA}` on 2026-08-31; repeat at every implementation "
        f"tranche.**"
    ) in step_zero
    assert "31ea810db" not in step_zero


def test_accepted_baseline_facts_are_validated_against_git() -> None:
    assert _git("rev-parse", f"{BASELINE_SHA}^{{commit}}") == BASELINE_SHA
    assert _git("rev-parse", f"{BASELINE_SHA}^{{tree}}") == BASELINE_TREE
    assert _git("show", "-s", "--format=%cI", BASELINE_SHA) == BASELINE_COMMIT_TIME
    _git("merge-base", "--is-ancestor", BASELINE_SHA, "HEAD")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_g0_freeze_record_binds_source_dependencies_and_drift() -> None:
    freeze = _text(G0_FREEZE_RECORD)
    drift_paths = sorted(
        _git("diff", "--name-only", PREVIOUS_BASELINE_SHA, BASELINE_SHA).splitlines()
    )
    drift_manifest = "\n".join(drift_paths).encode("utf-8")

    assert len(drift_paths) == DRIFT_PATH_COUNT
    assert hashlib.sha256(drift_manifest).hexdigest() == DRIFT_PATH_MANIFEST_SHA256
    assert _sha256(REPO_ROOT / "pixi.lock") == ROOT_LOCK_SHA256
    assert (
        _sha256(REPO_ROOT / "package" / "rattler-build" / "pixi.lock")
        == PACKAGE_LOCK_SHA256
    )
    assert (
        _sha256(REPO_ROOT / "package" / "rattler-build" / "recipe.yaml")
        == PACKAGE_RECIPE_SHA256
    )
    fasteners_row = _git("ls-tree", BASELINE_SHA, "src/Mod/Fasteners")
    assert fasteners_row.split()[2] == FASTENERS_SUBMODULE_SHA

    for value in (
        BASELINE_SHA,
        BASELINE_TREE,
        PREVIOUS_BASELINE_SHA,
        DRIFT_PATH_MANIFEST_SHA256,
        ROOT_LOCK_SHA256,
        PACKAGE_LOCK_SHA256,
        PACKAGE_RECIPE_SHA256,
        FASTENERS_SUBMODULE_SHA,
    ):
        assert freeze.count(value) == 1, value

    normalized = " ".join(freeze.split())
    assert "17 registered worktrees" in normalized
    assert "12 clean" in normalized
    assert "5 dirty" in normalized
    assert "5 non-ancestor" in normalized
    assert "No worktree was reset, stashed, cleaned, removed, or merged" in normalized
    assert "source freeze does not transfer exact-package runtime acceptance" in normalized


def test_dependency_graph_separates_native_foundation_from_full_closure() -> None:
    governed = _text(GOVERNED_ROADMAP)
    normalized = " ".join(governed.split())

    assert "`VIBECAD-NATIVE-AUTHORITY-FOUNDATION`" in governed
    assert "`VIBECAD-NATIVE-HOST`" in governed
    assert (
        "full `VIBECAD-NATIVE-HOST` closure is not a prerequisite for the "
        "FEM tranche"
    ) in normalized
    assert "PKG[Package-contained CalculiX] --> FEM" in governed
    assert "N0 --> FEM" in governed
    assert "FEM --> G2" in governed
    assert "N0 --> G2" in governed
    assert "G2 --> NH" in governed
    assert "G4 --> NH" in governed
    assert "T --> DG0" in governed
    assert "G2 --> DG0" not in governed
    assert (
        "VC-DG-0 depends on the reusable tester, not on completed G2"
    ) in normalized
    assert (
        "Generic tester success is infrastructure evidence only. It earns zero "
        "domain completion credit and zero physics, solver, numerical, "
        "verification, qualification, or domain-result-publication credit."
    ) in normalized


def test_ci_event_base_policy_rejects_stale_or_ambiguous_tranches() -> None:
    assert _validate_ci_event_base("pull_request", BASELINE_SHA) is True
    assert _validate_ci_event_base("push", BASELINE_SHA) is True
    assert _validate_ci_event_base("workflow_dispatch", "") is False
    assert _validate_ci_event_base("", "") is False

    with pytest.raises(AssertionError, match="does not match"):
        _validate_ci_event_base("pull_request", "1" * 40)
    with pytest.raises(AssertionError, match="full event-base SHA"):
        _validate_ci_event_base("push", "")
    with pytest.raises(AssertionError, match="must not imply"):
        _validate_ci_event_base("workflow_dispatch", BASELINE_SHA)
    with pytest.raises(AssertionError, match="Unsupported CI event"):
        _validate_ci_event_base("schedule", "")


def test_current_ci_event_base_matches_the_recorded_baseline_when_available() -> None:
    event_name = os.environ.get("VIBECAD_CI_EVENT_NAME", "")
    event_base_sha = os.environ.get("VIBECAD_CI_BASE_SHA", "")
    if not _validate_ci_event_base(event_name, event_base_sha):
        pytest.skip(
            "authoritative CI event-base enforcement unavailable for "
            f"{event_name or 'local'} run"
        )


def test_only_tracked_baseline_files_receive_integrated_evidence_credit() -> None:
    section = _reconciliation_section(_text(AERO_ROADMAP))
    baseline_paths = _baseline_tree_paths()
    documented_integrated = _bullet_paths(
        _bounded_section(section, BASELINE_EVIDENCE_BEGIN, BASELINE_EVIDENCE_END)
    )
    documented_concurrent = _bullet_paths(
        _bounded_section(section, CONCURRENT_REPORT_BEGIN, CONCURRENT_REPORT_END)
    )

    assert documented_integrated == INTEGRATED_EVIDENCE
    assert documented_concurrent == CONCURRENT_ZERO_CREDIT_EVIDENCE
    assert set(documented_integrated).isdisjoint(documented_concurrent)

    for relative_path in INTEGRATED_EVIDENCE:
        assert (REPO_ROOT / relative_path).is_file(), relative_path
        assert relative_path in baseline_paths, relative_path
        assert _git("hash-object", "--", relative_path) == _git(
            "rev-parse", f"{BASELINE_SHA}:{relative_path}"
        ), relative_path

    for relative_path in POST_BASELINE_TRACKED_EVIDENCE:
        assert (REPO_ROOT / relative_path).is_file(), relative_path
        if relative_path in baseline_paths:
            assert _git("hash-object", "--", relative_path) != _git(
                "rev-parse", f"{BASELINE_SHA}:{relative_path}"
            ), relative_path
        else:
            assert relative_path not in baseline_paths, relative_path

    for relative_path in REPORTED_ONLY_FEM_EVIDENCE:
        assert not (REPO_ROOT / relative_path).exists(), relative_path
        assert relative_path not in baseline_paths, relative_path

    normalized = " ".join(section.split())
    assert "Concurrent post-baseline report" in normalized
    assert "means the exact blob at the accepted baseline path" in normalized
    assert "reported paths are not accepted implementation evidence" in normalized
    assert "zero integrated completion credit" in normalized
    assert "exact committed and packaged tree" in normalized


def test_historical_and_concurrent_checkpoints_are_not_presented_as_current() -> None:
    aero = _text(AERO_ROADMAP)
    normalized = " ".join(aero.split())

    assert "**Current roadmap execution stack reconciled:**" not in aero
    assert "**Latest stabilization checkpoint:**" not in aero
    assert "**Historical roadmap execution record:**" in aero
    assert "**Concurrent stabilization report; zero integrated credit:**" in aero
    assert "The historical audit of `main@31ea810db`" in normalized
    assert "Reported physical CalculiX work remains outside the accepted baseline" in normalized
    assert "The reusable tester source is integrated at the accepted baseline" in normalized
    assert "its exact merged-tree package acceptance remains open" in normalized


def test_roadmaps_do_not_embed_common_machine_local_absolute_paths() -> None:
    machine_local_paths = (
        re.compile(
            r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|file:///[A-Za-z]:/)",
            flags=re.IGNORECASE,
        ),
        re.compile(r"(?<![\\])\\\\[^\\\s`]+\\[^\\\s`]+"),
        re.compile(
            r"(?<![A-Za-z0-9_])(?:file://)?/(?:home|Users)/"
            r"[A-Za-z0-9._-]+(?:/|\b)",
            flags=re.IGNORECASE,
        ),
    )

    for path in (AERO_ROADMAP, GOVERNED_ROADMAP):
        roadmap = _text(path)
        for pattern in machine_local_paths:
            assert pattern.search(roadmap) is None, (path, pattern.pattern)


def test_live_reconciliation_checks_are_enforced_by_ci() -> None:
    workflow_lines = [line.strip() for line in _text(CI_WORKFLOW).splitlines()]

    assert workflow_lines.count("fetch-depth: 0") == 1
    assert workflow_lines.count(
        "VIBECAD_CI_EVENT_NAME: ${{ github.event_name }}"
    ) == 1
    assert workflow_lines.count(
        "VIBECAD_CI_BASE_SHA: "
        "${{ github.event.pull_request.base.sha || github.event.before || '' }}"
    ) == 1
    for relative_path in ROADMAP_CI_TESTS:
        assert workflow_lines.count(f"{relative_path} \\") == 1, relative_path
