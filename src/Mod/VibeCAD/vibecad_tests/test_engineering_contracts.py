# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import annotations

import json
import typing
from collections.abc import Mapping as RuntimeMapping
from dataclasses import FrozenInstanceError, replace

import pytest
import VibeCADEngineeringContracts as engineering_contracts
from VibeCADAnalysisContracts import AnalysisContractError
from VibeCADEngineeringContracts import (
    ContentDescriptor,
    EngineeringIdentity,
    EngineeringResultEnvelope,
    FindingEnvelope,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    canonical_payload,
)

DOMAINS = ("native", "fem", "aero", "manufacture", "assembly", "robot")


def _identity(kind: str, value: str, owner: str = "vibecad") -> EngineeringIdentity:
    return EngineeringIdentity("vibecad", owner, kind, value, "1")


def _result(domain: str, *, minor: int = 0) -> EngineeringResultEnvelope:
    source = _identity("document", f"doc-{domain}", "native")
    result = _identity("result", f"result-{domain}", domain)
    activity = _identity("activity", f"activity-{domain}", domain)
    artifact = ContentDescriptor(
        "application/json", "sha256", "a" * 64, 17, "primary-result", "v1"
    )
    finding = FindingEnvelope(
        f"finding-{domain}", "rule-1", "vibecad-verifier", domain,
        "pass", "note", "bounded", "Representative bounded finding",
        (source,), (artifact,), "", "current", "engineering-evidence-only",
    )
    graph = ProvenanceGraph(
        f"graph-{domain}",
        (
            ProvenanceNode(source.canonical, "entity", canonical_payload({"domain": domain})),
            ProvenanceNode(activity.canonical, "activity", canonical_payload({"adapter": domain})),
            ProvenanceNode(result.canonical, "entity", canonical_payload({"status": "solved"})),
            ProvenanceNode("agent:vibecad", "agent", canonical_payload({"role": "host"})),
        ),
        (
            ProvenanceEdge("edge-used", "used", activity.canonical, source.canonical),
            ProvenanceEdge("edge-generated", "generated", result.canonical, activity.canonical),
            ProvenanceEdge("edge-associated", "associated", activity.canonical, "agent:vibecad", "runtime"),
        ),
    )
    return EngineeringResultEnvelope(
        1, minor, result, activity, domain, f"adapter.{domain}", "attempt-1",
        "solved", "model-unqualified", "current", "unpublished", source,
        "b" * 64, (artifact,), canonical_payload({"count": 1}), (finding,),
        graph, canonical_payload({"domain_specific": {"domain": domain}}),
    )


def _finding_profile(
    domain: str = "fem", *, minor: int = 0
):
    rule = engineering_contracts.FindingRuleProfile(
        rule_id="rule-1",
        source_id="vibecad-verifier",
        codes=("warning", "bounded"),
        verdicts=("pass", "fail"),
        severities=("warning", "note"),
        currentness=("stale", "current"),
        claim_ceilings=("diagnostic-only", "engineering-evidence-only"),
    )
    return engineering_contracts.FindingTaxonomyProfile(
        contract_major=1,
        contract_minor=minor,
        profile_id=f"vibecad.{domain}.findings",
        domain=domain,
        rules=(rule,),
    )


@pytest.mark.parametrize("domain", DOMAINS)
def test_cross_domain_round_trip_preserves_opaque_payload_and_axes(domain: str) -> None:
    original = _result(domain)
    encoded = original.to_canonical_json()
    restored = EngineeringResultEnvelope.from_canonical_json(encoded)

    assert restored == original
    assert encoded == restored.to_canonical_json()
    assert restored.execution_status == "solved"
    assert restored.verification_verdict == "model-unqualified"
    assert restored.currentness == "current"
    assert restored.publication_state == "unpublished"
    assert restored.domain_payload.to_value()["domain_specific"]["domain"] == domain


def test_additive_minor_version_is_readable_but_unknown_major_is_refused() -> None:
    assert EngineeringResultEnvelope.from_canonical_json(
        _result("fem", minor=7).to_canonical_json()
    ).contract_minor == 7
    value = json.loads(_result("fem").to_canonical_json())
    value["contract_major"] = 2
    with pytest.raises(AnalysisContractError, match="major version"):
        EngineeringResultEnvelope.from_dict(value)


