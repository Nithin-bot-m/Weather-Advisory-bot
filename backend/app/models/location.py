from pydantic import BaseModel, Field
from typing import Optional


class LocationData(BaseModel):
    name: str = Field(..., description="Name of the city or location")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    country: Optional[str] = Field(None, description="Country name if available")
