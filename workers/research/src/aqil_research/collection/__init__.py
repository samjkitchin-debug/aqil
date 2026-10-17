"""Controlled economic data collection."""

from aqil_research.collection.models import CollectionResult
from aqil_research.collection.service import collect_bls_unemployment

__all__ = ["CollectionResult", "collect_bls_unemployment"]
