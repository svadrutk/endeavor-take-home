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

## Phase 2: Identity & Lookup Endpoints Refactoring

### Issues Fixed

The Identity & Lookup endpoints had several data quality and consistency issues:

1. **Missing response model on POST /trainers** (app/main.py:47)
   - Added `response_model=TrainerResponse` to match POST /rangers
   - Ensures consistent API documentation and response validation

2. **No input validation for empty strings**
   - Added `Field(..., min_length=1)` to `name` and `specialization` fields in schemas
   - Prevents empty string values from being accepted
   - Updated both `TrainerCreate` and `RangerCreate` schemas

3. **No email format validation**
   - Changed `email: str` to `email: EmailStr` in both `TrainerCreate` and `RangerCreate`
   - Uses Pydantic's built-in email validation
   - Rejects invalid email formats like "invalid-email"

4. **No duplicate prevention**
   - Added `unique=True` constraint to `name` and `email` fields in both `Trainer` and `Ranger` models
   - Added `String(128)` length limit for name fields
   - Added `String(255)` length limit for email fields
   - Prevents multiple users with same name or email at database level

5. **No conflict handling for duplicates**
   - Added `IntegrityError` exception handling in both POST endpoints
   - Returns 409 Conflict status code with clear error message
   - Properly rolls back database transaction on conflict

6. **User lookup ambiguity**
   - With unique constraints in place, the lookup endpoint now guarantees at most one match
   - The existing implementation (returning first match) is now safe and predictable

### Design Decisions

- **Unique constraints on both name and email**: This ensures that each user can be uniquely identified by either field, which is important for the lookup endpoint and prevents data quality issues.
- **409 Conflict for duplicates**: Following REST conventions, we return 409 when attempting to create a resource that would conflict with an existing one.
- **EmailStr validation**: Using Pydantic's built-in email validator is more robust than custom regex patterns and handles edge cases better.
- **String length limits**: Added reasonable length limits (128 for names, 255 for emails) to prevent database bloat and potential issues with very long strings.

### Database Migration Note

Since we added unique constraints to existing fields, the database schema has changed. The existing database file (`poketracker.db`) will need to be recreated or migrated. The seed script should be re-run after these changes.

## Phase 3: Performance & Architecture Refactoring

### Critical Performance Issues Addressed

The main performance bottleneck was **missing database indexes** on the `sightings` table. With 55,000 records, queries were doing full table scans.

**Before:**
```sql
EXPLAIN QUERY PLAN SELECT * FROM sightings WHERE region = 'Kanto' LIMIT 50;
-- Result: SCAN sightings (full table scan)
```

**After adding indexes:**
```sql
EXPLAIN QUERY PLAN SELECT * FROM sightings WHERE region = 'Kanto' LIMIT 50;
-- Result: SEARCH sightings USING INDEX idx_sightings_region (region=?)
```

**Indexes added:**
- `idx_sightings_region` - Filter by region (16,472 Kanto records alone)
- `idx_sightings_ranger_id` - Filter by ranger
- `idx_sightings_date` - ORDER BY operations
- `idx_sightings_pokemon_id` - Filter by species
- `idx_sightings_is_confirmed` - Filter by confirmation status
- `idx_sightings_ranger_date` - Composite index for common query pattern
- `idx_sightings_region_date` - Composite index for regional analysis

**Expected performance improvement:** 10-100x faster for filtered queries, especially on large regions like Kanto.

### Architecture Refactoring: Services/Repositories Pattern

**Problem:** All business logic was embedded in route handlers, making it hard to test, reuse, and maintain.

**Solution:** Implemented a clean separation of concerns:

```
app/
├── main.py (routes only - thin controllers)
├── services/ (business logic)
│   ├── trainer_service.py
│   ├── ranger_service.py
│   ├── pokemon_service.py
│   └── sighting_service.py
├── repositories/ (data access layer)
│   ├── base_repository.py
│   ├── trainer_repository.py
│   ├── ranger_repository.py
│   ├── pokemon_repository.py
│   └── sighting_repository.py
├── models.py (database models)
└── schemas.py (API contracts)
```

**Benefits:**
- **Testability:** Services can be unit tested independently of routes
- **Reusability:** Business logic can be reused across different endpoints
- **Maintainability:** Clear separation makes code easier to understand and modify
- **Single Responsibility:** Each layer has one job

