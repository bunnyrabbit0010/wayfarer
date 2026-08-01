# Wayfarer — Project Context & Design Decisions

This doc captures design decisions made so far in planning/architecture discussions,
for context when picking up implementation work.

## What Wayfarer Is

An AI travel itinerary builder. Current repo has a working agent (using an
LLM + Foursquare Places API tool) that generates a day-by-day itinerary from
a user's travel request.

## Working Philosophy (important — apply to all suggestions)

- **Progressive complexity**: prefer simple, cheap implementations now, as long as
  they're abstracted behind a stable interface that can be swapped for a more
  accurate/expensive implementation later without touching calling code.
  Example: distance calculations start as haversine (lat/lng math), with the
  option to swap in a real routing/drive-time API later — same function
  signature, so the swap is localized.
- **User learns by building**: I (the assistant) act as a guide/coach, not an
  autonomous implementer. Explain trade-offs, flag logical gaps, ask before
  assuming — don't just hand over finished solutions unprompted.
- **Bite-sized steps**: one component at a time, confirm before moving on.

## Two Bugs Found in the Existing Agent

1. **Tool-call bug**: hotel search called Foursquare with `category: "hotels"`
   (not a valid Foursquare category — categories are numeric taxonomy IDs) and
   stuffed vibe/budget words like "family-friendly $500 budget" into the free-text
   `query` param. Foursquare does literal keyword matching, not semantic intent
   parsing, so it matched garbage ("Family Mart", "Budget Car Rental").
   **Fix direction**: use the correct Lodging category ID, use Foursquare's
   numeric `price` param (1-4) for budget, keep `query` for brand names only.

2. **Reasoning/orchestration bug**: the agent went straight from itinerary →
   hotel search without checking whether the itinerary's locations are even
   geographically compatible with a single home-base hotel. A real itinerary
   spanned Universal City (Day 1), Santa Monica/Venice (Day 2), and central LA
   (Day 3) — no one hotel is practical for all three without significant daily
   driving. The agent should detect this and either ask the user how they want
   to handle the trade-off, or flag it explicitly, rather than silently picking
   a hotel/location.

## Architecture Direction (in progress, not yet built)

Moving from a single monolithic agent toward a **multi-agent workflow**:

1. User submits travel request
2. **Itinerary Agent** generates the itinerary, then asks the user what's next
   (change destination / modify itinerary / proceed to next steps)
3. Downstream, specialized agents for: Hotel booking, Flight booking, Car
   booking, Activity reservations — each with prompts scoped to their task
4. Agents share a **structured trip state** (not raw conversation history) so
   decisions stay consistent across agents — e.g., hotel agent needs to know
   the locked itinerary and its geography before suggesting a location.

Cross-dependencies to keep in mind: hotel location depends on itinerary
clustering; flight arrival time affects Day 1 feasibility; car rental
relevance depends on whether the itinerary is walkable/rideshare-friendly.
Not fully resolved yet whether a lightweight orchestrator agent sequences
these, or the Itinerary Agent stays source of truth and downstream agents
validate against it.

**Decision so far**: build the itinerary feasibility-check logic first (needed
regardless of final architecture), and let that inform the trip-state schema
for the rest of the agents. Multi-agent restructuring itself is not yet built.

## Feasibility-Check Design (in progress)

Purpose: before handing off to a (future, separate) Hotel Agent, determine
whether the generated itinerary is geographically coherent enough for a
single home-base hotel, or whether the user needs to accept a trade-off
(long drives, split stay, or re-clustered itinerary).

Rejected approach: "distance from LA" as a single reference point — meaningless
since LA is ~500 sq mi and everything in-city reads as "close to LA."

**Correct approach** — two signals per itinerary:
1. **Within-day**: sequential distance between consecutive stops in a day
   (catches poor within-day pacing/sequencing).
2. **Across-day**: compute each day's centroid (from its stops' lat/lng), then
   distance between consecutive days' centroids (catches whether a single
   hotel location is even plausible across the whole trip).

Function contract agreed so far (not yet implemented):

```python
def compute_itinerary_geometry(itinerary: Itinerary) -> dict:
    """
    Returns both miles and estimated minutes (not just one), so today's
    haversine-based implementation can later be swapped for a real routing/
    drive-time API without changing the interface or downstream logic.

    Shape (draft, not finalized):
    {
      "days": [
        {
          "day_number": 1,
          "sequential_hops": [
            {"from": ..., "to": ..., "miles": ..., "est_minutes": ...},
            ...
          ],
          "centroid": {"lat": ..., "lng": ...}
        },
        ...
      ],
      "cross_day": [
        {"from_day": 1, "to_day": 2, "miles": ..., "est_minutes": ...},
        ...
      ]
    }
    """
```

Open question not yet settled: the miles→minutes conversion constant (flat
avg speed assumption vs. varying by distance/context).

## Data Models — LOCKED

Location: `src/models/itinerary.py` (Pydantic `BaseModel`s, so structured
LLM output can be validated against a JSON schema).

```python
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
```

Design notes:
- `lat`/`lng` are `Optional` on `Stop` because geocoding is deliberately
  deferred to a separate step (see `get_lat_long` below) rather than forcing
  the LLM to produce coordinates inline during generation.
- `status` defaults to `draft`.

## Repo Structure Decision

```
WAYFARER/
  src/
    models/       # Pydantic data models (itinerary.py currently)
    tools/        # functions that act on data (get_lat_long,
                   # compute_itinerary_geometry go here) — kept separate
                   # from models/ deliberately, especially given multi-agent
                   # direction
  logs/
  venv/
  .env
  requirements.txt
```

## In-Progress / Unresolved: `get_lat_long`

Question under discussion when this doc was written: should `get_lat_long`
(a Foursquare-backed geocoding function) be:

(a) An LLM-facing tool the agent calls at will during itinerary generation, or
(b) A plain deterministic backend function that the orchestration code calls
    in a guaranteed post-processing pass over every Stop after generation
    (avoids relying on the LLM to remember to call it for every stop —
    same class of risk as the earlier Foursquare query bug), or
(c) Both — LLM-callable for ad hoc use, but also always run as a guaranteed
    post-pass regardless.

Leaning direction (not fully settled): option (b) or (c) preferred over (a)
alone, because relying on the LLM to exhaustively call a tool once per stop
with no gaps is not reliable — same failure class as the original bug where
the model silently sent a bad query to Foursquare.

Also flagged: `get_lat_long(poi: str)` should probably take destination/city
context as a required input (not just a bare POI name), since a bare name
can resolve ambiguously without it — same lesson as the original bug
(underspecified tool query).

## Not Yet Started

- `get_lat_long` implementation
- `compute_itinerary_geometry` implementation
- Wiring feasibility check into the Itinerary Agent's flow/prompt
- Trip state schema for multi-agent sharing
- Hotel/Flight/Car/Activity agents
- Structured-output wiring (getting the LLM to actually populate the
  `Itinerary` Pydantic model rather than free-text/markdown)
