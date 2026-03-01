"""Location analyzer agent that fetches images and analyzes them with LLM.

This module provides the factory function and agents for analyzing
individual locations. Each location gets a SequentialAgent that:
1. Fetches satellite, map, and street view images
2. Analyzes all images with an LLM
3. Stores the analysis in session state
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from ..tools.maps_tools import (
    get_satellite_image,
    get_street_view_image,
    get_map_image,
    get_all_images_for_location,
)

logger = logging.getLogger(__name__)


class ImageFetcherAgent(BaseAgent):
    """Agent that fetches all image types for a specific location.

    This agent:
    1. Retrieves satellite, map, and street view images
    2. Stores them in session state for the analyzer to use
    """

    cid: str = ""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Fetch all images for the location.

        Args:
            ctx: The invocation context.

        Yields:
            Events describing the fetch progress.
        """
        # Get location info from session state
        cid_to_location = ctx.session.state.get("cid_to_location", {})
        location_info = cid_to_location.get(self.cid, {})
        location_name = location_info.get("name", self.cid)

        yield Event(
            author=self.name,
            content=Content(
                parts=[Part.from_text(text=f"Fetching images for: {location_name}")]
            ),
        )

        try:
            # Fetch all images
            satellite = get_satellite_image(self.cid, location_name)
            street_view = get_street_view_image(self.cid, location_name)
            map_view = get_map_image(self.cid, location_name)

            # Store in session state
            images_key = f"images_{self.cid}"
            ctx.session.state[images_key] = {
                "cid": self.cid,
                "location_name": location_name,
                "location_info": location_info,
                "satellite": satellite,
                "street_view": street_view,
                "map": map_view,
            }

            logger.info(
                f"Stored images for {self.cid} in session state key: {images_key}"
            )

            yield Event(
                author=self.name,
                content=Content(
                    parts=[
                        Part.from_text(
                            text=f"Fetched 3 images for {location_name}:\n"
                            f"- Satellite: {satellite['url']}\n"
                            f"- Street View: {street_view['url']}\n"
                            f"- Map: {map_view['url']}"
                        )
                    ]
                ),
            )

        except Exception as e:
            logger.error(f"Error fetching images for {self.cid}: {e}")
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part.from_text(text=f"Error fetching images: {e}")]
                ),
            )


class ImageAnalyzerAgent(BaseAgent):
    """Agent that analyzes images for a location using an LLM.

    This agent:
    1. Reads images from session state
    2. Sends them to an LLM for analysis
    3. Stores the analysis results in session state
    """

    cid: str = ""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Analyze images for the location.

        Args:
            ctx: The invocation context.

        Yields:
            Events containing the analysis results.
        """
        images_key = f"images_{self.cid}"
        images_data = ctx.session.state.get(images_key, {})

        if not images_data:
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part.from_text(text=f"No images found for CID: {self.cid}")]
                ),
            )
            return

        location_name = images_data.get("location_name", self.cid)
        location_info = images_data.get("location_info", {})

        yield Event(
            author=self.name,
            content=Content(
                parts=[Part.from_text(text=f"Analyzing images for: {location_name}")]
            ),
        )

        # In a real implementation, we would send actual images to a multimodal LLM
        # For this mock, we analyze the mock image descriptions
        satellite_content = images_data.get("satellite", {}).get(
            "mock_image_content", ""
        )
        street_view_content = images_data.get("street_view", {}).get(
            "mock_image_content", ""
        )
        map_content = images_data.get("map", {}).get("mock_image_content", "")

        # Generate mock analysis based on the mock content
        analysis = {
            "cid": self.cid,
            "location_name": location_name,
            "address": location_info.get("address", "Unknown"),
            "place_type": location_info.get("place_type", "Unknown"),
            "satellite_analysis": f"Satellite Analysis: {satellite_content}",
            "street_view_analysis": f"Street View Analysis: {street_view_content}",
            "map_analysis": f"Map Analysis: {map_content}",
            "overall_assessment": (
                f"{location_name} appears to be a well-established commercial location "
                f"with adequate facilities for business operations. The satellite imagery "
                f"shows a properly sized facility, street view confirms professional appearance, "
                f"and map data indicates good accessibility."
            ),
            "confidence_score": 0.85,
            "key_observations": [
                "Commercial/industrial building with adequate space",
                "Good road accessibility",
                "Professional exterior appearance",
                "Sufficient parking facilities",
                "Located in appropriate business zone",
            ],
        }

        # Store analysis in session state
        analysis_key = f"analysis_{self.cid}"
        ctx.session.state[analysis_key] = analysis

        logger.info(
            f"Stored analysis for {self.cid} in session state key: {analysis_key}"
        )

        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(
                        text=f"Analysis complete for {location_name}:\n\n"
                        f"**Overall Assessment:**\n{analysis['overall_assessment']}\n\n"
                        f"**Confidence Score:** {analysis['confidence_score']}\n\n"
                        f"**Key Observations:**\n"
                        + "\n".join(f"- {obs}" for obs in analysis["key_observations"])
                    )
                ]
            ),
        )


def create_location_analyzer(cid: str) -> SequentialAgent:
    """Factory function to create a location analyzer agent for a specific CID.

    This creates a SequentialAgent that:
    1. Fetches images for the location
    2. Analyzes the images with an LLM

    Args:
        cid: The Google Maps CID of the location to analyze.

    Returns:
        A SequentialAgent configured for analyzing the specified location.
    """
    logger.info(f"Creating location analyzer for CID: {cid}")

    # Create the image fetcher agent
    image_fetcher = ImageFetcherAgent(
        name=f"image_fetcher_{cid}",
        cid=cid,
        description=f"Fetches satellite, map, and street view images for {cid}",
    )

    # Create the image analyzer agent
    image_analyzer = ImageAnalyzerAgent(
        name=f"image_analyzer_{cid}",
        cid=cid,
        description=f"Analyzes images for {cid} using LLM",
    )

    # Combine into a sequential pipeline
    return SequentialAgent(
        name=f"location_analyzer_{cid}",
        description=f"Complete analysis pipeline for location {cid}",
        sub_agents=[image_fetcher, image_analyzer],
    )


# Alternative: LLM-based analyzer that could use actual multimodal capabilities
IMAGE_ANALYSIS_INSTRUCTION = """You are an expert location analyst. You will receive 
satellite, street view, and map images for a business location.

Analyze each image and provide:
1. **Satellite Analysis**: Building size, parking, surrounding area
2. **Street View Analysis**: Building appearance, signage, accessibility
3. **Map Analysis**: Location context, nearby amenities, transportation access

Then provide:
- **Overall Assessment**: Summary of the location's suitability
- **Confidence Score**: 0.0-1.0 based on image quality and clarity
- **Key Observations**: List of important findings

Store your analysis in a structured format.
"""


def create_llm_location_analyzer(cid: str) -> LlmAgent:
    """Create an LLM-based analyzer that could process actual images.

    This is an alternative implementation that uses Gemini's multimodal
    capabilities to analyze actual images (when available).

    Args:
        cid: The CID of the location to analyze.

    Returns:
        An LlmAgent configured for image analysis.
    """
    return LlmAgent(
        name=f"llm_analyzer_{cid}",
        model="gemini-2.5-flash",
        instruction=IMAGE_ANALYSIS_INSTRUCTION,
        output_key=f"analysis_{cid}",
        description=f"LLM-powered image analyzer for {cid}",
    )
