# Development Notes

## Phase 1: Seed Script Fixes

### Issues Fixed

The seed script (`scripts/seed.py`) had multiple incompatibilities with the current codebase:

1. **Import paths** - Used relative imports instead of absolute imports from the `app` module
   - Changed `from database import` to `from app.database import`
   - Changed `from models import` to `from app.models import`
   - Script must be run as a module: `uv run python -m scripts.seed` (not `uv run python scripts/seed.py`)

2. **Data file path** - Referenced wrong filename
   - Changed `pokedex.json` to `pokedex_entries.json` (line 138)

3. **Missing import** - `datetime` was used but not imported
   - Added `from datetime import datetime`

4. **Model field mismatches** - Field names didn't match the current models
   - Changed `pokemon_name` to `pokemon_id` in Sighting creation (the model uses a foreign key, not a name field)
   - Changed `confirmed` to `is_confirmed` (matches the model field name)
   - Changed `species_name` to `name` in Pokemon creation (matches the model field name)

5. **Auto-generated IDs** - Attempted to manually set IDs on models that use `init=False`
   - Removed manual `id=str(uuid.uuid4())` from Ranger creation (the model auto-generates UUIDs)
   - Removed manual `id=str(uuid.uuid4())` from Sighting creation (the model auto-generates UUIDs)
   - Added `db.flush()` after adding Rangers to ensure IDs are generated before creating sightings

### Result

The seed script now successfully:
- Loads 493 Pokemon species from Generations I-IV
- Creates 33 Ranger profiles
- Generates 55,000 historical sighting records across Kanto, Johto, Hoenn, and Sinnoh regions
