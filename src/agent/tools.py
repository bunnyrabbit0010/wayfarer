import requests
import logging

logger = logging.getLogger(__name__)

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
]


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


tool_mapping = {
    "get_country_info": get_country_info,
}