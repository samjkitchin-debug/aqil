import pytest

from aqil_research.editorial.claim_verifier import (
    ClaimVerificationError,
    verify_claim_for_publication,
)


def test_unverified_claim_blocks_publication() -> None:
    with pytest.raises(ClaimVerificationError):
        verify_claim_for_publication({})
