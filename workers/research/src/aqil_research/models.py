from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Minimal structured payload for worker health checks."""

    service: str = Field(default="aqil-research")
    version: str
    status: str = Field(default="ok")
