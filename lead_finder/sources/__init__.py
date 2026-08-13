"""Discovery sources - one module per public platform.

Each exposes `discover_city(conn, cfg, city_key, existing, target) -> int` and inserts new,
locally-matched businesses into the DB, returning how many it added. `existing` is a set the
orchestrator maintains so no platform re-adds what another already found.
"""
from . import designrush, openstreetmap, yellowpages, yelp  # noqa: F401

REGISTRY = {
    "designrush": designrush,
    "yellowpages": yellowpages,
    "yelp": yelp,
    "openstreetmap": openstreetmap,
}
