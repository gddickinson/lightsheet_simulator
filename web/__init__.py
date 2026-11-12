"""Web interface for the Lightsheet Simulator (FastAPI + plain ES modules, no build step).

Contents:
- app.py       FastAPI app: front end in static/, JSON API under /api, STATIC_ENDPOINTS for the static site
- pipeline.py  seeded sample (structure_pipeline / DataGenerator / BiologicalSimulator) + blur/noise acquisition
- static/      front end; *_engine.js, np_random.js, ndimage.js and pipeline.js are the JS port of the simulator
"""
