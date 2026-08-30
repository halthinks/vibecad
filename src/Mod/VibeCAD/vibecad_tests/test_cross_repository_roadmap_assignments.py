# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ROADMAP = REPO_ROOT / "docs" / "vibecad-governed-engineering-roadmap.md"
AERO_ROADMAP = REPO_ROOT / "docs" / "vibecadaero-roadmap.md"
DG_ADDENDUM = (
    REPO_ROOT
    / "docs"
    / "direct-geometry"
    / "VIBECAD_DIRECT_GEOMETRY_RECONCILIATION_ADDENDUM.md"
)
README = REPO_ROOT / "README.md"
BEGIN = "<!-- VIBECAD-CROSS-REPOSITORY-ASSIGNMENTS:BEGIN -->"
END = "<!-- VIBECAD-CROSS-REPOSITORY-ASSIGNMENTS:END -->"

EXPECTED_OWNERS = {
    "REUSABLE-VISIBLE-TESTER": "Reusable tester tooling",
    "VIBECAD-NATIVE-HOST": "VibeCAD",
    "VIBECAD-FEM-CALCULIX-RETAINED": "VibeCAD",
    "VIBECAD-MCMASTERINSERT-RETAINED": "VibeCAD",
    "VIBECAD-ENGINEERING-PRESENTATION": "VibeCAD",
    "AERO-STEP-00-11": "VibeCAD",
    "AERO-STEP-12-20": "VibeMechanica",
    "VIBECAD-CFDOF-COMPATIBILITY": "VibeCAD",
    "VC-DG-0": "VibeCAD",
    "VC-DG-1": "VibeCAD",
    "VC-DG-2": "VibeCAD",
    "VC-DG-3": "VibeCAD",
    "VC-DG-4": "VibeCAD",
    "VC-DG-5": "VibeCAD",
    "VC-DG-6": "VibeCAD",
    "VC-DG-7": "VibeCAD",
    "VIBEMECHANICA-GENERALIZED-PHYSICS": "VibeMechanica",
}

EXPECTED_STATUSES = {
    "REUSABLE-VISIBLE-TESTER": "partial",
    "VIBECAD-NATIVE-HOST": "partial",
    "VIBECAD-FEM-CALCULIX-RETAINED": "partial",
    "VIBECAD-MCMASTERINSERT-RETAINED": "partial",
    "VIBECAD-ENGINEERING-PRESENTATION": "partial",
    "AERO-STEP-00-11": "partial",
    "AERO-STEP-12-20": "planned in VibeMechanica; Step 13 optional; historical in VibeCAD",
    "VIBECAD-CFDOF-COMPATIBILITY": "partial compatibility",
    "VC-DG-0": "partial",
    "VC-DG-1": "partial",
    "VC-DG-2": "partial",
    "VC-DG-3": "partial",
    "VC-DG-4": "partial",
    "VC-DG-5": "partial",
    "VC-DG-6": "blocked",
    "VC-DG-7": "optional; not started",
    "VIBEMECHANICA-GENERALIZED-PHYSICS": "planned in VibeMechanica; outside VibeCAD",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assignment_rows(text: str) -> dict[str, dict[str, str]]:
    assert text.count(BEGIN) == 1
    assert text.count(END) == 1
    section = text.split(BEGIN, 1)[1].split(END, 1)[0]
    table_lines = [line.strip() for line in section.splitlines() if line.startswith("|")]
    assert len(table_lines) >= 3

    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    assert header == [
        "Item ID",
        "Accountable owner",
        "Supporting or consuming owner",
        "Status",
        "Dependency or start condition",
        "Acceptance and claim boundary",
    ]

    rows: dict[str, dict[str, str]] = {}
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == len(header), line
        row = dict(zip(header, cells, strict=True))
        item_id = row["Item ID"].strip("`")
        assert item_id not in rows, item_id
        rows[item_id] = row
    return rows


def test_cross_repository_assignment_matrix_is_complete_and_singly_owned() -> None:
    rows = _assignment_rows(_text(ROADMAP))

    assert set(rows) == set(EXPECTED_OWNERS)
    assert {
        item_id: row["Accountable owner"] for item_id, row in rows.items()
    } == EXPECTED_OWNERS
    assert {item_id: row["Status"] for item_id, row in rows.items()} == EXPECTED_STATUSES

    for item_id, row in rows.items():
        owner = row["Accountable owner"].strip()
        assert owner
        assert owner.casefold() not in {"shared", "unassigned", "tbd", "none"}
        assert row["Supporting or consuming owner"].strip(), item_id
        assert row["Dependency or start condition"].strip(), item_id
        assert row["Acceptance and claim boundary"].strip(), item_id


def test_vc_dg_states_and_cross_product_cutlines_are_not_flattened() -> None:
    roadmap = _text(ROADMAP)
    prose = " ".join(roadmap.split())

    assert "VC-DG-0 through VC-DG-5 are partial" in prose
    assert "VC-DG-6 is blocked by VC-DG-5" in prose
    assert "VC-DG-7 is optional and planned" not in prose
    assert "VC-DG-0 through VC-DG-7 remain open" not in prose
    assert "generic CfdOF compatibility earns zero Aero Step 12 completion credit" in prose
    assert "zero direct-geometry method credit" in prose
    assert "Aero Steps 12-20 are assigned to VibeMechanica" in prose
    assert "Aero Step 13 remains optional and non-blocking" in prose
    assert "VC-DG-7 is assigned to VibeCAD" in prose
    assert "Its optional status does not make its owner undecided" in prose
    assert "Optional changes the VibeCAD release gate, not ownership" in prose

    addendum = " ".join(_text(DG_ADDENDUM).split())
    assert "VC-DG-7 is assigned to VibeCAD" in addendum
    assert "Its optional status does not make its owner undecided" in addendum
    assert "Optional changes the VibeCAD release gate, not ownership" in addendum
    assert "their future implementation belongs to VibeMechanica" in addendum

    aero_roadmap = " ".join(_text(AERO_ROADMAP).split())
    readme = " ".join(_text(README).split())
    for text in (aero_roadmap, readme):
        assert "VC-DG-7 is assigned to VibeCAD" in text
        assert "Optional changes the VibeCAD release gate, not ownership" in text


def test_mcmaster_status_remains_partial_until_runtime_acceptance_closes() -> None:
    roadmap = _text(ROADMAP)
    readme = _text(README)

    assert "COMPLETE AND RETAIN CURRENT CAPABILITY" not in roadmap
    assert "RETAIN CURRENT CAPABILITY / ACTIVE ACCEPTANCE CLOSURE" in roadmap
    assert "remains partial until" in readme
    assert "is finished only" not in readme


def test_advanced_aero_transfer_is_explicit_in_the_aero_owner_document() -> None:
    aero_roadmap = " ".join(_text(AERO_ROADMAP).split())
    readme = " ".join(_text(README).split())

    assert "VibeMechanica owns future implementation of Steps 12-20" in aero_roadmap
    assert "They remain historical/non-normative in VibeCAD" in aero_roadmap
    assert "VibeCADAero continues to own only Steps 0-11 here" in aero_roadmap
    assert "accepted compatibility handoff" in aero_roadmap
    assert "HISTORICAL HERE; VIBEMECHANICA-OWNED" in aero_roadmap
    assert "Optional and non-blocking in VibeMechanica" in aero_roadmap
    assert (
        "detailed Step 12-20 sections below preserve technical source and "
        "acceptance history"
    ) in aero_roadmap
    assert "VibeMechanica roadmap" in readme
