from __future__ import annotations
import logging
import os
import requests
from src.models.itinerary import Itinerary, Stop
from math import radians, sin, cos, sqrt, atan2

#TODO - fix this hardcode to something configurable or inputtable...
# Straight-line distance can't distinguish well-connected rail corridors from poorly-connected
# detours (e.g. Rome-Florence at 143mi is a direct high-speed train; Venice-Como at 158mi is not,
# despite being a similar distance). 150mi is a best-fit line between real examples we've seen,
# not a guarantee. Real fix is a routing/transit API, per context.md's compute_itinerary_geometry design.
MAX_STOP_DISTANCE_MILES = 50.0  # Maximum distance between stops
MAX_DAY_DISTANCE_MILES = 150.0  # Maximum distance between days

logger = logging.getLogger(__name__)

def get_lat_long(poi: str, destination: str) -> tuple[float, float] | None:
    """
    Get the latitude and longitude of a point of interest (POI) in a given destination.

    Args:
        poi (str): The point of interest to search for.
        destination (str): The destination where the POI is located.

    Returns:
        tuple: A tuple containing the latitude and longitude of the POI or None, if not found.
    """
    logger.debug(f"Fetching latitude and longitude for POI '{poi}' in destination '{destination}'")
    try:
        headers = {
            "accept": "application/json",
            "X-Places-Api-Version": "2025-06-17",
            "authorization": f"Bearer {os.getenv('FOURSQUARE_API_KEY')}"
        }
        params = {
            "near": destination,
            "query": poi,
            "limit": 1
        }
        fs_response = requests.get(
            "https://places-api.foursquare.com/places/search",
            headers=headers,
            params=params
        )
        if fs_response.status_code == 200:
            places_data = fs_response.json()
            top_place = places_data.get("results", [])[0] if places_data.get("results") else None
            if top_place:
                latitude = top_place.get("latitude")
                longitude = top_place.get("longitude")
                if latitude is not None and longitude is not None:
                    logger.debug(f"Found lat-long for POI '{poi}': ({latitude}, {longitude})")
                    return latitude, longitude
                else:
                    logger.warning(f"Latitude or longitude not found for POI '{poi}' in destination '{destination}'")
            else:
                logger.warning(f"API Call returned 0 matching results for  POI '{poi}' in destination '{destination}'")
        else:
            logger.error(f"Foursquare API call failed: {fs_response.status_code} - {fs_response.text}")
    except requests.RequestException as e:
        logger.error(f"Error fetching lat-long from Foursquare API: {e}")

    return None  # Return None if no data is found

def is_valid_geo_cord(coord: float) -> bool :
    return coord != None and coord != 0.0

def compute_distance_between(stop1: Stop, stop2: Stop) -> float:
    lat1, lng1 = stop1.lat, stop1.lng
    lat2, lng2 = stop2.lat, stop2.lng

    if is_valid_geo_cord(lat1) and is_valid_geo_cord(lng1) and is_valid_geo_cord(lat2) and is_valid_geo_cord(lng2):
        R = 3958.8
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return -1.0  # Return -1.0 if any of the coordinates are invalid

def _find_nearest_resolved_stop(day_stops: list[Stop], resolved_indices: set[int], jj: int) -> Stop | None:
    """Search outward from index jj (both directions) for the closest stop whose
    coordinates were resolved in Pass 1 (per resolved_indices), not inherited."""
    offset = 1
    while jj - offset >= 0 or jj + offset < len(day_stops):
        if jj - offset >= 0 and (jj - offset) in resolved_indices:
            return day_stops[jj - offset]
        if jj + offset < len(day_stops) and (jj + offset) in resolved_indices:
            return day_stops[jj + offset]
        offset += 1
    return None  # nothing resolved anywhere in this day

 
def check_itinerary_feasibility(itinerary: Itinerary) -> list[str] :
    """
    Validates the feasibility of the given itinerary.

    Args:
        itinerary (Itinerary): The itinerary to validate.

    Returns:
        list[str]: A list of validation error messages. Empty if the itinerary is feasible.
    """
    errors = []
    logger.info("Checking Itinerary Feasibility...")
    # Populating lat long for all days/stops in the itinerary.
    
    # Pass 1 — geocode every stop, unchanged from what you have.
    for day in itinerary.days:
        for stop in day.stops:
            result = get_lat_long(stop.name, stop.address)
            stop.lat, stop.lng = result if result else (None, None)


    #Pass 2 to inherit the lat long from nearest neighbor if not found in pass 1
    for day in itinerary.days:
        # Snapshot must be taken before any inheritance happens, so later inheritance
        # never chains off a stop that was itself only inherited.
        resolved_indices = {
            jj for jj, stop in enumerate(day.stops)
            if is_valid_geo_cord(stop.lat) and is_valid_geo_cord(stop.lng)
        }

        for jj, stop in enumerate(day.stops):
            if jj in resolved_indices:
                continue  # already has real coordinates, nothing to do

            neighbor = _find_nearest_resolved_stop(day.stops, resolved_indices, jj)
            if neighbor is not None:
                stop.lat, stop.lng = neighbor.lat, neighbor.lng
                logger.info(
                    f"Stop '{stop.name}' on day {day.day_number} inherited coordinates "
                    f"from '{neighbor.name}' (could not geocode independently)"
                )
            else:
                errors.append(f"Could not verify location of '{stop.name}' on day {day.day_number}")

        logger.debug("Validating distances for day %d", day.day_number)
        for i in range(len(day.stops) - 1):
            stop1 = day.stops[i]
            stop2 = day.stops[i + 1]
            distance = compute_distance_between(stop1, stop2)
            if distance < 0:
                continue  # already reported during geocoding
            if distance  > MAX_STOP_DISTANCE_MILES:  # Assuming 50 miles is the threshold for feasibility
                errors.append(f"Distance between '{stop1.name}' and '{stop2.name}' on day {day.day_number} is too far: {distance:.2f} miles")

    #Itinerary specific validations - is the overall itinerary feasible from a distance perspective.     
    for i in range(len(itinerary.days) - 1):
        day1 = itinerary.days[i]
        day2 = itinerary.days[i + 1]
        logger.debug("Validating overall distances between day %d and day %d", day1.day_number, day2.day_number)

        if not day1.stops or not day2.stops:
            continue  # nothing to compare for a day with no stops

        #compare distance between the last stop of day1 and the first stop of day2.. this should later be fine tuned
        stop1 = day1.stops[-1]
        stop2 = day2.stops[0]
        distance = compute_distance_between(stop1, stop2)
        if distance < 0:
            continue  # already reported during geocoding
        elif distance  > MAX_DAY_DISTANCE_MILES:  
             errors.append(f"Distance between day {day1.day_number} and day {day2.day_number} is too far: {distance:.2f} miles")

    for error in errors:
        logger.warning(error)

    return errors