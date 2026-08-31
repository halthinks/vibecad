# VibeCAD G0 source freeze — 2026-08-31

## Purpose and claim ceiling

This is the reviewable G0 source, dependency, owner, drift, and parallel-work
record for the tranche that begins from the merged full-roadmap branch. It is a
source freeze, not a release receipt. In particular, this source freeze does not
transfer exact-package runtime acceptance from a parent branch or an earlier
package to the merged tree. No FEM, Aero, direct-geometry, numerical,
qualification, cross-platform, or full-roadmap completion follows from this
record.

## Exact accepted source

| Field | Frozen value |
| --- | --- |
| Repository | `halthinks/vibecad` |
| Accepted baseline | `d8bde1ba3f97a861b096ca8bb92a86b5306551e3` |
| Tree | `a6fa0ec77dd4b36aadd2f7bdd32576046124af82` |
| Source ref at audit | `origin/codex/vibecad-full-roadmap-20260830` |
| Commit time | `2026-08-31T08:23:49-07:00` |
| Previous accepted baseline | `8611ac881a67b77b777c38f1749880527d2cc956` |
| Accepted-baseline drift | 26 paths; canonical LF-separated sorted path-manifest SHA-256 `2ad30026c41466f2720381dff936bd5643cd2409f34b0fe0bec6ca4529f0884a` |

The drift is additive or compatibility-preserving roadmap, contract, tester,
launcher, persistence, and test work. Acceptance of these source blobs does not
promote any package or physics claim. The two-parent merge preserves both the
full-roadmap lineage and the independently reviewed reusable-tester lineage.

## Frozen dependency identities

| Dependency surface | Frozen identity |
| --- | --- |
| Root `pixi.lock` | SHA-256 `45cb657fc0d8d7e320673c559918ffabae582ffdfb2ab69e4ade271eada568b2` |
| Package `package/rattler-build/pixi.lock` | SHA-256 `f5cf92da6ec353ae450cdf613180a3fb7e7d74418a337577602f30d14c94d48d` |
| Package `package/rattler-build/recipe.yaml` | SHA-256 `c0e7a45efeef5e43f9e551aeaeeb0429aa5bc0cf0568782ad13406981757c287` |
| Fasteners gitlink | `033225ae84d65cfde0a39c2750dfa8e549a10cab` |
| Declared supported platforms | `linux-64`, `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64` |
| Current core runtime bounds | Python `>=3.11,<3.12`; Qt `>=6.8,<6.9`; root NumPy `>=1.26,<1.27`; package NumPy `>=1.26,<2`; CalculiX declared in root and package runtime dependencies |

These declarations and hashes prove dependency intent and frozen bytes. They do
not prove that every declared platform package builds, installs, launches, or
runs a physical solver.

## Registered-worktree census

The read-only census found **17 registered worktrees**: **12 clean**, **5
dirty**, and **5 non-ancestor** committed heads relative to this accepted
baseline. Missing and unreadable counts were zero. No worktree was reset,
stashed, cleaned, removed, or merged as part of the census.

| Branch or state | Head | Dirty rows | Head reachable from baseline | Disposition |
| --- | --- | ---: | --- | --- |
| `main` | `8611ac88` | 48 | yes | preserve and guard; never mutate for this tranche |
| `codex/vibecad-full-roadmap-20260830` | `d8bde1ba` | 0 | yes | accepted source |
| `codex/g0-native-fem-clarification-20260831` | `d8bde1ba` | 0 | yes | active isolated tranche |
| `codex/g1-finding-taxonomy-profile-20260830` | `7edf7dcd` | 0 | no | preserve for separate reconciliation |
| `codex/g1-provenance-profile-20260830` | `d52c1e03` | 4 | yes | preserve dirty work |
| `codex/g2-exact-recovery-20260830` | `d52c1e03` | 4 | yes | preserve dirty work |
| `codex/g2-host-restart-reconciliation-20260830` | `065308e5` | 0 | no | preserve for separate reconciliation |
| `docs/vibecad-roadmap-additive-audit-20260829` | `4175713f` | 0 | no | preserve historical audit lineage |
| `codex/vibecad-roadmap-tester-integration-20260831` | `d8bde1ba` | 0 | yes | integrated branch retained |
| `dev-agent-controlled-testing-gui` | `46e44307` | 0 | no | preserve earlier tester lineage |
| `feature/visible-agent-controlled-development-testing` | `fa7f0db8` | 0 | yes | preserve upstream-PR tester head |
| detached tester build | `29912d56` | 0 | yes | preserve build evidence |
| detached tester build | `cbf31e37` | 0 | yes | preserve build evidence |
| detached tester build | `fa7f0db8` | 0 | yes | preserve exact accepted tester GUI evidence |
| `fix/visible-tester-bootstrap-test-isolation-20260829` | `c373566d` | 2 | no | preserve dirty work |
| detached upstream baseline | `60b8f3fd` | 0 | yes | preserve lineage |
| `codex/full-roadmap-visible-tester-profile-20260831` | `d52c1e03` | 15 | yes | preserve and audit before selective reuse |

