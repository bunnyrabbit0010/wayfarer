import os
from urllib import response

import requests
import logging
import openai

from src.models.itinerary import Itinerary

logger = logging.getLogger(__name__)

_submit_itinerary_tool = {
    "type": "function",
    **openai.pydantic_function_tool(
        Itinerary,
        name="submit_itinerary",
        description="Submit the finalized, complete itinerary once the user has confirmed it.",
    )["function"],
}

tools = [
    {"type": "web_search"},
    {
        "type": "function",
        "name": "get_country_info",
        "description": "Get information about a country.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "The name of the country to fetch information for e.g  'Indonesia'.",
                },
            },
            "required": ["country"],
            "additionalProperties": False
        },
    },
    {
        "type": "function",
        "name": "get_places",
        "description": "Get information about hotels/restaurants in a vicinity.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "near": {
                    "type": "string",
                    "description": "The location to search near (e.g., 'Yosemite Valley, CA').",
                },
                "category": {
                    "type": "string",  
                    "description": "The category of places to filter by (e.g., 'restaurants', 'hotels').",
                },
                "query": {
                    "type": "string",
                    "description": "The search query use for additional context such as 'pet friendly' or 'vegan' to further enrich the category or any free text to send to places API.",
                },
                "limit": {
                    "type": "integer",
                    "description": "The maximum number of results to return. Defaults to 5.",
                },
            },
            "required": ["near", "query", "category", "limit"],
            "additionalProperties": False
        },
    },
    _submit_itinerary_tool,
]


def get_places(near: str, query: str = None, category: str = None, limit: int = 5) -> dict:
    """
    Fetches places from the Foursquare Places API based on the provided parameters.

    Args:
        near (str): The location to search near (e.g., "Yosemite Valley, CA").
        query (str): The search query (e.g., "restaurants").
        category (str, optional): The category of places to filter by. Defaults to None.
        limit (int, optional): The maximum number of results to return. Defaults to 5.

    Returns:
        dict: A dictionary containing the places data returned by the Foursquare API.
    """
    logger.debug(f"Fetching places near: {near}, query: {query}, category: {category}, limit: {limit}")
    try:
        fs_query = f"{query} {category}" if category else query
        headers = {
            "accept": "application/json",
            "X-Places-Api-Version": "2025-06-17",
            "authorization": f"Bearer {os.getenv('FOURSQUARE_API_KEY')}"
        }
        params = {
            "near": near,
            "query": fs_query,
            "limit": limit
        }
        fs_response = requests.get(
            "https://places-api.foursquare.com/places/search",
            headers=headers,
            params=params
        )
        if fs_response.status_code == 200:
            places_data = fs_response.json()
            return {
                "places": [
                    {
                        "name": place.get("name"),
                        "category": (
                            place.get("categories", [{}])[0].get("name")
                            if place.get("categories")
                            else None
                        ),
                        "distance": place.get("distance"),
                        "address": place.get("location", {}).get("formatted_address"),
                    }
                    for place in places_data.get("results", [])
                ]
            }
        else:
            logger.error(f"Foursquare API call failed: {fs_response.status_code} - {fs_response.text}")

    except requests.RequestException as e:
        logger.error(f"Error fetching places from Foursquare API: {e}")

    logger.warning(f"No places found for near: {near}, query: {query}, category: {category}")
    return {}  # Return an empty dictionary if no data is found

def get_country_info(country : str) -> dict:
    """
    Fetches information about a given country using the REST CountriesAPI.

    Args:
        country (str): The name of the country to fetch information for.

    Returns:
        dict: A dictionary containing the country's information.
    """

    logger.debug(f"Fetching information for country: {country}")
    try:
        headers = {
            "User-Agent": "Wayfarer/0.1 (learning project; bunnyrabbit.aws@example.com)"
        }
        response = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{country}",
            headers=headers
        )
        if response.status_code == 200:
            country_data = response.json()
            logger.debug(f"Raw response for {country}: {country_data}")
            if country_data:
                return {
                    "title": country_data.get("title"),
                    "description": country_data.get("description"),
                    "extract": country_data.get("extract"),
                    "url": country_data.get("content_urls", {}).get("desktop", {}).get("page")
                }
    except requests.RequestException as e:
        logger.error(f"Error fetching country information for {country}: {e}")

    logger.warning(f"No information found for country: {country}")
    return {}  # Return an empty dictionary if no data is found


def submit_itinerary(**itinerary_data) -> Itinerary:
    return Itinerary.model_validate(itinerary_data)

tool_mapping = {
    "get_country_info": get_country_info,
    "get_places": get_places,
    "submit_itinerary": submit_itinerary
}