def test_identity_types_cannot_be_substituted() -> None:
    _identity("result", "one").require_same_type(_identity("result", "two"))
    with pytest.raises(AnalysisContractError, match="not substitutable"):
        _identity("result", "one").require_same_type(_identity("document", "one"))


def test_duplicate_graph_and_finding_ids_are_refused() -> None:
    result = _result("assembly")
    node = result.provenance.nodes[0]
    with pytest.raises(AnalysisContractError, match="node IDs"):
        ProvenanceGraph("duplicate", (node, node), ())
    finding = result.findings[0]
    with pytest.raises(AnalysisContractError, match="finding IDs"):
        EngineeringResultEnvelope(
            result.contract_major, result.contract_minor, result.result_id,
            result.activity_id, result.domain, result.adapter_id,
            result.provider_attempt_id, result.execution_status,
            result.verification_verdict, result.currentness,
            result.publication_state, result.source_identity,
            result.dependency_digest, result.artifacts, result.summary_metrics,
            (finding, finding), result.provenance, result.domain_payload,
        )


@pytest.mark.parametrize("payload", (
    {"api_token": "do-not-store"},
    {"nested": {"password": "do-not-store"}},
    {"credential-id": "do-not-store"},
))
def test_secret_bearing_payload_fields_are_refused(payload) -> None:
    with pytest.raises(AnalysisContractError, match="Secret-bearing"):
        canonical_payload(payload)


def test_non_json_live_objects_and_non_finite_values_are_refused() -> None:
    with pytest.raises(AnalysisContractError):
        canonical_payload({"document": object()})
    with pytest.raises(AnalysisContractError):
        canonical_payload({"metric": float("nan")})


@pytest.mark.parametrize("path", ("C:\\Temp\\solver.out", "/tmp/solver.out", "\\\\host\\share\\result"))
def test_absolute_paths_are_refused_from_common_payloads(path: str) -> None:
    with pytest.raises(AnalysisContractError, match="Absolute paths"):
        canonical_payload({"working_path": path})


def test_legacy_canonical_payload_accepts_wide_payload_under_byte_limit() -> None:
    value = [None] * engineering_contracts.MAX_CONTRACT_JSON_NODES

    payload = canonical_payload(value)

    assert payload.to_value() == value
    assert len(payload.encoded.encode("utf-8")) < engineering_contracts.MAX_ENVELOPE_BYTES


def test_dangling_provenance_edge_is_refused() -> None:
    node = ProvenanceNode("entity:one", "entity", canonical_payload({}))
    with pytest.raises(AnalysisContractError, match="existing nodes"):
        ProvenanceGraph(
            "graph", (node,),
            (ProvenanceEdge("edge", "derived", "entity:one", "missing"),),
        )


def test_finding_profile_is_immutable_and_serializes_deterministically() -> None:
    profile = _finding_profile()
    equivalent_rule = engineering_contracts.FindingRuleProfile(
        rule_id="rule-1",
        source_id="vibecad-verifier",
        codes=("bounded", "warning"),
        verdicts=("fail", "pass"),
        severities=("note", "warning"),
        currentness=("current", "stale"),
        claim_ceilings=("engineering-evidence-only", "diagnostic-only"),
    )
    equivalent = engineering_contracts.FindingTaxonomyProfile(
        1, 0, "vibecad.fem.findings", "fem", (equivalent_rule,)
    )

    encoded = profile.to_canonical_json()

    assert encoded == equivalent.to_canonical_json()
    assert engineering_contracts.FindingTaxonomyProfile.from_canonical_json(encoded) == profile
    with pytest.raises(FrozenInstanceError):
        profile.domain = "aero"
    with pytest.raises(FrozenInstanceError):
        profile.rules[0].codes = ("unbounded",)


def test_finding_profile_refuses_unknown_major() -> None:
    value = json.loads(_finding_profile().to_canonical_json())
    value["contract_major"] = 2

    with pytest.raises(AnalysisContractError, match="major version"):
        engineering_contracts.FindingTaxonomyProfile.from_dict(value)


