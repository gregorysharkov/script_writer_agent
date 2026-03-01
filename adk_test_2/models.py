"""Pydantic models for location analysis."""

from typing import Optional
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Represents a candidate location from Google Maps."""

    cid: str = Field(..., description="Google Maps CID (unique identifier)")
    name: str = Field(..., description="Name of the location/business")
    address: str = Field(..., description="Full address of the location")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    place_type: Optional[str] = Field(None, description="Type of place (e.g., office, warehouse)")


class LocationImage(BaseModel):
    """Represents an image fetched for a location."""

    cid: str = Field(..., description="CID of the associated location")
    image_type: str = Field(..., description="Type: satellite, map, or street_view")
    url: str = Field(..., description="URL or path to the image")
    description: str = Field("", description="Description of what the image shows")


class LocationImages(BaseModel):
    """Collection of all images for a single location."""

    cid: str = Field(..., description="CID of the location")
    satellite: LocationImage = Field(..., description="Satellite view image")
    map: LocationImage = Field(..., description="Map view image")
    street_view: LocationImage = Field(..., description="Street view image")


class LocationAnalysis(BaseModel):
    """Analysis result for a single location."""

    cid: str = Field(..., description="CID of the analyzed location")
    location_name: str = Field(..., description="Name of the location")
    satellite_analysis: str = Field(..., description="Analysis of satellite imagery")
    map_analysis: str = Field(..., description="Analysis of map view")
    street_view_analysis: str = Field(..., description="Analysis of street view")
    overall_assessment: str = Field(..., description="Overall assessment of the location")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the analysis"
    )
    key_observations: list[str] = Field(
        default_factory=list, description="Key observations about the location"
    )


class LocationSearchResult(BaseModel):
    """Result of searching for company locations."""

    query: str = Field(..., description="Original search query")
    locations: list[Location] = Field(default_factory=list, description="Found locations")
    total_count: int = Field(0, description="Total number of locations found")
