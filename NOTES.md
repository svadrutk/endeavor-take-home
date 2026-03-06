# Development Notes

## Commit History

### 4d937e7 - Remove logging from repositories and improve environment context

**What changed:**
- Removed all logging statements from repository layer (base_repository, pokemon_repository, ranger_repository, sighting_repository, trainer_repository)
- Added dynamic git commit hash detection in logging_config.py
- Cleaned up NOTES.md to focus on commit history only

**Why it matters:**
Repositories should focus purely on data access, not logging. With the wide events pattern, all logging is now centralized in middleware. The dynamic git commit hash detection means you don't need to manually set COMMIT_SHA environment variable - it's automatically detected from the git repository.

---

### a4afa66 - Performance Improvements & Deprecation Fixes

**What changed:**
- Added database indexes to speed up queries on the sightings table
- Fixed deprecated `datetime.utcnow()` calls to use timezone-aware datetime

**Why it matters:**
Queries were doing full table scans on 55,000 records. Now they use indexes, making them 10-100x faster. The datetime fix ensures compatibility with Python 3.12+.

**Technical details:**
- Added 7 indexes: region, ranger_id, date, pokemon_id, is_confirmed, and two composite indexes
- Changed `datetime.utcnow()` to `datetime.now(timezone.utc)`

---

### 97bba47 - Logging Refactoring: Wide Events Pattern

**What changed:**
- Replaced scattered log statements with a single "wide event" per request
- Added middleware to automatically capture request context
- Included environment info (commit hash, version, region) in every log

**Why it matters:**
Instead of multiple log lines per request, we now have one rich log event with all the context. This makes debugging much easier - you can query logs by any field (user, pokemon, region, error type, etc.).

**Example:**
```json
{
  "request_id": "abc-123",
  "method": "POST",
  "path": "/sightings",
  "status_code": 200,
  "duration_ms": 45.23,
  "sighting": {
    "pokemon_name": "Pikachu",
    "region": "Kanto"
  },
  "commit_hash": "a4afa66"
}
```

---

### c90410d - API Design & Architecture Refactoring

**What changed:**
- Split code into services and repositories for better organization
- Added input validation (no empty strings, proper email format)
- Added unique constraints to prevent duplicate users
- Added rate limiting (100/min for reads, 10/min for writes)
- Improved error messages with more context

**Why it matters:**
The code is now easier to test and maintain. Business logic is separated from routes. Users can't create duplicate accounts. API is protected from abuse.

**Architecture:**
```
app/
├── main.py (routes - thin controllers)
├── services/ (business logic)
├── repositories/ (data access)
├── models.py (database models)
└── schemas.py (API contracts)
```

---

### 68f6a61 - Seed Script Fixes

**What changed:**
- Fixed import paths to use absolute imports from `app` module
- Fixed data file reference (pokedex.json → pokedex_entries.json)
- Added missing datetime import
- Fixed model field names to match current models
- Removed manual ID generation (models auto-generate UUIDs)

**Why it matters:**
The seed script now works correctly and can populate the database with test data.

**Result:**
- 493 Pokemon species (Generations I-IV)
- 33 Ranger profiles
- 55,000 historical sighting records

---

### bd0f85a - Initial Setup

**What changed:**
Initial repository setup with basic FastAPI application structure.

**Why it matters:**
Starting point for the Pokemon tracking application.