def test_finding_profile_requires_unique_rule_keys_and_allowed_values() -> None:
    profile = _finding_profile()
    rule = profile.rules[0]
    duplicate_key = replace(rule, codes=("another-code",))
    with pytest.raises(AnalysisContractError, match="rule keys must be unique"):
        replace(profile, rules=(rule, duplicate_key))
    with pytest.raises(AnalysisContractError, match="codes values must be unique"):
        replace(rule, codes=("bounded", " bounded "))


def test_finding_profile_bounds_rule_value_counts_rule_counts_and_bytes() -> None:
    profile = _finding_profile()
    rule = profile.rules[0]
    too_many_values = tuple(
        f"code-{index}"
        for index in range(engineering_contracts.MAX_FINDING_PROFILE_VALUES_PER_FIELD + 1)
    )
    with pytest.raises(AnalysisContractError, match="codes exceeds"):
        replace(rule, codes=too_many_values)
    with pytest.raises(AnalysisContractError, match="rules exceeds"):
        replace(
            profile,
            rules=(rule,) * (engineering_contracts.MAX_FINDING_PROFILE_RULES + 1),
        )
    with pytest.raises(AnalysisContractError, match="bounded envelope size"):
        replace(profile, profile_id="x" * (engineering_contracts.MAX_ENVELOPE_BYTES + 1))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("api_token", "do-not-store", "Secret-bearing"),
        ("apiToken", "do-not-store", "Secret-bearing"),
        ("clientSecret", "do-not-store", "Secret-bearing"),
        ("authorization", "Bearer do-not-store", "Credential-bearing"),
        ("authHeader", "Bearer do-not-store", "Credential-bearing"),
        ("passwords", "do-not-store", "Credential-bearing"),
        ("secrets", "do-not-store", "Credential-bearing"),
        ("accessTokens", "do-not-store", "Credential-bearing"),
        ("awsCredentials", "do-not-store", "Credential-bearing"),
        ("authHeaders", "Bearer do-not-store", "Credential-bearing"),
        ("apiKeys", "do-not-store", "Credential-bearing"),
        ("privateKeys", "do-not-store", "Credential-bearing"),
        ("futureCachePath", "   C:\\Temp\\profile.json", "Absolute paths"),
        ("future_cache_path", "   /tmp/profile.json", "Absolute paths"),
        ("futureCacheUri", "  file:///tmp/profile.json", "file: URI"),
    ),
)
def test_future_extensions_screen_credentials_paths_and_file_uris(
    field: str, value: str, message: str
) -> None:
    payload = json.loads(_finding_profile(minor=1).to_canonical_json())
    payload[field] = value

    with pytest.raises(AnalysisContractError, match=message):
        engineering_contracts.FindingTaxonomyProfile.from_dict(payload)


def test_finding_profile_validation_requires_exact_domain_and_rule_key() -> None:
    finding = _result("fem").findings[0]
    profile = _finding_profile("fem")

    assert engineering_contracts.validate_finding_against_profile(finding, profile) is finding
    with pytest.raises(AnalysisContractError, match="domain must exactly match"):
        engineering_contracts.validate_finding_against_profile(
            replace(finding, domain="fem.subdomain"), profile
        )
    for changed in (
        replace(finding, source_id="vibecad-verifier.child"),
        replace(finding, rule_id="rule-1.child"),
    ):
        with pytest.raises(AnalysisContractError, match="rule key"):
            engineering_contracts.validate_finding_against_profile(changed, profile)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("code", "BOUNDED"),
        ("verdict", "PASS"),
        ("severity", "NOTE"),
        ("currentness", "CURRENT"),
        ("claim_ceiling", "ENGINEERING-EVIDENCE-ONLY"),
    ),
)
def test_finding_profile_validation_checks_every_opt_in_axis(
    field: str, value: str
) -> None:
    finding = replace(_result("fem").findings[0], **{field: value})

    with pytest.raises(AnalysisContractError, match=field):
        engineering_contracts.validate_finding_against_profile(
            finding, _finding_profile("fem")
        )


