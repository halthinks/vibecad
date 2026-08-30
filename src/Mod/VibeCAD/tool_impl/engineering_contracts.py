# SPDX-License-Identifier: LGPL-2.1-or-later

"""Versioned, domain-neutral engineering result and provenance contracts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping as _RuntimeMapping
from dataclasses import dataclass
from dataclasses import field as _dataclass_field
from typing import (  # noqa: UP035 - compatibility facade exports this object
    Any,
    Mapping,
)

from .analysis_contracts import AnalysisContractError, CanonicalJson

ENGINEERING_CONTRACT_MAJOR = 1
ENGINEERING_CONTRACT_MINOR = 0
MAX_ENVELOPE_BYTES = 1024 * 1024
MAX_CONTRACT_JSON_DEPTH = 128
MAX_CONTRACT_JSON_NODES = 65536
MAX_FINDING_PROFILE_RULES = 1024
MAX_FINDING_PROFILE_VALUES_PER_FIELD = 256
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|/|\\\\)")
_SECRET_KEYS = re.compile(
    r"(?:^|[_-])(password|passwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)
_PROFILE_CAMEL_BOUNDARY = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_PROFILE_KEY_SEPARATOR = re.compile(r"[^A-Za-z0-9]+")
_PROFILE_CREDENTIAL_KEYS = re.compile(
    r"(?:^|_)(?:passwords?|passwds?|secrets?|tokens?|credentials?|authorizations?|auth_?headers?|api_?keys?|private_?keys?)(?:$|_)",
    re.IGNORECASE,
)
_PROFILE_FILE_URI = re.compile(r"^file:", re.IGNORECASE)
_FINDING_RULE_VALUE_FIELDS = (
    "codes", "verdicts", "severities", "currentness", "claim_ceilings",
)
_FINDING_RULE_WIRE_FIELDS = (
    "rule_id", "source_id", *_FINDING_RULE_VALUE_FIELDS,
)
_FINDING_RULE_FIELDS = frozenset(_FINDING_RULE_WIRE_FIELDS)
_FINDING_TAXONOMY_FIELDS = frozenset(
    ("contract_major", "contract_minor", "profile_id", "domain", "rules")
)
_FINDING_RULE_RESERVED_FIELDS = _FINDING_RULE_FIELDS | {"extensions"}
_FINDING_TAXONOMY_RESERVED_FIELDS = _FINDING_TAXONOMY_FIELDS | {"extensions"}
_EMPTY_EXTENSIONS = CanonicalJson("{}")
_CURRENT_MINOR_UNKNOWN = (
    "finding taxonomy profile contains unknown field(s) for the current contract minor version."
)


def _text(value: Any, field: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        raise AnalysisContractError(f"{field} must be non-empty.")
    return clean


def _version(major: int, minor: int) -> None:
    if major != ENGINEERING_CONTRACT_MAJOR:
        raise AnalysisContractError(
            f"Unsupported engineering contract major version {major}."
        )
    if type(minor) is not int or minor < 0:
        raise AnalysisContractError("contract_minor must be a non-negative integer.")


def _tuple_of(value: Any, expected: type, field: str) -> tuple[Any, ...]:
    result = tuple(value)
    if any(not isinstance(item, expected) for item in result):
        raise AnalysisContractError(f"{field} contains an invalid value.")
    return result


def _unique(values: tuple[str, ...], field: str) -> None:
    if len(values) != len(set(values)):
        raise AnalysisContractError(f"{field} IDs must be unique.")


def _reject_secrets(value: Any, path: str = "payload") -> None:
    """Preserve the original public canonical-payload screening contract."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _SECRET_KEYS.search(str(key)):
                raise AnalysisContractError(
                    f"Secret-bearing field is forbidden at {path}."
                )
            _reject_secrets(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and _ABSOLUTE_PATH.match(value):
        raise AnalysisContractError(f"Absolute paths are forbidden at {path}.")


def _canonical_payload(value: Any, field: str) -> CanonicalJson:
    _reject_secrets(value, field)
    payload = CanonicalJson.from_value(value)
    if len(payload.encoded.encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise AnalysisContractError(f"{field} exceeds the bounded envelope size.")
    return payload


def _profile_normalized_key(key: str) -> str:
    normalized = _PROFILE_CAMEL_BOUNDARY.sub("_", key)
    return _PROFILE_KEY_SEPARATOR.sub("_", normalized).strip("_")


def _profile_json_snapshot(value: Any, field: str) -> Any:
    """Take one bounded JSON snapshot for strict profile-only processing."""

    active: set[int] = set()
    nodes = 0
    size_hint = 0

    def add_text_size(text: str) -> None:
        nonlocal size_hint
        try:
            size_hint += len(text.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise AnalysisContractError(
                f"{field} could not be serialized as bounded canonical JSON."
            ) from exc
        if size_hint > MAX_ENVELOPE_BYTES:
            raise AnalysisContractError(
                f"{field} exceeds the bounded envelope size."
            )

    def visit(current: Any, current_path: str, depth: int) -> Any:
        nonlocal nodes
        if depth > MAX_CONTRACT_JSON_DEPTH:
            raise AnalysisContractError(
                f"{field} exceeds the maximum JSON depth."
            )
        nodes += 1
        if nodes > MAX_CONTRACT_JSON_NODES:
            raise AnalysisContractError(
                f"{field} exceeds the bounded JSON node count."
            )

        if isinstance(current, str):
            add_text_size(current)
            trimmed = current.strip()
            if _ABSOLUTE_PATH.match(trimmed):
                raise AnalysisContractError(
                    f"Absolute paths are forbidden at {current_path}."
                )
            if _PROFILE_FILE_URI.match(trimmed):
                raise AnalysisContractError(
                    f"file: URI values are forbidden at {current_path}."
                )
            return current

        if isinstance(current, _RuntimeMapping):
            container_id = id(current)
            if container_id in active:
                raise AnalysisContractError(
                    f"{field} contains a cyclic JSON mapping at {current_path}."
                )
            active.add(container_id)
            snapshot: dict[str, Any] = {}
            try:
                try:
                    items = iter(current.items())
                except Exception as exc:
                    raise AnalysisContractError(
                        f"{field} contains a malformed JSON mapping."
                    ) from exc
                while True:
                    try:
                        pair = next(items)
                    except StopIteration:
                        break
                    except Exception as exc:
                        raise AnalysisContractError(
                            f"{field} contains a malformed JSON mapping."
                        ) from exc
                    try:
                        key, item = pair
                    except Exception as exc:
                        raise AnalysisContractError(
                            f"{field} contains a malformed JSON mapping."
                        ) from exc
                    if not isinstance(key, str):
                        raise AnalysisContractError(
                            "Analysis contract JSON object keys must be strings."
                        )
                    if key in snapshot:
                        raise AnalysisContractError(
                            f"{field} contains duplicate JSON object key {key!r}."
                        )
                    normalized = _profile_normalized_key(key)
                    if _SECRET_KEYS.search(normalized):
                        raise AnalysisContractError(
                            f"Secret-bearing field is forbidden at {current_path}."
                        )
                    if _PROFILE_CREDENTIAL_KEYS.search(normalized):
                        raise AnalysisContractError(
                            f"Credential-bearing field is forbidden at {current_path}."
                        )
                    add_text_size(key)
                    snapshot[key] = visit(
                        item, f"{current_path}.{key[:80]}", depth + 1
                    )
            finally:
                active.discard(container_id)
            return snapshot

        if isinstance(current, (list, tuple)):
            container_id = id(current)
            if container_id in active:
                raise AnalysisContractError(
                    f"{field} contains a cyclic JSON sequence at {current_path}."
                )
            active.add(container_id)
            snapshot_list: list[Any] = []
            try:
                try:
                    iterator = iter(current)
                except Exception as exc:
                    raise AnalysisContractError(
                        f"{field} contains a malformed JSON sequence."
                    ) from exc
                index = 0
                while True:
                    try:
                        item = next(iterator)
                    except StopIteration:
                        break
                    except Exception as exc:
                        raise AnalysisContractError(
                            f"{field} contains a malformed JSON sequence."
                        ) from exc
                    snapshot_list.append(
                        visit(item, f"{current_path}[{index}]", depth + 1)
                    )
                    index += 1
            finally:
                active.discard(container_id)
            return snapshot_list

        return current

    try:
        return visit(value, field, 0)
    except AnalysisContractError:
        raise
    except RecursionError as exc:
        raise AnalysisContractError(
            f"{field} exceeds the maximum JSON depth."
        ) from exc


def _profile_canonical_payload(value: Any, field: str) -> CanonicalJson:
    snapshot = _profile_json_snapshot(value, field)
    try:
        payload = CanonicalJson.from_value(snapshot)
    except AnalysisContractError:
        raise
    except (RecursionError, RuntimeError, TypeError, ValueError) as exc:
        raise AnalysisContractError(
            f"{field} could not be serialized as bounded canonical JSON."
        ) from exc
    if len(payload.encoded.encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise AnalysisContractError(f"{field} exceeds the bounded envelope size.")
    return payload


def _profile_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise AnalysisContractError(f"{field} must be a string.")
    return _text(value, field)


def _bounded_iterable(
    value: Any,
    *,
    limit: int,
    field: str,
    limit_message: str,
) -> tuple[Any, ...]:
    try:
        iterator = iter(value)
    except Exception as exc:
        raise AnalysisContractError(f"{field} could not be consumed safely.") from exc
    items: list[Any] = []
    for _index in range(limit + 1):
        try:
            items.append(next(iterator))
        except StopIteration:
            return tuple(items)
        except Exception as exc:
            raise AnalysisContractError(
                f"{field} could not be consumed safely."
            ) from exc
    raise AnalysisContractError(limit_message)


def _profile_values(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, _RuntimeMapping)):
        raise AnalysisContractError(f"{field} must be a sequence of strings.")
    values = _bounded_iterable(
        value,
        limit=MAX_FINDING_PROFILE_VALUES_PER_FIELD,
        field=field,
        limit_message=f"{field} exceeds the bounded value count.",
    )
    if not values:
        raise AnalysisContractError(f"{field} must contain at least one value.")
    normalized = tuple(
        _profile_text(item, f"{field} value") for item in values
    )
    if len(normalized) != len(set(normalized)):
        raise AnalysisContractError(f"{field} values must be unique.")
    return tuple(sorted(normalized))


def _profile_version(major: Any, minor: Any) -> None:
    if type(major) is not int:
        raise AnalysisContractError("contract_major must be an integer.")
    _version(major, minor)


def _bounded_json_mapping(encoded: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(encoded, str):
        raise AnalysisContractError(f"Invalid {field} JSON.")
    try:
        byte_size = len(encoded.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise AnalysisContractError(f"Invalid {field} JSON.") from exc
    if byte_size > MAX_ENVELOPE_BYTES:
        raise AnalysisContractError(f"{field} exceeds the bounded envelope size.")

    def object_pairs_hook(
        pairs: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AnalysisContractError(
                    f"{field} contains duplicate JSON object key {key!r}."
                )
            result[key] = value
        return result

    def reject_constant(_constant: str) -> Any:
        raise AnalysisContractError(
            f"{field} contains a non-finite JSON number."
        )

    try:
        parsed = json.loads(
            encoded,
            object_pairs_hook=object_pairs_hook,
            parse_constant=reject_constant,
        )
    except AnalysisContractError:
        raise
    except RecursionError as exc:
        raise AnalysisContractError(
            f"{field} exceeds the maximum JSON depth."
        ) from exc
    except (TypeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        raise AnalysisContractError(f"Invalid {field} JSON.") from exc
    if not isinstance(parsed, _RuntimeMapping):
        raise AnalysisContractError(f"{field} must be a JSON object.")
    snapshot = _profile_canonical_payload(parsed, field).to_value()
    if not isinstance(snapshot, dict):
        raise AnalysisContractError(f"{field} must be a JSON object.")
    return snapshot


def _bounded_mapping_keys(
    value: Mapping[str, Any], field: str
) -> tuple[str, ...]:
    keys = _bounded_iterable(
        value,
        limit=MAX_CONTRACT_JSON_NODES,
        field=field,
        limit_message=f"{field} exceeds the bounded JSON field count.",
    )
    if any(not isinstance(key, str) for key in keys):
        raise AnalysisContractError(f"{field} keys must be strings.")
    if len(keys) != len(set(keys)):
        raise AnalysisContractError(f"{field} contains duplicate mapping keys.")
    return keys


def _mapping_items_snapshot(value: Any, field: str) -> dict[str, Any]:
    """Read one bounded, exact top-level view from a profile mapping."""

    if not isinstance(value, _RuntimeMapping):
        raise AnalysisContractError(f"{field} must be a mapping.")
    try:
        mapping_items = value.items()
        iterator = iter(mapping_items)
    except Exception as exc:
        raise AnalysisContractError(f"{field} could not be read safely.") from exc
    snapshot: dict[str, Any] = {}
    for index in range(MAX_CONTRACT_JSON_NODES + 1):
        try:
            pair = next(iterator)
        except StopIteration:
            return snapshot
        except Exception as exc:
            raise AnalysisContractError(
                f"{field} could not be read safely."
            ) from exc
        if index == MAX_CONTRACT_JSON_NODES:
            raise AnalysisContractError(
                f"{field} exceeds the bounded JSON field count."
            )
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise AnalysisContractError(
                f"{field} contains a malformed mapping item."
            )
        key, item = pair
        if not isinstance(key, str):
            raise AnalysisContractError(f"{field} keys must be strings.")
        if key in snapshot:
            raise AnalysisContractError(f"{field} contains duplicate mapping keys.")
        snapshot[key] = item
    return snapshot


def _extension_payload(
    value: Any,
    *,
    known_fields: frozenset[str],
    field: str,
) -> CanonicalJson:
    if isinstance(value, CanonicalJson):
        source: Any = _bounded_json_mapping(value.encoded, field)
    elif isinstance(value, _RuntimeMapping):
        source = value
    else:
        raise AnalysisContractError(
            f"{field} must be immutable canonical JSON or a mapping."
        )
    payload = _profile_canonical_payload(source, field)
    mapping = payload.to_value()
    if not isinstance(mapping, dict):
        raise AnalysisContractError(f"{field} must be a JSON object.")
    collisions = sorted(set(mapping) & known_fields)
    if collisions:
        names = ", ".join(collisions)
        raise AnalysisContractError(
            f"{field} collides with known field(s): {names}."
        )
    return payload


def _unknown_extensions(
    value: Mapping[str, Any],
    *,
    known_fields: frozenset[str],
    field: str,
    allow_extensions: bool,
) -> dict[str, Any]:
    keys = _bounded_mapping_keys(value, field)
    unknown = sorted(set(keys) - known_fields)
    if unknown and not allow_extensions:
        names = ", ".join(unknown)
        raise AnalysisContractError(
            f"{field} contains unknown field(s) for the current contract "
            f"minor version: {names}."
        )
    try:
        return {name: value[name] for name in unknown}
    except Exception as exc:
        raise AnalysisContractError(
            f"{field} could not be read safely."
        ) from exc


@dataclass(frozen=True, slots=True)
class EngineeringIdentity:
    namespace: str
    owner: str
    kind: str
    value: str
    version: str

    def __post_init__(self) -> None:
        for name in ("namespace", "owner", "kind", "value", "version"):
            object.__setattr__(self, name, _text(getattr(self, name), name))

    @property
    def canonical(self) -> str:
        return f"{self.namespace}:{self.owner}:{self.kind}:{self.version}:{self.value}"

    def require_same_type(self, other: "EngineeringIdentity") -> None:  # noqa: UP037
        if not isinstance(other, EngineeringIdentity) or (
            self.namespace, self.owner, self.kind, self.version
        ) != (other.namespace, other.owner, other.kind, other.version):
            raise AnalysisContractError("Engineering identity types are not substitutable.")

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in (
            "namespace", "owner", "kind", "value", "version"
        )}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EngineeringIdentity":  # noqa: UP037
        return cls(**{name: value[name] for name in (
            "namespace", "owner", "kind", "value", "version"
        )})


@dataclass(frozen=True, slots=True)
class ContentDescriptor:
    media_type: str
    digest_algorithm: str
    digest: str
    byte_size: int
    semantic_role: str
    schema: str
    signature_reference: str = ""

    def __post_init__(self) -> None:
        for name in ("media_type", "digest_algorithm", "semantic_role", "schema"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        digest = str(self.digest or "").lower()
        if self.digest_algorithm != "sha256" or not _DIGEST.fullmatch(digest):
            raise AnalysisContractError("Content descriptors require a SHA-256 digest.")
        object.__setattr__(self, "digest", digest)
        if type(self.byte_size) is not int or self.byte_size < 0:
            raise AnalysisContractError("byte_size must be a non-negative integer.")
        object.__setattr__(self, "signature_reference", str(self.signature_reference or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in (
            "media_type", "digest_algorithm", "digest", "byte_size",
            "semantic_role", "schema", "signature_reference"
        )}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContentDescriptor":  # noqa: UP037
        return cls(**{name: value.get(name, "") for name in (
            "media_type", "digest_algorithm", "digest", "byte_size",
            "semantic_role", "schema", "signature_reference"
        )})


@dataclass(frozen=True, slots=True)
class FindingEnvelope:
    finding_id: str
    rule_id: str
    source_id: str
    domain: str
    verdict: str
    severity: str
    code: str
    message: str
    affected: tuple[EngineeringIdentity, ...]
    evidence: tuple[ContentDescriptor, ...]
    remediation: str
    currentness: str
    claim_ceiling: str

    def __post_init__(self) -> None:
        for name in ("finding_id", "rule_id", "source_id", "domain", "verdict",
                     "severity", "code", "message", "currentness", "claim_ceiling"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "remediation", str(self.remediation or "").strip())
        object.__setattr__(self, "affected", _tuple_of(self.affected, EngineeringIdentity, "affected"))
        object.__setattr__(self, "evidence", _tuple_of(self.evidence, ContentDescriptor, "evidence"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id, "rule_id": self.rule_id,
            "source_id": self.source_id, "domain": self.domain,
            "verdict": self.verdict, "severity": self.severity, "code": self.code,
            "message": self.message, "affected": [item.to_dict() for item in self.affected],
            "evidence": [item.to_dict() for item in self.evidence],
            "remediation": self.remediation, "currentness": self.currentness,
            "claim_ceiling": self.claim_ceiling,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FindingEnvelope":  # noqa: UP037
        data = dict(value)
        data["affected"] = tuple(EngineeringIdentity.from_dict(item) for item in value["affected"])
        data["evidence"] = tuple(ContentDescriptor.from_dict(item) for item in value["evidence"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class FindingRuleProfile:
    rule_id: str
    source_id: str
    codes: tuple[str, ...]
    verdicts: tuple[str, ...]
    severities: tuple[str, ...]
    currentness: tuple[str, ...]
    claim_ceilings: tuple[str, ...]
    extensions: CanonicalJson = _EMPTY_EXTENSIONS
    _canonical_byte_size: int = _dataclass_field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _profile_text(self.rule_id, "rule_id"))
        object.__setattr__(self, "source_id", _profile_text(self.source_id, "source_id"))
        for name in _FINDING_RULE_VALUE_FIELDS:
            object.__setattr__(self, name, _profile_values(getattr(self, name), name))
        extensions = _extension_payload(
            self.extensions,
            known_fields=_FINDING_RULE_RESERVED_FIELDS,
            field="finding rule profile extensions",
        )
        object.__setattr__(self, "extensions", extensions)
        payload = _profile_canonical_payload(
            self.to_dict(), "finding rule profile"
        )
        object.__setattr__(
            self, "_canonical_byte_size", len(payload.encoded.encode("utf-8"))
        )

    @property
    def key(self) -> tuple[str, str]:
        return self.source_id, self.rule_id

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            name: list(getattr(self, name)) for name in _FINDING_RULE_VALUE_FIELDS
        }
        payload.update(rule_id=self.rule_id, source_id=self.source_id)
        payload.update(json.loads(self.extensions.encoded))
        return payload

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        allow_extensions: bool = False,
    ) -> FindingRuleProfile:
        if not isinstance(value, _RuntimeMapping):
            raise AnalysisContractError("finding rule profile must be a mapping.")
        snapshot = _mapping_items_snapshot(value, "finding rule profile")
        extensions = _unknown_extensions(
            snapshot,
            known_fields=_FINDING_RULE_FIELDS,
            field="finding rule profile",
            allow_extensions=allow_extensions,
        )
        try:
            return cls(
                extensions=extensions,
                **{name: snapshot[name] for name in _FINDING_RULE_WIRE_FIELDS},
            )
        except KeyError as exc:
            raise AnalysisContractError(
                f"finding rule profile requires {exc.args[0]}."
            ) from exc


def _bounded_profile_rules(
    value: Any, initial_bytes: int
) -> tuple[FindingRuleProfile, ...]:
    if isinstance(value, (str, bytes, _RuntimeMapping)):
        raise AnalysisContractError(
            "rules must contain FindingRuleProfile values."
        )
    try:
        iterator = iter(value)
    except Exception as exc:
        raise AnalysisContractError("rules could not be consumed safely.") from exc

    rules: list[FindingRuleProfile] = []
    aggregate_bytes = initial_bytes
    for index in range(MAX_FINDING_PROFILE_RULES + 1):
        try:
            rule = next(iterator)
        except StopIteration:
            break
        except AnalysisContractError:
            raise
        except Exception as exc:
            raise AnalysisContractError(
                "rules could not be consumed safely."
            ) from exc
        if index == MAX_FINDING_PROFILE_RULES:
            raise AnalysisContractError(
                "rules exceeds the bounded rule count."
            )
        if not isinstance(rule, FindingRuleProfile):
            raise AnalysisContractError(
                "rules must contain FindingRuleProfile values."
            )
        additional_bytes = rule._canonical_byte_size + bool(rules)
        if additional_bytes > MAX_ENVELOPE_BYTES - aggregate_bytes:
            raise AnalysisContractError(
                "finding taxonomy profile exceeds the bounded envelope size."
        )
        aggregate_bytes += additional_bytes
        rules.append(rule)

    if not rules:
        raise AnalysisContractError("rules must contain at least one rule.")
    keys = tuple(rule.key for rule in rules)
    if len(keys) != len(set(keys)):
        raise AnalysisContractError("finding rule keys must be unique.")
    return tuple(sorted(rules, key=lambda rule: rule.key))


@dataclass(frozen=True, slots=True)
class FindingTaxonomyProfile:
    contract_major: int
    contract_minor: int
    profile_id: str
    domain: str
    rules: tuple[FindingRuleProfile, ...]
    extensions: CanonicalJson = _EMPTY_EXTENSIONS

    def __post_init__(self) -> None:
        _profile_version(self.contract_major, self.contract_minor)
        object.__setattr__(
            self, "profile_id", _profile_text(self.profile_id, "profile_id")
        )
        object.__setattr__(self, "domain", _profile_text(self.domain, "domain"))
        extensions = _extension_payload(
            self.extensions,
            known_fields=_FINDING_TAXONOMY_RESERVED_FIELDS,
            field="finding taxonomy profile extensions",
        )
        object.__setattr__(self, "extensions", extensions)
        if (
            self.contract_minor == ENGINEERING_CONTRACT_MINOR
            and extensions.encoded != "{}"
        ):
            raise AnalysisContractError(_CURRENT_MINOR_UNKNOWN)

        metadata = {
            "contract_major": self.contract_major,
            "contract_minor": self.contract_minor,
            "profile_id": self.profile_id,
            "domain": self.domain,
        }
        metadata.update(json.loads(extensions.encoded))
        metadata_json = _profile_canonical_payload(
            metadata, "finding taxonomy profile"
        )
        metadata_bytes = len(metadata_json.encoded.encode("utf-8"))
        empty_rules_overhead = len(',"rules":[]')
        if metadata_bytes + empty_rules_overhead > MAX_ENVELOPE_BYTES:
            raise AnalysisContractError(
                "finding taxonomy profile exceeds the bounded envelope size."
            )
        rules = _bounded_profile_rules(
            self.rules, metadata_bytes + empty_rules_overhead
        )
        if self.contract_minor == ENGINEERING_CONTRACT_MINOR and any(
            rule.extensions.encoded != "{}" for rule in rules
        ):
            raise AnalysisContractError(_CURRENT_MINOR_UNKNOWN)
        object.__setattr__(self, "rules", rules)
        _profile_canonical_payload(
            self.to_dict(), "finding taxonomy profile"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "contract_major": self.contract_major,
            "contract_minor": self.contract_minor,
            "profile_id": self.profile_id,
            "domain": self.domain,
            "rules": [rule.to_dict() for rule in self.rules],
        }
        payload.update(json.loads(self.extensions.encoded))
        return payload

    def to_canonical_json(self) -> str:
        return _profile_canonical_payload(
            self.to_dict(), "finding taxonomy profile"
        ).encoded

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> FindingTaxonomyProfile:
        if not isinstance(value, _RuntimeMapping):
            raise AnalysisContractError("finding taxonomy profile must be a mapping.")
        snapshot = _mapping_items_snapshot(value, "finding taxonomy profile")
        try:
            major = snapshot["contract_major"]
            minor = snapshot["contract_minor"]
        except KeyError as exc:
            raise AnalysisContractError(
                f"finding taxonomy profile requires {exc.args[0]}."
            ) from exc
        _profile_version(major, minor)

        allow_extensions = minor > ENGINEERING_CONTRACT_MINOR
        extensions = _unknown_extensions(
            snapshot,
            known_fields=_FINDING_TAXONOMY_FIELDS,
            field="finding taxonomy profile",
            allow_extensions=allow_extensions,
        )
        try:
            rules_value = snapshot["rules"]
            if isinstance(rules_value, (str, bytes, _RuntimeMapping)):
                raise AnalysisContractError("finding taxonomy profile rules must be a sequence.")
            rules = (
                FindingRuleProfile.from_dict(
                    rule, allow_extensions=allow_extensions
                )
                for rule in rules_value
            )
            return cls(
                contract_major=major,
                contract_minor=minor,
                profile_id=snapshot["profile_id"],
                domain=snapshot["domain"],
                rules=rules,
                extensions=extensions,
            )
        except KeyError as exc:
            raise AnalysisContractError(
                f"finding taxonomy profile requires {exc.args[0]}."
            ) from exc

    @classmethod
    def from_canonical_json(cls, encoded: str) -> FindingTaxonomyProfile:
        return cls.from_dict(_bounded_json_mapping(encoded, "finding taxonomy profile"))


def validate_finding_against_profile(
    finding: FindingEnvelope, profile: FindingTaxonomyProfile
) -> FindingEnvelope:
    """Opt in to exact, fail-closed finding taxonomy validation."""

    if not isinstance(finding, FindingEnvelope):
        raise AnalysisContractError("finding must be FindingEnvelope.")
    if not isinstance(profile, FindingTaxonomyProfile):
        raise AnalysisContractError("profile must be FindingTaxonomyProfile.")
    if profile.contract_minor > ENGINEERING_CONTRACT_MINOR:
        raise AnalysisContractError(
            "A finding taxonomy profile from a newer contract minor version "
            "cannot be used for semantic validation."
        )
    if finding.domain != profile.domain:
        raise AnalysisContractError(
            "Finding domain must exactly match the taxonomy profile domain."
        )
    rule = next(
        (candidate for candidate in profile.rules
         if candidate.key == (finding.source_id, finding.rule_id)),
        None,
    )
    if rule is None:
        raise AnalysisContractError(
            "Finding rule key is not declared by the taxonomy profile."
        )
    for field, allowed_field in (
        ("code", "codes"),
        ("verdict", "verdicts"),
        ("severity", "severities"),
        ("currentness", "currentness"),
        ("claim_ceiling", "claim_ceilings"),
    ):
        if getattr(finding, field) not in getattr(rule, allowed_field):
            raise AnalysisContractError(
                f"Finding {field} is not allowed by the selected rule profile."
            )
    return finding


@dataclass(frozen=True, slots=True)
class ProvenanceNode:
    node_id: str
    node_type: str
    attributes: CanonicalJson

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _text(self.node_id, "node_id"))
        if self.node_type not in {"entity", "activity", "agent"}:
            raise AnalysisContractError("Unknown provenance node type.")
        if not isinstance(self.attributes, CanonicalJson):
            raise AnalysisContractError("attributes must be CanonicalJson.")
        _reject_secrets(self.attributes.to_value(), "provenance attributes")

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "node_type": self.node_type,
                "attributes": self.attributes.to_value()}


@dataclass(frozen=True, slots=True)
class ProvenanceEdge:
    edge_id: str
    relation: str
    source_id: str
    target_id: str
    role: str = ""

    def __post_init__(self) -> None:
        for name in ("edge_id", "relation", "source_id", "target_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.relation not in {"used", "generated", "derived", "associated",
                                  "delegated", "invalidated"}:
            raise AnalysisContractError("Unknown provenance relation.")
        object.__setattr__(self, "role", str(self.role or "").strip())

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in (
            "edge_id", "relation", "source_id", "target_id", "role"
        )}


@dataclass(frozen=True, slots=True)
class ProvenanceGraph:
    graph_id: str
    nodes: tuple[ProvenanceNode, ...]
    edges: tuple[ProvenanceEdge, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph_id", _text(self.graph_id, "graph_id"))
        nodes = _tuple_of(self.nodes, ProvenanceNode, "nodes")
        edges = _tuple_of(self.edges, ProvenanceEdge, "edges")
        _unique(tuple(item.node_id for item in nodes), "provenance node")
        _unique(tuple(item.edge_id for item in edges), "provenance edge")
        node_ids = {item.node_id for item in nodes}
        if any(edge.source_id not in node_ids or edge.target_id not in node_ids for edge in edges):
            raise AnalysisContractError("Provenance edges must reference existing nodes.")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)

    def to_dict(self) -> dict[str, Any]:
        return {"graph_id": self.graph_id,
                "nodes": [item.to_dict() for item in self.nodes],
                "edges": [item.to_dict() for item in self.edges]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProvenanceGraph":  # noqa: UP037
        return cls(
            graph_id=value["graph_id"],
            nodes=tuple(ProvenanceNode(
                node_id=item["node_id"], node_type=item["node_type"],
                attributes=_canonical_payload(item.get("attributes", {}), "attributes")
            ) for item in value["nodes"]),
            edges=tuple(ProvenanceEdge(**item) for item in value["edges"]),
        )


@dataclass(frozen=True, slots=True)
class EngineeringResultEnvelope:
    contract_major: int
    contract_minor: int
    result_id: EngineeringIdentity
    activity_id: EngineeringIdentity
    domain: str
    adapter_id: str
    provider_attempt_id: str
    execution_status: str
    verification_verdict: str
    currentness: str
    publication_state: str
    source_identity: EngineeringIdentity
    dependency_digest: str
    artifacts: tuple[ContentDescriptor, ...]
    summary_metrics: CanonicalJson
    findings: tuple[FindingEnvelope, ...]
    provenance: ProvenanceGraph
    domain_payload: CanonicalJson

    def __post_init__(self) -> None:
        _version(self.contract_major, self.contract_minor)
        for name in ("result_id", "activity_id", "source_identity"):
            if not isinstance(getattr(self, name), EngineeringIdentity):
                raise AnalysisContractError(f"{name} must be EngineeringIdentity.")
        for name in ("domain", "adapter_id", "provider_attempt_id", "execution_status",
                     "verification_verdict", "currentness", "publication_state"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        digest = str(self.dependency_digest or "").lower()
        if not _DIGEST.fullmatch(digest):
            raise AnalysisContractError("dependency_digest must be SHA-256.")
        object.__setattr__(self, "dependency_digest", digest)
        object.__setattr__(self, "artifacts", _tuple_of(self.artifacts, ContentDescriptor, "artifacts"))
        findings = _tuple_of(self.findings, FindingEnvelope, "findings")
        _unique(tuple(item.finding_id for item in findings), "finding")
        object.__setattr__(self, "findings", findings)
        if not isinstance(self.provenance, ProvenanceGraph):
            raise AnalysisContractError("provenance must be ProvenanceGraph.")
        for name in ("summary_metrics", "domain_payload"):
            value = getattr(self, name)
            if not isinstance(value, CanonicalJson):
                raise AnalysisContractError(f"{name} must be CanonicalJson.")
            _reject_secrets(value.to_value(), name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_major": self.contract_major, "contract_minor": self.contract_minor,
            "result_id": self.result_id.to_dict(), "activity_id": self.activity_id.to_dict(),
            "domain": self.domain, "adapter_id": self.adapter_id,
            "provider_attempt_id": self.provider_attempt_id,
            "execution_status": self.execution_status,
            "verification_verdict": self.verification_verdict,
            "currentness": self.currentness, "publication_state": self.publication_state,
            "source_identity": self.source_identity.to_dict(),
            "dependency_digest": self.dependency_digest,
            "artifacts": [item.to_dict() for item in self.artifacts],
            "summary_metrics": self.summary_metrics.to_value(),
            "findings": [item.to_dict() for item in self.findings],
            "provenance": self.provenance.to_dict(),
            "domain_payload": self.domain_payload.to_value(),
        }

    def to_canonical_json(self) -> str:
        payload = _canonical_payload(self.to_dict(), "result envelope")
        return payload.encoded

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EngineeringResultEnvelope":  # noqa: UP037
        _version(value["contract_major"], value["contract_minor"])
        return cls(
            contract_major=value["contract_major"], contract_minor=value["contract_minor"],
            result_id=EngineeringIdentity.from_dict(value["result_id"]),
            activity_id=EngineeringIdentity.from_dict(value["activity_id"]),
            domain=value["domain"], adapter_id=value["adapter_id"],
            provider_attempt_id=value["provider_attempt_id"],
            execution_status=value["execution_status"],
            verification_verdict=value["verification_verdict"],
            currentness=value["currentness"], publication_state=value["publication_state"],
            source_identity=EngineeringIdentity.from_dict(value["source_identity"]),
            dependency_digest=value["dependency_digest"],
            artifacts=tuple(ContentDescriptor.from_dict(item) for item in value["artifacts"]),
            summary_metrics=_canonical_payload(value["summary_metrics"], "summary_metrics"),
            findings=tuple(FindingEnvelope.from_dict(item) for item in value["findings"]),
            provenance=ProvenanceGraph.from_dict(value["provenance"]),
            domain_payload=_canonical_payload(value["domain_payload"], "domain_payload"),
        )

    @classmethod
    def from_canonical_json(cls, encoded: str) -> "EngineeringResultEnvelope":  # noqa: UP037
        try:
            value = json.loads(encoded)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AnalysisContractError("Invalid engineering result JSON.") from exc
        return cls.from_dict(value)


def canonical_payload(value: Any, field: str = "payload") -> CanonicalJson:
    """Create a bounded, secret-screened opaque domain payload."""

    return _canonical_payload(value, field)