### Logging Implementation with structlog

**Why structlog?**
- Structured logging with JSON output for production
- Human-readable console output for development
- Context binding for request tracing
- Better performance than standard logging

**Configuration:**
- JSON format in production (parseable by log aggregators)
- Console format in development (human-readable)
- Automatic context: app name, timestamp, log level
- Request context binding for tracing

**Example log output:**
```json
{
  "event": "Creating sighting",
  "pokemon_id": 25,
  "ranger_id": "...",
  "region": "Kanto",
  "logger": "app.main",
  "level": "info",
  "app": "poketracker",
  "timestamp": "2026-03-06T05:20:51.289676Z"
}
```

### Rate Limiting with slowapi

**Why rate limiting?**
- Prevent API abuse
- Protect against DoS attacks
- Ensure fair usage across clients
- Reduce load on database

**Implementation:**
- Used slowapi (FastAPI wrapper for limits)
- Rate limits per endpoint type:
  - **Read operations:** 100/minute (generous for browsing)
  - **Write operations:** 10/minute (prevent spam)
- IP-based limiting using `get_remote_address`
- Custom 429 error handler with clear message

**Example:**
```python
@app.post("/sightings")
@limiter.limit("10/minute")
def create_sighting(...):
    ...
```

### Error Message Improvements

**Before:**
```python
raise HTTPException(status_code=404, detail="Trainer not found")
```

**After:**
```python
raise HTTPException(
    status_code=404,
    detail=f"Trainer with ID '{trainer_id}' not found"
)
```

**Benefits:**
- More context for debugging
- Clearer error messages for API consumers
- Include relevant IDs in error messages
- Distinguish between "not found" and "permission denied"

### Fixed Deprecated datetime.utcnow()

**Problem:** `datetime.utcnow()` is deprecated in Python 3.12+ and will be removed.

**Solution:**
```python
# Before
from datetime import datetime
created_at: Mapped[datetime] = mapped_column(
    default_factory=datetime.utcnow
)

# After
from datetime import datetime, timezone
created_at: Mapped[datetime] = mapped_column(
    default_factory=lambda: datetime.now(timezone.utc)
)
```

### Design Decisions & Trade-offs

1. **Repository Pattern Over Active Record**
   - **Decision:** Separate data access from business logic
   - **Trade-off:** More boilerplate code, but better testability
   - **Rationale:** With 7 features to implement, clean architecture pays off

2. **Service Layer for Business Logic**
   - **Decision:** All validation and business rules in services
   - **Trade-off:** Additional layer of indirection
   - **Rationale:** Routes stay thin, logic is reusable and testable

3. **Composite Indexes**
   - **Decision:** Added both single-column and composite indexes
   - **Trade-off:** Slightly slower writes, much faster reads
   - **Rationale:** Read-heavy workload (researchers querying data)

4. **Rate Limiting Strategy**
   - **Decision:** IP-based, different limits for read vs write
   - **Trade-off:** Could block legitimate users behind NAT
   - **Rationale:** Simple to implement, good enough for research tool

5. **Optional Pagination on Region Endpoint**
   - **Decision:** Support both paginated and non-paginated responses
   - **Trade-off:** More complex endpoint logic
   - **Rationale:** Backward compatibility with existing tests

6. **JSON Logging in Production**
   - **Decision:** Use JSON format for logs
   - **Trade-off:** Less human-readable in raw logs
   - **Rationale:** Better for log aggregation and analysis tools

### Performance Impact

**Query Performance (estimated):**
- Region filter (Kanto, 16,472 records): ~100x faster with index
- Ranger sightings: ~50x faster with composite index
- Date range queries: ~80x faster with date index

**Memory Impact:**
- Additional indexes: ~2-5MB storage overhead
- Negligible for 55,000 records

**Write Performance:**
- Slightly slower inserts (updating indexes)
- Acceptable for research tool (not high-frequency writes)

### Testing

All 24 existing tests pass after refactoring:
- Trainer/Ranger registration: ✓
- User lookup: ✓
- Pokédex operations: ✓
- Sighting CRUD: ✓
- Error handling: ✓

### Next Steps

With the architecture in place, implementing the 7 features will be straightforward:
1. Feature 1: Sighting filters & pagination (service method ready)
2. Feature 2: Research campaigns (new model + service)
3. Feature 3: Peer confirmation (extend Sighting model)
4. Feature 4: Regional summary (aggregation queries)
5. Feature 5: Rarity analysis (statistical methods)
6. Feature 6: Leaderboard (ranking queries)
7. Feature 7: Trainer catch tracking (new model + service)

