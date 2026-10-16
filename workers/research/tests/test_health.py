from aqil_research import __version__
from aqil_research.models import HealthStatus


def test_health_status_defaults() -> None:
    payload = HealthStatus(version=__version__)
    assert payload.service == "aqil-research"
    assert payload.status == "ok"
    assert payload.version == __version__
