# Technical White Paper 1

# Direct-Geometry, No-Body-Fitted-Meshing Analysis for VibeCAD

**Document type:** Standalone implementation white paper  
**Target repository:** VibeCAD  
**Primary audience:** VibeCAD maintainers, FreeCAD/Python developers, solver-integration developers, engineering-validation developers, and automated coding agents  
**Implementation status:** Proposed repository build specification  
**Normative language:** “MUST,” “SHOULD,” and “MAY” describe required, recommended, and optional implementation behavior

---

## Executive summary

VibeCAD SHOULD provide a direct-geometry analysis workflow in which a user can solve selected structural, thermal, and flow problems without manually exporting CAD, repairing a second geometry representation, generating a geometry-conforming mesh, and then mapping results back into the design environment.

The intended user workflow is:

```text
Open or create CAD
→ define physics
→ select geometry semantically
→ preview loads and boundaries
→ run analysis
→ inspect qualified results
→ modify CAD
→ rerun without a manual meshing round trip
```

This capability is called **direct-geometry analysis** in this paper.

Direct-geometry analysis does not eliminate all numerical discretization. Immersed, unfitted, finite-cell, embedded-boundary, and lattice methods normally place the geometry inside a background grid, mesh, lattice, or other computational representation. The product promise is therefore:

> VibeCAD eliminates the mandatory user-managed body-fitted-meshing and geometry-conversion loop for analysis classes that have a qualified direct-geometry method.

This implementation MUST be additive to the existing VibeCAD Analysis Runtime. It MUST NOT create a second job system, result publication system, CAD mutation authority, or artifact store.

Existing CalculiX, Elmer, OpenFOAM, CfdOF, low-order Aero, and other working solver integrations remain important. They SHOULD serve as:

- production analysis routes where already qualified;
- reference implementations;
- independent comparison solvers;
- fallback routes;
- qualification oracles for new direct-geometry methods.

The initial supported VibeCAD scope SHOULD be deliberately bounded:

1. linear static elasticity;
2. steady linear thermal conduction;
3. simple closed solid geometry;
4. semantic loads and constraints;
5. result fields and quantities of interest;
6. independent comparison against an established conforming solver;
7. optional embedded-flow evaluation only after the structural and thermal path is complete.

Advanced nonlinear mechanics, contact, fracture, turbulence, fluid–structure interaction, generalized multiphysics, and automated multi-method routing are outside the required VibeCAD scope.

---

# 1. Product requirements

## 1.1 User-facing objective

A VibeCAD user MUST be able to:

1. open a supported FreeCAD/VibeCAD model;
2. choose an analysis domain;
3. define material and operating conditions;
4. identify loads, supports, sources, sinks, inlets, outlets, or probes using stable semantic selectors;
5. preview the resolved geometry;
6. select an available analysis method;
7. start, observe, cancel, retry, save, and reload an analysis;
8. view result fields and quantities of interest;
9. see whether the result is current, stale, qualified, provisional, or unsupported;
10. modify the CAD geometry and rerun without manually rebuilding a body-fitted mesh when the selected method supports direct geometry.

## 1.2 Development and test objective

Every delivered feature MUST be testable through the repository’s visible one-click development environment.

The implementation is not complete if it is only exercised through isolated unit tests or a hidden script. A builder MUST be able to demonstrate:

- launching the application from the one-click developer launcher;
- observing an independent cyan agent cursor;
- opening each relevant analysis page or tab;
- creating or loading a model;
- defining a scenario;
- previewing selectors;
- saving the project;
- closing and reopening it;
- starting and cancelling a solve;
- opening result fields;
- inspecting qualification and currentness;
- changing geometry and observing stale-state behavior.

Automated tests remain mandatory, but visible end-to-end testing is an additional release gate.

## 1.3 Open-capable completion objective

VibeCAD MUST have a complete route that does not require:

- a paid solver;
- a subscription;
- a commercial cloud account;
- a proprietary geometry format;
- a noncommercial-only dependency.

Commercial connectors MAY be added as optional user-installed integrations, but they MUST NOT be required for:

- default installation;
- automated tests;
- roadmap completion;
- a supported core workflow;
- reproduction of qualification evidence.

---

# 2. Technical terminology

A builder MUST use the following distinctions consistently.

## 2.1 Authoritative geometry

The accepted FreeCAD/OCCT document state is the authoritative design geometry.

Authoritative geometry includes:

