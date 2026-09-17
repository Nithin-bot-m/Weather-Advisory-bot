from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    temperature_2m: float = Field(..., description="Temperature at 2 meters (°C)")
    wind_speed_10m: float = Field(..., description="Wind speed at 10 meters (km/h)")
    precipitation: float = Field(..., description="Precipitation amount (mm)")
    precipitation_probability: float = Field(
        ..., description="Precipitation probability (%)"
    )
    uv_index: float = Field(..., description="UV index (0-12+)")