The five dirty worktrees overlap launcher/tester, G1 provenance, G2 recovery, or
FEM/Native/package owners. Their uncommitted rows receive zero credit here. The
five non-ancestor heads are not disposable merely because another branch is
newer. Every row remains preserved until its committed and uncommitted state is
independently classified as integrated, superseded, or still required.

## Owner map for the next bounded tranches

| Surface | Current owner | Primary source and contract locations | Immediate boundary |
| --- | --- | --- | --- |
| Reusable visible tester | reusable repository-wide tester | root launchers and tour; `VibeCADAgentControl.py`; `VibeCADAgentCli.py`; developer and agent-control docs; launcher/operator/control tests | Generic infrastructure only. The merged source is present, but an exact merged-tree cold package and visible acceptance receipt remain open. |
| Bounded Native authority foundation | VibeCAD document thread and Native mutation/publication owners | `VibeCADNativeState.py`; `VibeCADNativeStatePersistence.py`; `VibeCADNativeDispatch.py`; `VibeCADNativeMutation.py`; Native preview control/commands; `VibeCADAnalysisNativePublication.py` | Provides exact document identity/currentness, refusal, authorization, and the sole mutation/publication seam needed before FEM integration. It is not full durable Native-host closure. |
| Full Native host | VibeCAD | bounded Native foundation plus current G2 persistence, verification, publication, packaging, rollback, and exact visible acceptance | Closes only after its G2 and G4 dependencies pass; it must not be used as a prerequisite that makes G2 depend on itself. |
| Current FEM/CalculiX G2 | VibeCAD retained compatibility lane | `tool_impl/analysis_fem_adapter.py`; Native solver execution/runtime/process/compatibility adapter; persistence, recovery, verification, publication, and output-admission modules and tests | Extend additively through the bounded Native foundation. Exact installed packaging, physical CalculiX, active-close, crash/restart, currentness, rollback, and publish-once evidence remain open. |
| VC-DG-0 consumer profile | VibeCAD direct-geometry lane consuming the reusable tester | governed roadmap, direct-geometry addendum, generic tester profile registry/runner to be added under a failing contract | Profile registration and exact merged-package visible evidence only. No direct-geometry algorithm or physics credit. |
| Roadmap and G0 evidence | VibeCAD roadmap owner | this record; the governed roadmap; the Aero roadmap; live-reconciliation contract test | Record exact source/dependencies/drift and keep completion claims at the evidence ceiling. |

## Compatibility and acceptance surfaces reread

- Existing public functions, CLI/tool names, route schemas, preference keys,
  launcher defaults, ordinary non-development startup, and error shapes remain
  compatible.
- Native remains the sole CAD mutation and publication authority. Workers and
  providers receive immutable prepared work and never live FreeCAD/Qt authority.
- The reusable tester keeps authenticated checkout-bound control, semantic UI
  discovery, plain cyan in-application cursor behavior, native file lifecycle,
  screenshot receipts, bounded timeouts, and zero physical input injection.
- The VC-DG-0 profile consumes the tester without copying it. Generic tester
  success is infrastructure evidence only. It earns zero domain completion
  credit and zero physics, solver, numerical, verification, qualification, or
  domain-result-publication credit. A passing consumer profile earns VC-DG-0
  visible-profile credit only and no later domain credit.
- FEM execution, verification, currentness, authorization, publication,
  qualification, and cross-platform packaging remain separate gates.
- All concurrent dirty or non-ancestor work is preserved and receives no credit
  until independently reconciled, committed, packaged where applicable, and
  rerun from one exact tree.

## Dependency cutline established by this freeze

The immediate order is:

1. keep the reusable tester generic and add the VC-DG-0 consumer profile plus an
   exact merged-tree package receipt;
2. use the bounded Native authority foundation—not full Native-host closure—as
   the prerequisite for the current FEM/CalculiX G2 tranche;
3. close full Native-host durability only after the required G2 and G4 evidence
   is accepted;
4. then continue the retained McMaster, low-order Aero, X1/X2/X4, and later
   VC-DG tranches in the governed order.

This cutline removes the prior circular reading while preserving every existing
capability and authority boundary.
