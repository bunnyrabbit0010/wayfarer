from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TimeBlock(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class ItineraryStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    LOCKED = "locked"


class Stop(BaseModel):
    name: str
    category: str = Field(..., description="e.g. theme_park, restaurant, landmark")
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    time_block: TimeBlock
    notes: Optional[str] = None


class Day(BaseModel):
    day_number: int
    theme: str
    stops: List[Stop]


class Itinerary(BaseModel):
    destination: str
    start_date: date
    end_date: date
    days: List[Day]
    status: ItineraryStatus = ItineraryStatus.DRAFT