## Phase 4: Logging Refactoring with Wide Events Pattern

### Overview

Refactored the entire logging system to follow the **Wide Events** (Canonical Log Lines) pattern, which is a best practice for modern observability. This pattern consolidates all request context into a single, rich log event per request, enabling powerful debugging and analytics.

### Key Changes

#### 1. Wide Event Middleware (`app/middleware.py`)

**Created a new middleware** that handles all logging infrastructure:

- **Request ID Generation**: Unique ID for each request (from `X-Request-ID` header or auto-generated)
- **Timing**: Automatic duration tracking in milliseconds
- **Environment Context**: Automatically includes deployment info (commit hash, version, region, etc.)
- **Error Handling**: Captures errors and adds structured error information
- **Emission**: Emits the complete event in a `finally` block, ensuring logs are always written

**Example wide event:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/sightings",
  "query_params": {},
  "client_ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "app": "poketracker",
  "version": "0.0.1",
  "commit_hash": "abc123",
  "environment": "production",
  "region": "us-east-1",
  "status_code": 200,
  "outcome": "success",
  "duration_ms": 45.23,
  "sighting": {
    "id": "sighting-uuid",
    "pokemon_id": 25,
    "pokemon_name": "Pikachu",
    "ranger_id": "ranger-uuid",
    "ranger_name": "Ash",
    "region": "Kanto"
  }
}
```

#### 2. Environment Context (`app/logging_config.py`)

**Added environment characteristics** to every log event:

- `app`: Application name
- `version`: Service version (from `SERVICE_VERSION` env var)
- `commit_hash`: Git commit SHA (from `COMMIT_SHA` or `GIT_COMMIT` env var)
- `environment`: Environment type (from `ENVIRONMENT` or `NODE_ENV` env var)
- `region`: Deployment region (from `REGION` env var)
- `instance_id`: Instance identifier (from `HOSTNAME` env var)

**Why this matters:**
- Instantly identify which code version caused an issue
- Correlate errors with specific deployments
- Identify region-specific failures
- Debug issues affecting specific instances

#### 3. Route Handlers Refactored (`app/main.py`)

**Removed all scattered log statements** and replaced with business context enrichment:

**Before (scattered logs):**
```python
def create_trainer(...):
    logger.info("Creating trainer", name=trainer.name)
    # ... business logic ...
    logger.info("Trainer created", trainer_id=new_trainer.id)
    return new_trainer
```

**After (business context only):**
```python
def create_trainer(...):
    service = TrainerService(db)
    new_trainer = service.create_trainer(trainer)
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["trainer"] = {
            "id": new_trainer.id,
            "name": new_trainer.name,
        }
    return new_trainer
