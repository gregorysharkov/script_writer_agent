"""Mock Google Maps API tools for location analysis.

These tools simulate Google Maps API responses for testing the fan-out pattern.
In production, these would be replaced with actual API calls.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Mock data for testing
MOCK_LOCATIONS = {
    "acme_corp": [
        {
            "cid": "cid_acme_hq",
            "name": "ACME Corp Headquarters",
            "address": "123 Innovation Drive, San Francisco, CA 94105",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "place_type": "corporate_office",
        },
        {
            "cid": "cid_acme_warehouse",
            "name": "ACME Corp Distribution Center",
            "address": "456 Logistics Way, Oakland, CA 94607",
            "latitude": 37.8044,
            "longitude": -122.2712,
            "place_type": "warehouse",
        },
        {
            "cid": "cid_acme_research",
            "name": "ACME Research Lab",
            "address": "789 Science Park, Palo Alto, CA 94301",
            "latitude": 37.4419,
            "longitude": -122.1430,
            "place_type": "research_facility",
        },
    ],
    "default": [
        {
            "cid": "cid_default_1",
            "name": "Sample Location 1",
            "address": "100 Main Street, Anytown, USA",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "place_type": "office",
        },
        {
            "cid": "cid_default_2",
            "name": "Sample Location 2",
            "address": "200 Second Avenue, Anytown, USA",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "place_type": "retail",
        },
    ],
}

MOCK_IMAGES = {
    "satellite": {
        "url_template": "https://maps.example.com/satellite/{cid}",
        "description": "Aerial satellite view showing building footprint, parking areas, and surrounding infrastructure",
    },
    "map": {
        "url_template": "https://maps.example.com/map/{cid}",
        "description": "Standard map view with roads, landmarks, and points of interest",
    },
    "street_view": {
        "url_template": "https://maps.example.com/streetview/{cid}",
        "description": "Street-level panoramic view of the location entrance and facade",
    },
}


def find_locations(company_name: str) -> dict[str, Any]:
    """Find candidate locations for a company using Google Maps.

    This is a mock implementation that returns predefined locations.
    In production, this would call the Google Maps Places API.

    Args:
        company_name: Name of the company to search for.

    Returns:
        Dictionary containing search results with location details.
    """
    logger.info(f"Searching for locations of company: {company_name}")

    # Normalize company name for lookup
    normalized_name = company_name.lower().replace(" ", "_")

    # Get mock locations or default
    locations = MOCK_LOCATIONS.get(normalized_name, MOCK_LOCATIONS["default"])

    result = {
        "query": company_name,
        "locations": locations,
        "total_count": len(locations),
        "cids": [loc["cid"] for loc in locations],
    }

    logger.info(f"Found {len(locations)} locations for {company_name}")
    return result


def get_satellite_image(cid: str, location_name: str = "") -> dict[str, Any]:
    """Get satellite imagery for a location.

    This is a mock implementation that returns simulated image data.
    In production, this would call the Google Maps Static API.

    Args:
        cid: Google Maps CID for the location.
        location_name: Optional name of the location for context.

    Returns:
        Dictionary containing image URL and metadata.
    """
    logger.info(f"Fetching satellite image for CID: {cid}")

    image_config = MOCK_IMAGES["satellite"]
    return {
        "cid": cid,
        "image_type": "satellite",
        "url": image_config["url_template"].format(cid=cid),
        "description": image_config["description"],
        "location_name": location_name,
        "mock_image_content": f"[Satellite image of {location_name or cid}: Shows a large commercial building complex with approximately 50,000 sq ft of floor space. Visible features include a main building, parking lot with ~200 spaces, loading dock area, and landscaped perimeter.]",
    }


def get_street_view_image(cid: str, location_name: str = "") -> dict[str, Any]:
    """Get street view imagery for a location.

    This is a mock implementation that returns simulated image data.
    In production, this would call the Google Street View API.

    Args:
        cid: Google Maps CID for the location.
        location_name: Optional name of the location for context.

    Returns:
        Dictionary containing image URL and metadata.
    """
    logger.info(f"Fetching street view image for CID: {cid}")

    image_config = MOCK_IMAGES["street_view"]
    return {
        "cid": cid,
        "image_type": "street_view",
        "url": image_config["url_template"].format(cid=cid),
        "description": image_config["description"],
        "location_name": location_name,
        "mock_image_content": f"[Street view of {location_name or cid}: Modern glass-fronted building with prominent company signage. Main entrance has automatic doors, wheelchair ramp, and visitor parking. Well-maintained landscaping with mature trees along the street frontage.]",
    }


def get_map_image(cid: str, location_name: str = "") -> dict[str, Any]:
    """Get map view for a location.

    This is a mock implementation that returns simulated image data.
    In production, this would call the Google Maps Static API.

    Args:
        cid: Google Maps CID for the location.
        location_name: Optional name of the location for context.

    Returns:
        Dictionary containing image URL and metadata.
    """
    logger.info(f"Fetching map image for CID: {cid}")

    image_config = MOCK_IMAGES["map"]
    return {
        "cid": cid,
        "image_type": "map",
        "url": image_config["url_template"].format(cid=cid),
        "description": image_config["description"],
        "location_name": location_name,
        "mock_image_content": f"[Map view of {location_name or cid}: Located in a commercial/industrial zone. Major highways within 2 miles. Nearby amenities include restaurants, gas stations, and public transit stops. Surrounding businesses appear to be similar commercial enterprises.]",
    }


def get_all_images_for_location(cid: str, location_name: str = "") -> dict[str, Any]:
    """Get all three image types for a location.

    Convenience function that fetches satellite, street view, and map images.

    Args:
        cid: Google Maps CID for the location.
        location_name: Optional name of the location for context.

    Returns:
        Dictionary containing all image types.
    """
    logger.info(f"Fetching all images for CID: {cid}")

    return {
        "cid": cid,
        "location_name": location_name,
        "satellite": get_satellite_image(cid, location_name),
        "street_view": get_street_view_image(cid, location_name),
        "map": get_map_image(cid, location_name),
    }