def test_finding_profile_validation_remains_opt_in_for_legacy_findings() -> None:
    legacy = replace(_result("fem").findings[0], code="legacy-unregistered")

    assert FindingEnvelope.from_dict(legacy.to_dict()) == legacy
    with pytest.raises(AnalysisContractError, match="code"):
        engineering_contracts.validate_finding_against_profile(
            legacy, _finding_profile("fem")
        )


class _GuardedUnendingIterator:
    def __init__(self, factory, maximum_calls: int) -> None:
        self._factory = factory
        self._maximum_calls = maximum_calls
        self.calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.calls >= self._maximum_calls:
            raise AssertionError("iterator was consumed beyond the required bound")
        self.calls += 1
        return self._factory(self.calls)


class _BrokenIterator:
    def __iter__(self):
        return self

    def __next__(self):
        raise RuntimeError("malformed iterator")


def _nested_mapping(depth: int):
    root = {}
    cursor = root
    for index in range(depth):
        child = {}
        cursor[f"level_{index}"] = child
        cursor = child
    return root


def test_future_extensions_reject_cycles_and_depth() -> None:
    cyclic = {"safe": "value"}
    cyclic["cycle"] = cyclic
    for invalid, message in (
        (cyclic, "cyclic"),
        (_nested_mapping(500), "depth"),
    ):
        payload = json.loads(_finding_profile(minor=1).to_canonical_json())
        payload["futureExtension"] = invalid
        with pytest.raises(AnalysisContractError, match=message):
            engineering_contracts.FindingTaxonomyProfile.from_dict(payload)


def test_profile_rejects_aggregate_node_count_during_construction() -> None:
    values = tuple(
        f"value-{index}"
        for index in range(engineering_contracts.MAX_FINDING_PROFILE_VALUES_PER_FIELD)
    )
    per_rule_nodes = 1 + 2 + 5 * (1 + len(values))
    rule_count = engineering_contracts.MAX_CONTRACT_JSON_NODES // per_rule_nodes + 1
    rules = tuple(
        engineering_contracts.FindingRuleProfile(
            rule_id=f"rule-{index}",
            source_id="vibecad-verifier",
            codes=values,
            verdicts=values,
            severities=values,
            currentness=values,
            claim_ceilings=values,
        )
        for index in range(rule_count)
    )

    with pytest.raises(AnalysisContractError, match="node count"):
        engineering_contracts.FindingTaxonomyProfile(
            contract_major=1,
            contract_minor=0,
            profile_id="aggregate-node-limit",
            domain="fem",
            rules=rules,
        )


def test_profile_rejects_embedded_depth_during_construction() -> None:
    rule = replace(
        _finding_profile().rules[0],
        extensions={
            "futureDeep": _nested_mapping(
                engineering_contracts.MAX_CONTRACT_JSON_DEPTH - 2
            )
        },
    )

    with pytest.raises(AnalysisContractError, match="depth"):
        engineering_contracts.FindingTaxonomyProfile(
            contract_major=1,
            contract_minor=1,
            profile_id="aggregate-depth-limit",
            domain="fem",
            rules=(rule,),
        )


def test_deep_profile_json_normalizes_parser_recursion_failures() -> None:
    encoded = _finding_profile(minor=1).to_canonical_json()
    deeply_nested = '{"next":' * 1100 + "null" + "}" * 1100
    encoded = encoded[:-1] + ',"futureDeepValue":' + deeply_nested + "}"

    with pytest.raises(AnalysisContractError, match="depth"):
        engineering_contracts.FindingTaxonomyProfile.from_canonical_json(encoded)


@pytest.mark.parametrize(
    ("target", "limit"),
    (
        ("values", engineering_contracts.MAX_FINDING_PROFILE_VALUES_PER_FIELD),
        ("rules", engineering_contracts.MAX_FINDING_PROFILE_RULES),
    ),
)
def test_profile_iterators_stop_after_limit_plus_one(target: str, limit: int) -> None:
    profile = _finding_profile()
    factory = (
        (lambda index: f"code-{index}")
        if target == "values"
        else (lambda _index: profile.rules[0])
    )
    iterator = _GuardedUnendingIterator(factory, limit + 1)

    with pytest.raises(AnalysisContractError, match=f"bounded {target[:-1]} count"):
        if target == "values":
            replace(profile.rules[0], codes=iterator)
        else:
            replace(profile, rules=iterator)
    assert iterator.calls == limit + 1