```

**Benefits:**
- Single log per request with complete context
- No scattered log statements throughout the code
- Business context is queryable (e.g., "show me all trainers created by user X")
- Middleware handles timing, status, and emission automatically

#### 4. Services Refactored (All `app/services/*.py`)

**Removed all logging from services:**

- Services now focus purely on business logic
- No logger instances or log statements
- Route handlers are responsible for adding business context to wide events
- Cleaner, more testable code

**Rationale:** Services should not be concerned with logging. The route handler knows the full business context and is the right place to enrich the wide event.

### Design Decisions

#### 1. Wide Events Over Scattered Logs

**Decision:** Emit one context-rich event per request instead of multiple log lines.

**Rationale:**
- **Queryability**: Can query by any field (user_id, pokemon_id, region, etc.)
- **Completeness**: All context in one place, nothing lost
- **Performance**: Fewer log writes, better I/O
- **Debugging**: Can answer questions you haven't anticipated yet

**Trade-off:** Slightly more complex middleware setup, but massive gains in observability.

#### 2. Middleware Pattern for Logging Infrastructure

**Decision:** Use middleware to handle timing, status, environment, and emission.

**Rationale:**
- **Consistency**: Every request gets the same treatment
- **DRY**: No repeated timing/status code in each handler
- **Reliability**: `finally` block ensures logs are always written
- **Separation of Concerns**: Handlers focus on business logic, middleware handles logging

**Trade-off:** Less flexibility in log emission timing, but this is actually a feature (ensures consistency).

#### 3. Environment Context in Every Event

**Decision:** Include deployment info (commit hash, version, region) in every log event.

**Rationale:**
- **Deployment Correlation**: Instantly know which code version caused an issue
- **Region Debugging**: Identify region-specific problems
- **Instance Tracking**: Debug issues affecting specific instances
- **Version Tracking**: Track issues across service versions

**Trade-off:** Slightly larger log events, but the value far outweighs the cost.

#### 4. Business Context in Wide Events

**Decision:** Include business-specific context (trainer, ranger, pokemon, sighting details).

**Rationale:**
- **Business Impact**: Know "enterprise customer couldn't complete $2,499 order" not just "error 500"
- **Prioritization**: Can prioritize issues based on business context
- **Analytics**: Enable business analytics from logs
- **Unknown Unknowns**: Can answer questions you haven't thought of yet

**Example:** Instead of "Sighting created", we log the full sighting context (pokemon, ranger, region, etc.).

#### 5. Simplified Log Levels

**Decision:** Use only `info` and `error` levels.

**Rationale:**
- **Clarity**: No confusion between debug/trace/warn/info/critical
- **Simplicity**: Two levels are sufficient
- **Wide Events**: Context is in the event, not the log level
- **Best Practice**: Recommended by logging experts

**Implementation:**
- `info`: All successful requests and wide events
- `error`: Unexpected failures that need attention

#### 6. JSON Format for Production

**Decision:** Use JSON format in production, human-readable console in development.

**Rationale:**
- **Parseability**: JSON is universally supported by log aggregators
- **Queryability**: Can query by any field in the JSON
- **Standards**: Works with ELK, Datadog, CloudWatch, etc.
- **Development UX**: Console renderer for local development

**Configuration:** Controlled by `ENVIRONMENT` environment variable.

#### 7. Request ID Propagation

**Decision:** Generate unique request ID and include in every log event.

**Rationale:**
- **Tracing**: Can trace a single request through the system
- **Correlation**: Link related events together
- **Debugging**: Find all logs for a specific request
- **Distributed Tracing**: Can propagate to downstream services

**Implementation:** Uses `X-Request-ID` header if provided, otherwise generates UUID.

### Benefits of Wide Events Pattern

1. **Queryability**: Can query logs by any field (user_id, pokemon_id, region, error type, etc.)
2. **Completeness**: All context in one place, nothing lost
3. **Performance**: Fewer log writes, better I/O
4. **Debugging**: Can answer questions you haven't anticipated yet
5. **Business Context**: Know the business impact of errors
6. **Deployment Correlation**: Instantly know which code version caused an issue
7. **Analytics**: Enable business analytics from logs

### Example Use Cases Enabled

**Before (scattered logs):**
- "Show me all errors for user X" → Not possible (logs don't have user_id)
- "Show me all sightings created in Kanto" → Not possible (logs don't have region)
- "Which code version caused this error?" → Not possible (logs don't have commit_hash)

**After (wide events):**
- "Show me all errors for user X" → `SELECT * FROM logs WHERE user.id = 'X' AND outcome = 'error'`
- "Show me all sightings created in Kanto" → `SELECT * FROM logs WHERE sighting.region = 'Kanto'`
- "Which code version caused this error?" → `SELECT commit_hash FROM logs WHERE request_id = 'X'`

### Migration Notes

**Environment Variables to Set:**
```bash
export SERVICE_VERSION="0.0.1"
export COMMIT_SHA="abc123"  # or GIT_COMMIT
export ENVIRONMENT="production"  # or "development"
export REGION="us-east-1"
export HOSTNAME="instance-1"
```

**Log Aggregator Configuration:**
- Configure your log aggregator (Datadog, CloudWatch, ELK) to parse JSON logs
- Index on fields: `request_id`, `user.id`, `sighting.id`, `error.type`, `commit_hash`
- Set up dashboards for: error rates by commit, response times by endpoint, business metrics

### Testing

All existing tests pass after refactoring. The logging changes are non-breaking and purely additive - they don't change the API behavior, only how requests are logged.

### References

- [Logging Sucks](https://loggingsucks.com) - Original wide events pattern
- [Observability Wide Events 101](https://boristane.com/blog/observability-wide-events-101/)
- [Stripe - Canonical Log Lines](https://stripe.com/blog/canonical-log-lines)