- document revision;
- body and part identities;
- placements;
- units;
- coordinate frames;
- parameters;
- assembly relationships;
- accepted user mutations.

A background grid, tessellation, STL, level set, sparse volume, or solver mesh is not authoritative design geometry.

## 2.2 Derived geometry representation

A derived geometry representation is an immutable analysis artifact computed from authoritative geometry.

Examples:

- controlled surface tessellation;
- occupancy grid;
- signed-distance field;
- unsigned-distance field;
- level set;
- OpenVDB sparse grid;
- cut-cell intersection data;
- background finite-element grid;
- lattice domain;
- particle cloud.

Every representation MUST record its source revision and approximation settings.

## 2.3 Body-fitted or conforming mesh

A body-fitted mesh approximates and conforms to the modeled boundary.

Examples include:

- a tetrahedral mesh generated for CalculiX;
- a conforming finite-element mesh for Elmer;
- an OpenFOAM volume mesh generated through castellating and snapping operations.

OpenFOAM’s `snappyHexMesh` begins from a background mesh and then castellates, snaps, and optionally adds layers to produce a body-conforming mesh. It remains valuable, but it is not the direct-geometry method defined here. [OpenFOAM `snappyHexMesh` documentation](https://doc.openfoam.com/2606/tools/pre-processing/mesh/generation/snappyhexmesh/)

## 2.4 Unfitted or immersed method

An unfitted or immersed method represents a physical boundary inside a computational background mesh that does not conform to that boundary.

Such methods commonly require:

- cut-cell classification;
- integration over partial cells;
- weak or specialized boundary enforcement;
- stabilization;
- small-cut conditioning controls;
- representation and resolution studies.

The finite-cell method, for example, combines an embedding or fictitious-domain concept with finite elements and can use BREP or voxelized geometry. [Finite-cell method publication record](https://portal.fis.tum.de/de/publications/the-finite-cell-method-for-three-dimensional-problems-of-solid-me/)

## 2.5 Embedded-boundary CFD

Embedded-boundary CFD represents solid boundaries inside a fluid background mesh or grid without first creating a fully body-fitted fluid mesh.

It is a flow method. It is not a structural solver.

## 2.6 True meshfree method

A true meshfree method uses particles or points rather than a conventional element or control-volume mesh.

Examples include:

- smoothed particle hydrodynamics;
- peridynamics;
- selected reproducing-kernel methods.

These are separate method families and are not required for the initial VibeCAD implementation.

## 2.7 Numerical method, solver, and provider

These are different entities:

- **Numerical method:** finite-cell, CutFEM, conforming FEM, embedded-boundary CFD, LBM, and so forth.
- **Solver:** a concrete implementation of governing equations using a method.
- **Provider:** the process or environment that executes a prepared scenario.

A local Kratos process, for example, is a provider executing a Kratos solver configured for an embedded CFD method.

---

# 3. Scope and non-scope

## 3.1 Required initial scope

The first qualified VibeCAD release SHOULD support:

### Structural

- three-dimensional linear elasticity;
- homogeneous isotropic material;
- small displacement and strain;
- prescribed displacement;
- fixed support;
- distributed traction or pressure;
- gravity or body force if supported;
- displacement field;
- strain field;
- stress field;
- reaction balance;
- selected quantities of interest.

### Thermal

- steady linear conduction;
- isotropic conductivity;
- prescribed temperature;
- heat flux;
- volumetric heat source;
- convection boundary if independently verified;
- temperature field;
- heat-flux field;
- energy balance;
- selected quantities of interest.

### Geometry

- one or more closed solids;
- explicit units;
- explicit placements;
- deterministic tessellation;
- closure check;
- bounded feature size relative to requested resolution;
- stable semantic selectors.

## 3.2 Optional later VibeCAD scope

After structural and thermal qualification:

- a bounded embedded incompressible-flow preview;
- drag or pressure-drop evaluation;
- simple fixed-boundary flow;
- comparison with OpenFOAM;
- no automatic turbulence or compressibility claims.

## 3.3 Explicit non-scope

The VibeCAD implementation is not required to support:

- material plasticity;
- hyperelasticity;
- large deformation;
- general contact;
- crack propagation;
- fracture mechanics;
- fatigue life;
- composite layup failure;
- arbitrary multiphysics coupling;
- moving-boundary CFD;
- full fluid–structure interaction;
- combustion;
- compressible shock flow;
- automatic solver certification;
- autonomous high-confidence method selection.

If a scenario requests unsupported physics, preparation MUST fail before execution and return an actionable finding.

---

# 4. Authority and trust architecture

## 4.1 Required authority boundaries

| Responsibility | Required owner |
|---|---|
| Accepted CAD mutation | Native VibeCAD/FreeCAD host |
| User approval of design changes | Native host and user |
| Scenario preparation | Analysis host and domain adapter |
| Geometry representation generation | Analysis preparation service |
| Semantic selector resolution | Host-side selector service |
| Job lifecycle | Existing Analysis Runtime |
| Artifact identity and storage | Existing immutable artifact service |
| Numerical execution | Provider |
| Physics interpretation | Domain adapter |
| Verification | Verification coordinator |
| Qualification decision | Host-side qualification service |
| Result publication | Existing publication coordinator |
| Scientific visualization | Existing Analyze workspace/viewer |

A provider MUST NOT:

- mutate the open FreeCAD document;
- accept a design proposal;
- resolve an ambiguous surface;
- mark itself qualified;
- publish directly into the accepted model;
- replace the Analysis Runtime lifecycle;
- write untracked output into arbitrary project directories.

## 4.2 End-to-end execution lifecycle

```text
1. User defines analysis intent
2. Host validates physics domain
3. Host resolves semantic selectors
4. User previews and accepts selector resolution
5. Host seals geometry revision and dependencies
6. Representation builder creates immutable derived geometry
7. Domain adapter prepares method-specific scenario
8. Method registry validates compatibility
9. Provider registry chooses an allowed execution provider
10. Provider executes immutable inputs
11. Parser normalizes output
12. Verifier checks numerical and physical invariants
13. Qualification service determines allowed claim ceiling
14. Publication coordinator publishes once
15. Viewer opens fields and evidence
16. Geometry changes mark dependent results stale
```

Every step MUST be observable through structured state and durable artifacts.

---

# 5. Repository implementation architecture

The following existing modules SHOULD remain authoritative integration seams:

```text
src/Mod/VibeCAD/tool_impl/analysis_contracts.py
src/Mod/VibeCAD/tool_impl/analysis_artifacts.py
src/Mod/VibeCAD/tool_impl/analysis_persistence.py
src/Mod/VibeCAD/tool_impl/analysis_verification.py
src/Mod/VibeCAD/tool_impl/analysis_publication.py
src/Mod/VibeCAD/tool_impl/engineering_contracts.py
src/Mod/VibeCAD/VibeCADAnalysisProviders.py
src/Mod/VibeCAD/VibeCADAnalysisNativePublication.py
```

Recommended new modules are:

```text
src/Mod/VibeCAD/tool_impl/analysis_geometry_representation.py
src/Mod/VibeCAD/tool_impl/analysis_selectors.py
src/Mod/VibeCAD/tool_impl/analysis_method_registry.py
src/Mod/VibeCAD/tool_impl/analysis_qualification.py
src/Mod/VibeCAD/tool_impl/analysis_resolution_study.py
src/Mod/VibeCAD/tool_impl/analysis_immersed_structures_adapter.py
src/Mod/VibeCAD/tool_impl/analysis_immersed_thermal_adapter.py
src/Mod/VibeCAD/tool_impl/analysis_embedded_flow_adapter.py
```

If repository conventions require different paths, the module names MAY differ, but the architectural boundaries MUST remain distinct.

---

# 6. Required data contracts

The examples below are illustrative Python contracts. A builder MAY adapt their exact syntax to existing repository conventions, but MUST preserve their semantics.

## 6.1 Geometry representation descriptor

```python
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

RepresentationKind = Literal[
    "brep",
    "surface_tessellation",
    "level_set",
    "signed_distance_field",
    "unsigned_distance_field",
    "sparse_volume",
    "occupancy_grid",
]

@dataclass(frozen=True)
class GeometryRepresentationDescriptor:
    schema_version: str
    representation_id: str
    representation_kind: RepresentationKind

    source_document_id: str
    source_revision_id: str
    source_geometry_digest: str
    source_entity_ids: Tuple[str, ...]

    units: str
    coordinate_frame_id: str
    placement_digest: str

    artifact_id: str
    producing_tool_id: str
    producing_tool_version: str

    surface_tolerance: Optional[float] = None
    voxel_size: Optional[float] = None
    narrow_band_width: Optional[float] = None

    closure_status: Literal[
        "closed",
        "open",
        "unknown",
        "not_applicable",
    ] = "unknown"

    sign_semantics: Literal[
        "inside_negative",
        "inside_positive",
        "unsigned",
        "not_applicable",
    ] = "not_applicable"

    approximation_class: Literal[
        "exact_reference",
        "controlled_approximation",
        "visual_only",
    ] = "controlled_approximation"
```

Required invariants:

- `source_geometry_digest` MUST bind the representation to the exact accepted geometry.
- Units and coordinate frame MUST always be explicit.
- A signed-distance representation MUST NOT have `closure_status="open"` or `"unknown"`.
- Representation tolerances MUST be included in currentness.
- A `visual_only` representation MUST NOT be used for publication-grade solving.

## 6.2 Semantic selector definition

```python
SelectorKind = Literal[
    "named_entity",
    "plane_proximity",
    "point_proximity",
    "normal_direction",
    "bounding_region",
    "material_region",
    "connected_component",
    "user_confirmed_entity_set",
]

@dataclass(frozen=True)
class SelectorDefinition:
    schema_version: str
    selector_id: str
    selector_kind: SelectorKind
    semantic_role: str
    parameters: dict
    source_revision_id: str
```

Example fixed-end selector:

```json
{
  "schema_version": "1.0",
  "selector_id": "fixed-end",
  "selector_kind": "plane_proximity",
  "semantic_role": "fixed_support",
  "parameters": {
    "point": [0.0, 0.0, 0.0],
    "normal": [-1.0, 0.0, 0.0],
    "distance_tolerance": 0.0001,
    "normal_tolerance_degrees": 5.0
  },
  "source_revision_id": "rev-0042"
}
```

## 6.3 Selector resolution

```python
@dataclass(frozen=True)
class SelectorResolution:
    selector_id: str
    source_revision_id: str
    resolved_entity_ids: Tuple[str, ...]
    resolved_geometry_artifact_id: str

    status: Literal[
        "resolved",
        "empty",
        "ambiguous",
        "stale",
        "unsupported",
    ]

    candidate_count: int
    ambiguity_reason: Optional[str]
    resolution_digest: str
```

Execution MUST be blocked when:

- status is not `resolved`;
- the selector resolved against a different source revision;
- the result contains unexpected disconnected regions;
- an ambiguity requires user acceptance.

The provider receives the sealed resolution, not the unresolved semantic query.

## 6.4 Numerical method descriptor

```python
@dataclass(frozen=True)
class NumericalMethodDescriptor:
    schema_version: str
    method_id: str
    method_family: str
    method_version: str

    physics_domains: Tuple[str, ...]
    supported_representation_kinds: Tuple[str, ...]
    supported_boundary_conditions: Tuple[str, ...]
    supported_material_models: Tuple[str, ...]

    basis_order: Optional[int]
    background_cell_type: Optional[str]
    integration_strategy: Optional[str]
    boundary_enforcement: Optional[str]
    stabilization_strategy: Optional[str]

    qualification_record_ids: Tuple[str, ...]
    known_limitations: Tuple[str, ...]
```

Example method identities:

```text
conforming_fem
finite_cell
cutfem
aggregated_unfitted_fem
embedded_boundary_fvm
lattice_boltzmann
```

## 6.5 Prepared analysis

An existing `PreparedAnalysis` SHOULD be extended or composed with:

```python
@dataclass(frozen=True)
class DirectGeometryPreparedInput:
    geometry_representation_id: str
    selector_resolution_ids: Tuple[str, ...]
    numerical_method_id: str
    solver_id: str
    provider_id: str
    resolution_policy_id: str
    qualification_context_id: str
```

Method, solver, and provider MUST be separately stored.

## 6.6 Method qualification record

```python
@dataclass(frozen=True)
class MethodQualificationRecord:
    schema_version: str
    qualification_id: str

    method_id: str
    solver_id: str
    solver_version: str
    runtime_digest: str

    physics_domain: str
    supported_regime: str
    geometry_classes: Tuple[str, ...]
    boundary_condition_classes: Tuple[str, ...]
    material_model_classes: Tuple[str, ...]

    benchmark_artifact_ids: Tuple[str, ...]
    resolution_study_artifact_ids: Tuple[str, ...]
    independent_reference_artifact_ids: Tuple[str, ...]
    experimental_validation_artifact_ids: Tuple[str, ...]

    known_limitations: Tuple[str, ...]
    claim_ceiling: str
```

Qualification MUST be tied to a context of use. The application MUST NOT display a global boolean such as `solver_is_valid=True`.

---

# 7. Geometry representation pipeline

## 7.1 Input sealing

Before generating any derived representation, the host MUST seal:

- source document ID;
- source revision;
- selected bodies;
- body geometry hashes;
- placements;
- units;
- coordinate frame;
- material assignments;
- selector definitions;
- representation settings;
- runtime identity.

The job MUST become stale if any sealed dependency changes.

## 7.2 Tessellation

A deterministic tessellation service SHOULD:

1. tessellate the selected shape at an explicit tolerance;
2. preserve placement and units;
3. calculate triangle count and bounds;
4. detect open edges;
5. detect degenerate triangles;
6. record whether normals are reliable;
7. store the output as an immutable artifact;
8. include the tessellation tolerance in currentness.

The system MUST NOT silently substitute the viewer’s display tessellation if that tessellation does not meet analysis requirements.

## 7.3 Signed and unsigned fields

A signed-distance field MAY be generated only when the geometry is proven closed under the selected tolerance.

Required statuses:

```text
closed_signed_ready
open_unsigned_only
closure_ambiguous
self_intersection_detected
representation_failed
```

OpenVDB is a viable sparse-field representation. Its signed mesh-to-volume conversion requires a closed surface, although the surface does not have to be manifold. [OpenVDB `MeshToVolume` API](https://www.openvdb.org/documentation/doxygen/MeshToVolume_8h.html)

The standard OpenVDB Python bindings expose most grid operations but very little of the C++ tools library. A VibeCAD implementation MUST explicitly package a native tool or binding if it depends on mesh-to-volume functionality. [OpenVDB Python documentation](https://www.openvdb.org/documentation/doxygen/python.html)

## 7.4 Background domain

A background domain builder MUST record:

- geometry bounds;
- padding;
- cell dimensions;
- cell counts;
- cell type;
- refinement regions;
- basis order;
- integration strategy;
- inactive-domain policy;
- memory estimate;
- expected condition-number risks.

For structural or thermal unfitted FEM:

1. classify cells as inside, outside, or cut;
2. retain active cells;
3. integrate the physical portion of cut cells;
4. apply the selected boundary-enforcement formulation;
5. apply required stabilization;
6. assemble and solve;
7. project results into common scientific-field artifacts.

An occupancy-only cell-center test MAY be implemented as a Phase 0 plumbing prototype, but its results MUST be labeled `preview_unqualified`. It MUST NOT be used for stress, failure, or certification claims.

---

# 8. Semantic selector implementation

## 8.1 Why selectors are necessary

Topology identifiers such as `Face7` are not stable engineering intent. They can change when:

- a fillet is added;
- a hole is moved;
- a boolean operation changes topology;
- a feature is reordered;
- a parameter alters face decomposition.

The application SHOULD instead preserve semantic intent such as:

- “the planar end surface at minimum X”;
- “the cylindrical interior wall connected to this inlet”;
- “the region within 2 mm of this datum plane”;
- “the downward-facing surfaces in the mounting group”;
- “the material region named Aluminum.”

## 8.2 Resolution process

For each selector:

1. evaluate the selector against the authoritative host geometry;
2. collect candidates;
3. calculate diagnostic metrics;
4. reject empty results;
5. detect ambiguity;
6. generate a visible preview;
7. require confirmation when policy requires it;
8. seal the resolved region as an immutable artifact;
9. attach the source revision and digest;
10. pass only the sealed resolution to the worker.

## 8.3 Example: cantilever support

A rectangular cantilever has:

- length along positive X;
- one end at `X = 0`;
- downward traction on the opposite end.

Selectors:

```json
[
  {
    "selector_id": "support",
    "selector_kind": "plane_proximity",
    "semantic_role": "fixed_support",
    "parameters": {
      "axis": "x",
      "coordinate": 0.0,
      "distance_tolerance": 0.0001
    }
  },
  {
    "selector_id": "load",
    "selector_kind": "plane_proximity",
    "semantic_role": "traction",
    "parameters": {
      "axis": "x",
      "coordinate": 0.1,
      "distance_tolerance": 0.0001
    }
  }
]
```

The preview MUST show the two resolved regions before execution.

If a later geometry operation creates two separate surfaces at `X = 0`, the scenario MUST become ambiguous or stale rather than applying a support silently to both.

---

# 9. Solver and provider integration

## 9.1 Method registry

The method registry MUST answer:

- Does this method support the requested domain?
- Does it accept this geometry representation?
- Does it support the requested material?
- Does it support each boundary condition?
- Is it available on this platform?
- Does an execution provider exist?
- Is it qualified for the requested claim?
- What fallback is available?

Example decision:

```text
Requested physics: linear static
Geometry: closed solid
Material: isotropic linear elastic
BCs: fixed support + traction
Requested claim: bounded engineering preview

Candidate methods:
- conforming_fem: compatible, qualified
- cutfem: compatible, preview-qualified
- embedded_boundary_fvm: incompatible physics
- lattice_boltzmann: incompatible physics
```

## 9.2 Backend candidates

### CalculiX and Elmer

Use as:

- conforming production routes;
- regression references;
- independent comparison solvers;
- fallbacks.

### CutFEMx

CutFEMx is a specialized candidate for an unfitted finite-element route. Its documented features include runtime quadrature, ghost-penalty support, and MPI. Its current FEniCSx alignment and source-build requirements create a packaging gate. [CutFEMx README](https://github.com/sclaus2/CutFEMx/blob/main/README.md)

Before adoption, the builder MUST prove:

- exact dependency versions;
- Windows installation or bundling;
- reproducible build;
- geometry representation ingestion;
- selector mapping;
- result extraction;
- cancellation;
- deterministic replay;
- license inventory;
- benchmark performance.

### GridapEmbedded

GridapEmbedded is an alternative embedded-FEM candidate supporting level-set and CSG geometry with examples for Poisson, Stokes, and bimaterial elasticity. [GridapEmbedded documentation](https://github.com/gridap/GridapEmbedded.jl)

Before adoption, the builder MUST decide whether a Julia runtime is acceptable for:

- installer size;
- update policy;
- process supervision;
- cross-platform support;
- development environment reproducibility.

### MFEM

MFEM MAY be evaluated as a finite-element library. Selection requires a complete proof of:

- cut-cell or immersed implementation;
- boundary enforcement;
- integration;
- stabilization;
- result mapping;
- packaging.

General finite-element breadth alone is not sufficient evidence of a complete direct-geometry backend. [MFEM repository](https://github.com/mfem/mfem)

### Kratos embedded CFD

Kratos SHOULD be the first broad open candidate evaluated for VibeCAD’s optional embedded-flow preview. Its official FluidDynamicsApplication documentation describes embedded CFD based on distance fields and CutFEM, including support for poor or non-watertight STL sources, moving boundaries, fluid–structure interaction, and conjugate heat transfer. [Kratos FluidDynamicsApplication](https://github.com/KratosMultiphysics/Kratos/blob/master/applications/FluidDynamicsApplication/README.md)

The initial VibeCAD integration MUST remain restricted to a small qualified subset.

### FluidX3D

FluidX3D MUST NOT be a required dependency. Its repository states that it is available for noncommercial use, is not open source, and prohibits commercial use. [FluidX3D repository](https://github.com/ProjectPhysX/FluidX3D)

It MAY be supported through an optional adapter that:

- is disabled by default;
- is never bundled without explicit licensing approval;
- displays the usage restriction;
- is excluded from required tests and completion criteria.

---

# 10. Worked implementation examples

## 10.1 Example A — linear static cantilever

### User intent

> Analyze a 100 mm long aluminum cantilever fixed on its left end with a 100 N downward load on its right end.

### Preparation

```json
{
  "physics_domain": "structural",
  "analysis_type": "linear_static",
  "units": "SI",
  "material": {
    "model": "isotropic_linear_elastic",
    "youngs_modulus_pa": 69000000000.0,
    "poisson_ratio": 0.33,
    "density_kg_m3": 2700.0
  },
  "selectors": {
    "fixed_support": "support",
    "traction_region": "load"
  },
  "load": {
    "type": "resultant_force",
    "vector_n": [0.0, -100.0, 0.0]
  },
  "method_request": {
    "method_family": "unfitted_fem",
    "target_resolution_m": 0.0025
  }
}
```

### Required verification

- compare tip displacement with beam theory where assumptions apply;
- compare with a refined CalculiX model;
- verify total reaction is approximately 100 N opposite the applied load;
- run at least three systematically refined background resolutions;
- inspect whether peak stress is converging or remains geometry-resolution sensitive;
- report geometry, discretization, and solver errors separately where possible.

### Allowed result

A result MAY claim bounded linear-static displacement accuracy after the method is qualified for this geometry and loading class.

Peak stress at a sharp fixed corner SHOULD carry a singularity warning and MUST NOT be represented as a universally converged material-failure value.

## 10.2 Example B — steady thermal bracket

### User intent

> Apply 80°C to the mounting face, convection to the exposed surfaces, and report maximum temperature and total heat flow.

### Preparation requirements

- closed solid;
- conductivity and convection units;
- hot-face selector;
- exposed-surface selector;
- ambient temperature;
- convection coefficient;
- background resolution;
- method qualification for convection boundaries.

### Verification

- total applied heat equals total rejected heat within the context-specific tolerance;
- compare with Elmer;
- perform a resolution study;
- inspect temperature and flux continuity;
- record whether curved boundaries are sufficiently resolved.

## 10.3 Example C — embedded duct-flow preview

### User intent

> Calculate pressure drop and maximum velocity through a fixed internal duct.

### Correct physics route

```text
Domain: CFD
Method: embedded-boundary CFD or conforming FVM
Reference: OpenFOAM
```

The structural and thermal adapters MUST reject this scenario.

Required outputs:

- velocity;
- pressure;
- mass-flow balance;
- pressure drop;
- residual history;
- domain and boundary previews;
- method and resolution identity.

Until an embedded-flow route has independent OpenFOAM comparison evidence, the claim ceiling remains preview-level.

---

# 11. Verification and qualification

## 11.1 Required evidence layers

### Software verification

- contract serialization;
- immutable artifact identity;
- exact currentness;
- save/reopen;
- cancel/recover;
- retry without mutation ambiguity;
- parser regression;
- result publication exactly once;
- cross-platform runtime identity.

### Numerical verification

- analytical or manufactured solution where available;
- benchmark comparison;
- systematic refinement;
- independent solver comparison;
- force, reaction, energy, or mass balance;
- small-cut conditioning diagnostics;
- integration sensitivity;
- geometry-representation sensitivity.

### Validation

For higher claim ceilings:

- relevant experimental data;
- material evidence;
- boundary-condition evidence;
- uncertainty;
- declared context of use.

ASME V&V 10 provides a recognized framework for verification and validation in computational solid mechanics. NASA-STD-7009B provides a broader credibility and acceptance framework for model and simulation use. These standards SHOULD inform the evidence model without implying that VibeCAD is certified merely by referencing them. [ASME V&V 10](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics) and [NASA-STD-7009B](https://standards.nasa.gov/standard/nasa/nasa-std-7009)

## 11.2 Proposed claim ceilings

```text
plumbing_only
preview_unqualified
software_verified
numerically_benchmarked
independently_cross_verified
validated_for_context
```

A provider exit code of zero MUST NOT increase the claim ceiling.

## 11.3 Resolution study

A resolution study SHOULD include at least three systematically related resolutions for an initial trend assessment.

Example:

```text
coarse:  5.0 mm
medium:  2.5 mm
fine:    1.25 mm
```

The study MUST track quantities of interest, such as:

- tip displacement;
- average stress over a finite region;
- total reaction;
- maximum temperature;
- total heat flow;
- pressure drop;
- integrated drag.

A universal numerical tolerance MUST NOT be hardcoded across every physics problem. Acceptance criteria depend on the quantity of interest and context of use. [ASME material on grid-refinement error estimation](https://www.asme.org/codes-standards/publications-information/verification-validation-uncertainty/workshop-on-estimation-of-discretization-errors-based-on-grid-refinement-studies-2017/introduction)

---

# 12. UI and result presentation requirements

The Analyze workspace MUST display:

- physics domain;
- numerical method;
- solver;
- provider;
- geometry representation;
- source document revision;
- representation tolerance or voxel size;
- background resolution;
- basis order where applicable;
- boundary-enforcement strategy;
- stabilization strategy;
- runtime version;
- currentness;
- qualification;
- claim ceiling;
- warnings and known limitations.

Scientific fields SHOULD remain large sidecar artifacts. The accepted `.FCStd` document SHOULD contain only stable metadata, links, user decisions, and compact summaries.

The viewer SHOULD support:

- scalar fields;
- vector fields;
- displacement deformation;
- stress components and invariants;
- temperature;
- heat flux;
- pressure;
- velocity;
- slices;
- probes;
- time or iteration histories;
- quantities of interest;
- comparison overlays;
- method and resolution comparison.

The viewer MUST NOT hide the fact that a field came from a coarse approximate geometry representation.

---

# 13. Implementation work packages

## Work Package VC-DG-0 — visible development environment

Deliver:

- one-click dev launcher;
- independent cyan agent cursor;
- visible tab navigation;
- file save/load;
- deterministic developer state;
- screenshots or trace evidence;
- launcher contract tests.

No direct-geometry feature work is considered fully testable until this package is complete.

## Work Package VC-DG-1 — terminology and contracts

Deliver:

- method/solver/provider separation;
- representation descriptor;
- selector contracts;
- method identity;
- qualification record;
- result metadata integration;
- contract serialization tests.

## Work Package VC-DG-2 — selector resolution

Deliver:

- semantic selector definitions;
- host-side resolution;
- ambiguity handling;
- preview;
- stale detection;
- save/reopen tests.

## Work Package VC-DG-3 — representation pipeline

Deliver:

- BREP sealing;
- deterministic tessellation;
- closure analysis;
- optional SDF or sparse-volume generation;
- artifact storage;
- currentness integration;
- memory estimates;
- failure findings.

## Work Package VC-DG-4 — structural and thermal plumbing prototype

Deliver:

- simple background-grid preparation;
- domain adapter;
- provider execution;
- result parsing;
- sidecar fields;
- low-claim result publication.

All results remain `preview_unqualified`.

## Work Package VC-DG-5 — production candidate integration

Deliver:

- selected open backend;
- exact-build tooling;
- Windows packaging;
- license inventory;
- process supervision;
- cancellation;
- deterministic replay;
- reference-solver adapters.

## Work Package VC-DG-6 — qualification

Deliver:

- analytical tests;
- benchmark suite;
- resolution studies;
- CalculiX/Elmer comparisons;
- force and energy checks;
- declared context of use;
- claim-ceiling promotion only where evidence supports it.

## Work Package VC-DG-7 — optional embedded flow

Deliver only after VC-DG-6:

- Kratos evaluation spike;
- simple fixed-boundary incompressible case;
- OpenFOAM comparison;
- mass and momentum checks;
- explicit preview claim ceiling;
- no required commercial or restricted-use dependency.

---

# 14. Test matrix

| Test category | Required examples |
|---|---|
| Contract | Versioned serialization, unknown fields, malformed IDs |
| Geometry | Closed box, cylinder, filleted bracket, lattice-like geometry, open shell |
| Selector | Stable plane selector, ambiguous selector, empty selector, stale selector |
| Representation | Deterministic tessellation, closure status, unit conversion, placement |
| Structural | Cantilever, tension block, pressure vessel subset, reaction balance |
| Thermal | 1D conduction-equivalent block, mixed boundary slab, energy balance |
| Flow preview | Straight duct, obstacle channel, mass-flow balance |
| Lifecycle | Start, cancel, crash, recover, retry, reopen |
| Currentness | Geometry change, material change, selector change, method change |
| Publication | Publish once, stale result preserved, new result separated |
| Cross-platform | Exact supported Windows runtime and any additional supported platforms |
| GUI | Visible launch, page navigation, save, reload, run, result inspection |
| License | Required core route contains no paid or noncommercial-only dependency |

---

# 15. Definition of done for VibeCAD

The direct-geometry VibeCAD initiative is complete only when all of the following are true:

- [ ] The one-click visible developer GUI can exercise the complete workflow.
- [ ] Accepted CAD remains the only design authority.
- [ ] Geometry representation, numerical method, solver, and provider are separate identities.
- [ ] Semantic selectors replace fragile long-lived face numbers.
- [ ] Derived representations are immutable and provenance-linked.
- [ ] A supported linear structural example runs without manual body-fitted meshing.
- [ ] A supported steady thermal example runs without manual body-fitted meshing.
- [ ] Save, close, reopen, rerun, cancel, recover, and stale-state behavior work.
- [ ] Results show method, representation, resolution, currentness, and qualification.
- [ ] CalculiX or Elmer provides an independent comparison route.
- [ ] Systematic resolution studies exist.
- [ ] Unsupported physics fails before execution.
- [ ] No solver or provider can mutate accepted CAD.
- [ ] No provider can self-publish or self-qualify.
- [ ] No required core path depends on paid or noncommercial-only software.
- [ ] License obligations are documented.
- [ ] Large fields remain sidecar artifacts.
- [ ] All supported contexts have explicit claim ceilings and known limitations.
- [ ] No unresolved issue remains within the declared VibeCAD scope.

---