@pytest.mark.parametrize("target", ("values", "rules"))
def test_profile_iterator_runtime_errors_are_normalized(target: str) -> None:
    profile = _finding_profile()

    with pytest.raises(AnalysisContractError):
        if target == "values":
            replace(profile.rules[0], codes=_BrokenIterator())
        else:
            replace(profile, rules=_BrokenIterator())


@pytest.mark.parametrize(
    ("original", "duplicate"),
    (
        ('"contract_major":1', '"contract_major":1,"contract_major":1'),
        ('"rule_id":"rule-1"', '"rule_id":"rule-1","rule_id":"rule-1"'),
    ),
)
def test_finding_profile_json_rejects_duplicate_keys_at_every_level(
    original: str, duplicate: str
) -> None:
    encoded = _finding_profile().to_canonical_json()
    duplicated = encoded.replace(original, duplicate, 1)
    assert duplicated != encoded

    with pytest.raises(AnalysisContractError, match="duplicate JSON object key"):
        engineering_contracts.FindingTaxonomyProfile.from_canonical_json(duplicated)


@pytest.mark.parametrize("location", ("profile", "rule"))
def test_current_minor_profile_rejects_unknown_fields_as_typos(location: str) -> None:
    payload = json.loads(_finding_profile().to_canonical_json())
    target = payload if location == "profile" else payload["rules"][0]
    target["futureHint"] = {"mode": "typo"}

    with pytest.raises(AnalysisContractError, match="unknown field"):
        engineering_contracts.FindingTaxonomyProfile.from_dict(payload)


def test_future_minor_extensions_are_preserved_immutably_and_in_equality() -> None:
    payload = json.loads(_finding_profile().to_canonical_json())
    payload["contract_minor"] = 1
    payload["futureProfileHint"] = {
        "mode": "additive",
        "nested": {"levels": [1, 2, 3]},
    }
    payload["rules"][0]["futureRuleHint"] = {
        "review": "metadata-only",
        "weight": 3,
    }
    encoded = canonical_payload(payload).encoded

    restored = engineering_contracts.FindingTaxonomyProfile.from_canonical_json(encoded)

    assert restored.to_canonical_json() == encoded
    assert restored.extensions.to_value() == {
        "futureProfileHint": payload["futureProfileHint"]
    }
    assert restored.rules[0].extensions.to_value() == {
        "futureRuleHint": payload["rules"][0]["futureRuleHint"]
    }
    assert engineering_contracts.FindingTaxonomyProfile.from_canonical_json(encoded) == restored
    finding = _result("fem").findings[0]
    with pytest.raises(AnalysisContractError, match="newer contract minor"):
        engineering_contracts.validate_finding_against_profile(finding, restored)

    decoded = restored.extensions.to_value()
    decoded["futureProfileHint"]["mode"] = "mutated"
    assert restored.extensions.to_value()["futureProfileHint"]["mode"] == "additive"
    changed = json.loads(encoded)
    changed["futureProfileHint"]["mode"] = "different"
    assert engineering_contracts.FindingTaxonomyProfile.from_dict(changed) != restored


@pytest.mark.parametrize(
    ("target", "collision"),
    (
        ("profile", {"domain": "collision"}),
        ("rule", {"codes": ["collision"]}),
    ),
)
def test_profile_extensions_reject_known_field_collisions(
    target: str, collision: dict
) -> None:
    profile = _finding_profile(minor=1)
    extensions = canonical_payload(collision)

    with pytest.raises(AnalysisContractError, match="known field"):
        if target == "profile":
            replace(profile, extensions=extensions)
        else:
            replace(profile.rules[0], extensions=extensions)


class _ChangingExtensionMapping(RuntimeMapping):
    def __iter__(self):
        return iter(("future",))

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str):
        if key == "future":
            return "metadata-only"
        raise KeyError(key)

    def items(self):
        return iter((("rule_id", "OVERRIDE"),))


