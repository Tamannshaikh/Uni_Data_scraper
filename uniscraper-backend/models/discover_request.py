# models/discover_request.py
from pydantic import BaseModel, field_validator


class DiscoverRequest(BaseModel):
    """Request body for POST /api/v1/discover."""
    university_name: str

    @field_validator("university_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("University name must be at least 3 characters")
        if len(v) > 200:
            raise ValueError("University name must be under 200 characters")
        return v
