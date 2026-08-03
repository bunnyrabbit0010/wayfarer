# Progress Log

## 2026-08-01

### Accomplishments - Architecting for the future
-- Wayfarer is now shaping up to be a multi-agent solution. A light weight Orchestrator Agent will delegate to Worker Agents to do specific tasks such as Itinerary Drafting, Hotel Booking, Restaurants, Rentals etc.  Currently a light weight Orchestrator Agent will forward requests to an Itinerary Agent. The new architecture not only farms out to sub Agents but accounts for iterative refinements for inter-dependencies.
-- The repo has been restructured to reflect the new architecture. Each Agent dealing with a specific concern will have its associated prompts, tools etc.
-- Session state information is now defined and it is used to track the turn by turn items and also an Itinerary instance which holds the draft itinerary. New tools to store Itinerary submit_itinerary introduced.

### Loose Ends
-- Need to remove hard coding call to Itinerary Agent
-- Python version needs to be updated to deal with Union Type
-- Itinerary dates are hallucinated — submit_itinerary produced start_date=2023-10-01 despite no dates ever being discussed; traces to prompt.md's "Gathering Requirements" never asking for actual travel dates, only duration.
-- get_places was never called during the whole test conversation, despite the prompt requiring it before naming real attractions — model named Universal Studios, Griffith Observatory, Disneyland, etc. from memory alone. Low risk this time (famous places), but a live example of prompt instructions not being reliably followed.
-- Validation layer (get_lat_long, compute_itinerary_geometry) still isn't built — the Itinerary now gets captured correctly, but nothing runs on it yet; the "Glad we have an itinerary, what next?" reply is still just a placeholder.

## 2026-08-02

### Accomplishments - Building the feasibility gate
-- Implemented `get_lat_long` (src/tools/validators.py) — a Foursquare-backed geocoding function resolving a single POI's lat/lng given destination context, returning `None` on failure rather than raising, per the contract locked before implementation.
-- Implemented `check_itinerary_feasibility` (src/tools/validators.py) — populates coordinates for every Stop, then checks within-day sequential-hop distance and across-day (last-stop-of-day-N to first-stop-of-day-N+1) distance against a threshold, returning a list of human-readable problems instead of raising.
-- Decided, after explicitly comparing the trade-offs, to gate `submit_itinerary` inside the agent loop (src/agents/itinerary/loop.py) rather than inside the tool function itself — retry-count tracking naturally belongs to loop state, and it keeps tool functions uniform.
-- Wired the gate in: `submit_itinerary` now runs `check_itinerary_feasibility`, feeds problems back to the model as a normal tool result with a capped retry (`MAX_ITR_RETRIES = 3`), and only returns success once the check passes. Exhausting retries now returns an honest message to the user instead of silently accepting a known-infeasible itinerary (this was caught and fixed during review — the first version regressed to silent accept-on-exhaustion).
-- Ran a full end-to-end test with a real 10-day multi-city Italy family itinerary. Confirmed the gate fires on `submit_itinerary`, correctly catches distance problems, feeds them back, and the model responds to the feedback with a revised plan — the core loop works as designed.
-- Explicitly decided and recorded the near-term roadmap: finish the feasibility milestone on the current hand-rolled architecture, then run a dedicated tech-debt sprint (Python 3.10+ upgrade, pivot to `openai-agents-python` for its handoffs/guardrails primitives) *before* building the next layer of sub-agents — a deliberate choice to avoid re-architecting load-bearing interfaces mid-build.

### Loose Ends
-- **Geocoding context is too coarse for multi-city trips.** `get_lat_long` is called with `itinerary.destination` (e.g. "Italy") as the `near` search context for every stop, regardless of which city that stop is actually in. In the live test this produced ~30 "location not found" warnings across Rome/Florence/Venice/Lake Como/Cinque Terre stops — likely the dominant cause, not real geocoding failures. The `Day` model has no city/location field to fix this properly; needs a model change.
-- **Some submitted Stop names are activity descriptions, not real venues** — e.g. "Beach Time," "Wine Tasting Experience," "Farewell Dinner," "Evening Walk in Venice." These can never resolve via a Places search regardless of the geocoding-context fix. Same root cause as yesterday's "get_places wasn't called" loose end, now showing up in structured submissions.
-- **`MAX_STOP_DISTANCE_MILES` (50mi) is applied identically to within-day and across-day checks**, which conflates two different questions. Normal, expected multi-city rail legs (Rome→Florence 143mi, Florence→Venice 127mi) get flagged exactly like the genuinely bad leg (Venice→Lake Como 153mi), diluting the signal the model receives and likely contributing to an overly broad self-correction attempt rather than a targeted one.
-- Milestone ("Itinerary Agent reliably produces feasible itineraries") not yet reached — pending the three fixes above.