def test_profile_extensions_reject_collision_from_same_mapping_snapshot() -> None:
    rule = _finding_profile(minor=1).rules[0]

    with pytest.raises(AnalysisContractError, match="known field"):
        replace(rule, extensions=_ChangingExtensionMapping())


class _ItemsOnlyCredentialMapping(RuntimeMapping):
    def __init__(self, stable: dict) -> None:
        self._stable = stable

    def __iter__(self):
        return iter(self._stable)

    def __len__(self) -> int:
        return len(self._stable)

    def __getitem__(self, key: str):
        return self._stable[key]

    def items(self):
        return iter((*self._stable.items(), ("authHeader", "Bearer do-not-store")))


@pytest.mark.parametrize("target", ("profile", "rule"))
def test_profile_from_dict_uses_one_exact_mapping_items_snapshot(target: str) -> None:
    payload = json.loads(_finding_profile(minor=1).to_canonical_json())
    if target == "profile":
        source = _ItemsOnlyCredentialMapping(payload)
    else:
        payload["rules"][0] = _ItemsOnlyCredentialMapping(payload["rules"][0])
        source = payload

    with pytest.raises(AnalysisContractError, match="Credential-bearing"):
        engineering_contracts.FindingTaxonomyProfile.from_dict(source)


class _MutatingPairItemsMapping(_ItemsOnlyCredentialMapping):
    def items(self):
        credential_pair = ["authHeaders", "Bearer do-not-store"]
        yield credential_pair
        credential_pair[0] = "futureHint"
        yield from self._stable.items()


@pytest.mark.parametrize("target", ("profile", "rule"))
def test_profile_from_dict_snapshots_each_mapping_pair_before_resuming(
    target: str,
) -> None:
    payload = json.loads(_finding_profile(minor=1).to_canonical_json())
    if target == "profile":
        source = _MutatingPairItemsMapping(payload)
    else:
        payload["rules"][0] = _MutatingPairItemsMapping(payload["rules"][0])
        source = payload

    with pytest.raises(AnalysisContractError, match="Credential-bearing"):
        engineering_contracts.FindingTaxonomyProfile.from_dict(source)


class _StaticItemsMapping(RuntimeMapping):
    def __init__(self, items: tuple) -> None:
        self._items = items

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 0

    def __getitem__(self, key: str):
        raise KeyError(key)

    def items(self):
        return iter(self._items)


@pytest.mark.parametrize(
    ("items", "message"),
    (
        ((("contract_major", 1, "unexpected"),), "malformed mapping item"),
        (
            (("contract_major", 1), ("contract_major", 1)),
            "duplicate mapping keys",
        ),
        (((1, 1),), "keys must be strings"),
    ),
)
def test_profile_from_dict_rejects_ambiguous_mapping_item_streams(
    items: tuple, message: str
) -> None:
    with pytest.raises(AnalysisContractError, match=message):
        engineering_contracts.FindingTaxonomyProfile.from_dict(
            _StaticItemsMapping(items)
        )


def test_engineering_contract_facade_preserves_public_mapping_identity() -> None:
    assert engineering_contracts.Mapping is typing.Mapping
    assert not hasattr(engineering_contracts, "dataclass_field")


def test_profile_aggregate_budget_is_checked_before_full_serialization(monkeypatch) -> None:
    base_rule = _finding_profile().rules[0]
    half_budget = "x" * (engineering_contracts.MAX_ENVELOPE_BYTES // 2)
    first = replace(base_rule, rule_id="first-" + half_budget)
    second = replace(base_rule, rule_id="second-" + half_budget)
    rules = _GuardedUnendingIterator(
        lambda index: first if index == 1 else second, 2
    )

    def fail_if_fully_serialized(_self):
        raise AssertionError("aggregate profile was fully constructed")

    monkeypatch.setattr(
        engineering_contracts.FindingTaxonomyProfile,
        "to_dict",
        fail_if_fully_serialized,
    )
    with pytest.raises(AnalysisContractError, match="bounded envelope size"):
        engineering_contracts.FindingTaxonomyProfile(
            contract_major=1,
            contract_minor=0,
            profile_id="aggregate-budget",
            domain="fem",
            rules=rules,
        )
    assert rules.calls == 2
