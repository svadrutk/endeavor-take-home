# Development Notes

## Feature 2: Research Campaigns with Lifecycle Management

**What changed:**
- Implemented full CRUD for research campaigns with state machine lifecycle (draft → active → completed → archived)
- Added Campaign model with CampaignStatus enum for type-safe state management
- Integrated campaigns with existing sighting system via optional campaign_id foreign key
- Implemented sighting locking for completed campaigns to prevent data modification
- Created campaign summary endpoint with aggregated statistics
- Added comprehensive test coverage for campaign lifecycle

**Why it matters:**
Rangers can now organize field research into structured campaigns with clear status tracking. The state machine ensures data integrity by preventing backward transitions and locking sightings when campaigns are completed. This provides Professor Oak with the ability to track active vs. completed research efforts and prevents accidental modification of finalized data.

**Design Decisions:**

1. **Authorization Model**: Any ranger can create, update, and transition any campaign (collaborative model). This aligns with the peer confirmation system where any ranger can confirm any sighting. This promotes collaboration and avoids ownership complexity.

2. **State Machine Implementation**: Used Python's StrEnum for type-safe state comparisons with a `can_transition_to()` method that centralizes transition validation logic. This prevents typos in state strings and provides IDE autocomplete support.

3. **Sighting Locking**: Implemented in the service layer by checking campaign status before any sighting modification. This ensures data integrity without requiring database-level constraints.

4. **Campaign Summary**: Uses efficient aggregation queries with SQLAlchemy's `func.count`, `func.min`, and `func.max` to avoid N+1 query problems. The summary is available for all campaign states (not just completed) to allow real-time monitoring of active campaigns.

5. **Database Indexes**: Added indexes on campaign_id and composite indexes (campaign_id, date) for efficient querying of campaign-related sightings.

6. **Backward Compatibility**: Made campaign_id optional in sighting creation to maintain compatibility with existing code. Sightings can exist without being associated with a campaign.

**Technical Implementation:**
- CampaignStatus enum with transition validation
- Campaign model with proper indexes and timestamps
- CampaignRepository extending BaseRepository
- CampaignService with dependency injection
- Campaign router with all CRUD endpoints
- Integration with SightingService for campaign validation and locking
- Comprehensive test suite covering all lifecycle scenarios

---

## Commit History

### 5788019 - refactor: implement proper dependency injection across services and controllers

**What changed:**
- Created service factory functions in app/api/deps.py that use FastAPI's Depends() to inject services
- Refactored all services (PokemonService, TrainerService, RangerService, SightingService) to receive repositories via constructor injection instead of creating them internally
- Updated all API controllers to use FastAPI's Depends() for service injection instead of manually instantiating services
- Moved business validation (date range validation) from controllers to service layer
- Removed database session dependency from services (repositories now handle it)
- Removed manual db.rollback() calls from services (repositories handle transactions)

**Why it matters:**
This implements proper dependency injection, which reduces tight coupling between services and their dependencies. Services no longer create their own repositories, making them easier to test with mock objects. Each layer now has clear responsibilities: controllers handle HTTP concerns, services handle business logic, and repositories handle data access. This architectural improvement enables swapping implementations without changing service code and maintains clean separation of concerns throughout the application.

---

### ec19b5d - Extract endpoints into modular v1 router structure

**What changed:**
Extracted all API endpoints from app/main.py into a modular structure under app/api/v1/. Created separate modules for each resource (pokemon.py, rangers.py, sightings.py, trainers.py, users.py) with a central router that includes all sub-routers. Moved database dependency injection to app/api/deps.py. Updated all test files to use the new /v1/ prefix for API endpoints.

**Why it matters:**
Reduces main.py from ~500 lines to ~60 lines, making it easier to navigate and maintain. Follows FastAPI best practices for project structure with clear separation of concerns. Enables future API versioning (v2, v3, etc.) without breaking existing clients. Each resource module is now isolated, making testing and debugging more straightforward. All endpoints now accessible under /v1/ prefix, providing clear API versioning from the start.

---

### ca21756 - Add pre-commit hooks and modernize Python syntax

**What changed:**
- Added pre-commit configuration with ruff (linter/formatter), ty (type checker), and pytest hooks
- Modernized Python syntax to use Python 3.12 features: replaced `Optional[X]` with `X | None`, updated generic class syntax from `Generic[T]` to `[T]`, and changed `datetime.timezone.utc` to `datetime.UTC`
- Added ruff, ty, and pytest configuration to pyproject.toml with linting rules and coverage reporting
- Created helper scripts: check.sh (runs all checks) and format.sh (formats code)
- Fixed type ignore comments in base_repository.py to work with ty type checker

**Why it matters:**
Pre-commit hooks ensure code quality checks run automatically before every commit, preventing issues from being committed. Modern Python syntax improves readability and reduces boilerplate. Automated linting and formatting maintain consistent code style across the team. Type checking catches potential bugs early in development. Test coverage reporting helps identify untested code paths.

---

### 53b468d - Automate commit workflow to eliminate manual input

**What changed:**
Created `.opencode/commands/commit.md` with fully automated commit workflow that auto-generates commit messages from diffs and auto-generates NOTES.md summaries without requiring user input.

**Why it matters:**
Eliminates the need to manually provide commit messages and describe changes. The workflow now analyzes diffs automatically to generate conventional commit messages and human-readable summaries, making the commit process faster and more consistent.

---

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
