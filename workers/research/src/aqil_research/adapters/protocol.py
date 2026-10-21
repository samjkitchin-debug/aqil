"""Typed provider adapter contract — normalise to EconomicObservation only."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from aqil_research.contracts.observation import EconomicObservation


class ProviderFailureCode(StrEnum):
    DISABLED = "disabled"
    FETCH_FAILED = "fetch_failed"
    PARSE_FAILED = "parse_failed"
    RIGHTS_BLOCKED = "rights_blocked"
    EMPTY_RESPONSE = "empty_response"


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    adapter_id: str
    adapter_version: str
    source_id: str
    dataset_id: str
    provider_id: str = "bls"


@dataclass(frozen=True, slots=True)
class ProviderFetchError:
    code: ProviderFailureCode
    message: str
    optional: bool = False


@dataclass(frozen=True, slots=True)
class ProviderFetchResult:
    """Provider-native payloads never leave the adapter boundary."""

    observations: tuple[EconomicObservation, ...]
    errors: tuple[ProviderFetchError, ...] = ()
    partial: bool = False


class ProviderAdapter(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...

    def fetch(self) -> ProviderFetchResult: ...
