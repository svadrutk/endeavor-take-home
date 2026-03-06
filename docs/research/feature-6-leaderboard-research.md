# Feature 6: Ranger Leaderboard - Codebase Research

**Research Date:** 2026-03-06  
**Feature Requirements:** GET /leaderboard endpoint with filtering, sorting, and pagination

---

## Executive Summary

This research provides a comprehensive analysis of the codebase patterns, conventions, and existing implementations that will guide the development of Feature 6: Ranger Leaderboard endpoint.

**Key Findings:**
- Well-established patterns for filtering, pagination, and aggregation
- Clear separation of concerns: API → Service → Repository layers
- Existing aggregation queries in regional summaries and campaign summaries
- Database has 55,000 sightings across 38 rangers with proper indexing
- Rarity tier classification logic already implemented
- No existing leaderboard implementation found

---

## 1. Existing Filtering, Pagination, and Aggregation Patterns

### 1.1 Filtering Pattern (Feature 1 - Sightings)

**File:** `app/api/v1/sightings.py` (lines 18-113)

**Pattern:**
```python
@router.get("/", response_model=PaginatedSightingResponse)
def list_sightings(
    request: Request,
    service: SightingService = Depends(get_sighting_service),
    pokemon_id: int | None = Query(None, description="Filter by Pokemon species ID"),
    region: str | None = Query(None, description="Filter by region name"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
```

**Key Observations:**
- Uses FastAPI's `Query()` for optional filters with descriptions
- Default pagination: `limit=50`, `offset=0`
- Validation: `ge=1, le=200` for limit, `ge=0` for offset
- Returns `PaginatedSightingResponse` with `results`, `total`, `limit`, `offset`
- Service layer handles business logic validation
- Repository layer builds dynamic query with conditional filters

**Repository Implementation:** `app/repositories/sighting_repository.py` (lines 42-77)
```python
def filter_sightings(
    self,
    pokemon_id: int | None = None,
    region: str | None = None,
    # ... other filters
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Sighting], int]:
    query = self.db.query(Sighting)
    
    if pokemon_id is not None:
        query = query.filter(Sighting.pokemon_id == pokemon_id)
    if region is not None:
        query = query.filter(Sighting.region == region)
    # ... more filters
    
    total = query.count()
    sightings = query.order_by(Sighting.date.desc()).offset(skip).limit(limit).all()
    
    return sightings, total
```

### 1.2 Aggregation Patterns

**Regional Summary Aggregation:** `app/repositories/sighting_repository.py` (lines 125-157)

```python
def get_regional_summary_stats(self, region: str) -> dict:
    query_result = (
        self.db.query(
            func.count(Sighting.id).label("total"),
            func.sum(case((Sighting.is_confirmed.is_(True), 1), else_=0)).label("confirmed"),
            func.sum(case((Sighting.is_confirmed.is_(False), 1), else_=0)).label("unconfirmed"),
            func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
        )
        .filter(Sighting.region == region)
        .first()
    )
```

**Campaign Summary Aggregation:** `app/services/campaign_service.py` (lines 115-133)

```python
summary_result = (
    db.query(
        func.count(Sighting.id).label("total_sightings"),
        func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
        func.min(Sighting.date).label("earliest_date"),
        func.max(Sighting.date).label("latest_date"),
    )
    .filter(Sighting.campaign_id == campaign_id)
    .first()
)

rangers = (
    db.query(Ranger.name, func.count(Sighting.id).label("sighting_count"))
    .join(Sighting, Ranger.id == Sighting.ranger_id)
    .filter(Sighting.campaign_id == campaign_id)
    .group_by(Ranger.id)
    .order_by(func.count(Sighting.id).desc())
    .all()
)
```

**Key Aggregation Functions Used:**
- `func.count()` - for counting records
- `func.count(func.distinct())` - for unique counts
- `func.sum(case(...))` - for conditional aggregations
- `func.min()`, `func.max()` - for date ranges
- `.group_by()` - for grouping by ranger/pokemon
- `.order_by(desc("count"))` - for sorting by aggregated values

---

## 2. Sightings Query Patterns (Features 1, 4, 5)

### 2.1 Common Filters

**Available Filter Fields:**
- `pokemon_id` (int) - Filter by Pokemon species
- `region` (str) - Filter by region name (e.g., "Kanto", "Johto")
- `weather` (str) - Filter by weather condition
- `time_of_day` (str) - Filter by time of day
- `ranger_id` (str) - Filter by Ranger UUID
- `date_from` / `date_to` (datetime) - Date range filter
- `is_confirmed` (bool) - Filter by confirmation status
- `campaign_id` (str) - Filter by campaign

### 2.2 Sighting Relationships

**Model:** `app/models.py` (lines 112-171)

```python
class Sighting(Base):
    pokemon_id: Mapped[int] = mapped_column(ForeignKey("pokemon.id"))
    ranger_id: Mapped[str] = mapped_column(ForeignKey("rangers.id"))
    region: Mapped[str]
    is_confirmed: Mapped[bool] = mapped_column(default=False)
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("rangers.id"))
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"))
    is_shiny: Mapped[bool] = mapped_column(default=False)
    
    pokemon: Mapped["Pokemon"] = relationship("Pokemon", init=False, lazy="select")
    ranger: Mapped["Ranger"] = relationship("Ranger", foreign_keys=[ranger_id])
    confirming_ranger: Mapped["Ranger | None"] = relationship("Ranger", foreign_keys=[confirmed_by])
```

**Key Relationships:**
- Sighting → Pokemon (many-to-one)
- Sighting → Ranger (many-to-one, via `ranger_id`)
- Sighting → Ranger (many-to-one, via `confirmed_by`)
- Sighting → Campaign (many-to-one, optional)

---

## 3. Confirmation Status Tracking (Feature 3)

### 3.1 Confirmation Fields

**Model Fields:** `app/models.py` (lines 150-154)
```python
is_confirmed: Mapped[bool] = mapped_column(default=False)
confirmed_by: Mapped[str | None] = mapped_column(
    ForeignKey("rangers.id", ondelete="SET NULL"), default=None, nullable=True
)
confirmed_at: Mapped[datetime | None] = mapped_column(default=None)
```

### 3.2 Confirmation Constraints

**Database Constraints:** `app/models.py` (lines 126-133)
```python
CheckConstraint(
    "(is_confirmed = FALSE) OR (confirmed_by IS NOT NULL)",
    name="ck_sighting_confirmation_integrity",
),
CheckConstraint(
    "(is_confirmed = FALSE) OR (confirmed_at IS NOT NULL)",
    name="ck_sighting_confirmation_timestamp",
),
```

### 3.3 Counting Confirmed Sightings

**Pattern from Regional Summary:** `app/repositories/sighting_repository.py` (line 129)
```python
func.sum(case((Sighting.is_confirmed.is_(True), 1), else_=0)).label("confirmed")
```

**Alternative Pattern:** Direct count with filter
```python
query.filter(Sighting.is_confirmed == True).count()
```

---

## 4. Rarity Tier Calculations (Feature 5)

### 4.1 Rarity Tier Classification

**Service Method:** `app/services/region_service.py` (lines 18-27)

```python
def _classify_rarity_tier(self, pokemon_data: dict) -> str:
    if pokemon_data["is_mythical"]:
        return "mythical"
    if pokemon_data["is_legendary"]:
        return "legendary"
    if pokemon_data["capture_rate"] < 75:
        return "rare"
    if pokemon_data["capture_rate"] < 150:
        return "uncommon"
    return "common"
```

**Rarity Hierarchy (highest to lowest):**
1. **Mythical** - `is_mythical = true`
2. **Legendary** - `is_legendary = true`
3. **Rare** - `capture_rate < 75`
4. **Uncommon** - `75 <= capture_rate < 150`
5. **Common** - `capture_rate >= 150`

**Important:** Legendary/Mythical flags take precedence over capture_rate.

### 4.2 Pokemon Rarity Fields

**Model:** `app/models.py` (lines 27-40)
```python
class Pokemon(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    capture_rate: Mapped[int]
    is_legendary: Mapped[bool] = mapped_column(default=False)
    is_mythical: Mapped[bool] = mapped_column(default=False)
    is_baby: Mapped[bool] = mapped_column(default=False)
```

### 4.3 Shiny Status

**Model Field:** `app/models.py` (line 146)
```python
is_shiny: Mapped[bool] = mapped_column(default=False)
```

**Shiny Priority:** Shiny Pokémon are more valuable than non-shiny of the same species.

---

## 5. Database Models and Relationships

### 5.1 Core Models

**Ranger Model:** `app/models.py` (lines 60-77)
```python
class Ranger(Base):
    __tablename__ = "rangers"
    
    name: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    specialization: Mapped[str]
    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime]
```

**Pokemon Model:** `app/models.py` (lines 27-40)
```python
class Pokemon(Base):
    __tablename__ = "pokemon"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type1: Mapped[str]
    type2: Mapped[str | None]
    generation: Mapped[int]
    capture_rate: Mapped[int]
    is_legendary: Mapped[bool]
    is_mythical: Mapped[bool]
    is_baby: Mapped[bool]
```

**Campaign Model:** `app/models.py` (lines 79-110)
```python
class Campaign(Base):
    __tablename__ = "campaigns"
    
    name: Mapped[str]
    region: Mapped[str]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    status: Mapped[str]  # draft, active, completed, archived
    id: Mapped[str] = mapped_column(primary_key=True)
```

### 5.2 Database Statistics

**Current Data Volume:**
- 55,000 sightings
- 38 rangers
- 493 Pokemon species (Gen I-IV)
- 1 campaign (active)

**Sample Ranger Stats:**
- Top ranger: 1,753 total sightings, 509 confirmed
- Top unique species: 486 different Pokemon observed by one ranger

### 5.3 Database Indexes

**Sighting Indexes:** `app/models.py` (lines 114-124)
```python
Index("idx_sightings_region", "region"),
Index("idx_sightings_ranger_id", "ranger_id"),
Index("idx_sightings_date", "date"),
Index("idx_sightings_pokemon_id", "pokemon_id"),
Index("idx_sightings_ranger_date", "ranger_id", "date"),
Index("idx_sightings_region_date", "region", "date"),
Index("idx_sightings_is_confirmed", "is_confirmed"),
Index("idx_sightings_campaign_id", "campaign_id"),
Index("idx_sightings_campaign_date", "campaign_id", "date"),
```

**Key Indexes for Leaderboard:**
- `idx_sightings_ranger_id` - For filtering by ranger
- `idx_sightings_region` - For filtering by region
- `idx_sightings_date` - For date range filters
- `idx_sightings_is_confirmed` - For confirmed status
- `idx_sightings_campaign_id` - For campaign filtering
- `idx_sightings_ranger_date` - Composite for ranger + date queries

---

## 6. API Endpoint Structure and Conventions

### 6.1 Standard Endpoint Structure

**Pattern:**
1. **API Layer** (`app/api/v1/`) - HTTP concerns, request/response handling
2. **Service Layer** (`app/services/`) - Business logic, validation
3. **Repository Layer** (`app/repositories/`) - Data access, queries

**Example:** `app/api/v1/sightings.py` → `app/services/sighting_service.py` → `app/repositories/sighting_repository.py`

### 6.2 Dependency Injection

**Pattern:** `app/api/deps.py` (lines 29-63)

```python
def get_sighting_service(db: Session = Depends(get_db)) -> SightingService:
    sighting_repo = SightingRepository(db)
    pokemon_repo = PokemonRepository(db)
    ranger_repo = RangerRepository(db)
    campaign_service = get_campaign_service(db)
    return SightingService(sighting_repo, pokemon_repo, ranger_repo, campaign_service)
```

**Usage in Endpoints:**
```python
@router.get("/")
def list_sightings(
    service: SightingService = Depends(get_sighting_service),
):
```

### 6.3 Response Format Conventions

**Paginated Response:** `app/schemas.py` (lines 141-146)
```python
class PaginatedSightingResponse(BaseModel):
    results: list[SightingResponse]
    total: int
    limit: int
    offset: int
```

**Standard Response Pattern:**
- Use Pydantic models with `model_config = ConfigDict(from_attributes=True)`
- Include related entity names (e.g., `pokemon_name`, `ranger_name`)
- Return tuples from service layer: `(entity, related_entity1, related_entity2)`

### 6.4 Error Handling Patterns

**Pattern:** `app/api/v1/sightings.py` (lines 63-69)
```python
try:
    # Business logic
except ValueError as e:
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["error"] = {
            "type": "ValidationError",
            "message": str(e),
        }
    raise HTTPException(status_code=400, detail=str(e)) from None
```

**Common HTTP Status Codes:**
- 200: Success (GET, POST that returns data)
- 201: Created (POST for new resources)
- 400: Validation error
- 401: Authentication required
- 403: Permission denied / wrong role
- 404: Resource not found
- 409: Conflict (e.g., already confirmed)

### 6.5 Wide Event Logging

**Middleware:** `app/middleware.py` (lines 12-57)

Every request logs a single "wide event" with:
- Request metadata (method, path, query params, client IP)
- User context (ID, role)
- Response metadata (status code, duration)
- Error details (if applicable)

**Usage in Endpoints:**
```python
if hasattr(request.state, "wide_event"):
    request.state.wide_event["filter_params"] = {
        "region": region,
        "date_from": str(date_from) if date_from else None,
    }
    request.state.wide_event["results_count"] = len(results)
```

---

## 7. Performance Patterns

### 7.1 Query Optimization Strategies

**From Regional Summary Implementation:**
1. **Single Aggregation Query** - Use `func.count()`, `func.sum()`, `func.distinct()` in one query
2. **Avoid N+1 Queries** - Fetch related entities in bulk using `get_by_ids()`
3. **Use Indexes** - Leverage existing indexes for filtering
4. **Lazy Loading** - Use `lazy="select"` for relationships (default)

**Example:** `app/services/region_service.py` (lines 76-84)
```python
# Fetch top pokemon IDs
top_pokemon_data = self.sighting_repo.get_top_pokemon_by_region(region_title)
pokemon_ids = [p[0] for p in top_pokemon_data]

# Batch fetch pokemon names (avoid N+1)
pokemon_list = self.pokemon_repo.get_by_ids(pokemon_ids)
pokemon_map = {p.id: p.name for p in pokemon_list}
```

### 7.2 Batch Loading Pattern

**Repository Method:** `app/repositories/pokemon_repository.py` (lines 33-36)
```python
def get_by_ids(self, ids: list[int]) -> list[Pokemon]:
    if not ids:
        return []
    return self.db.query(Pokemon).filter(Pokemon.id.in_(ids)).all()
```

**Similar for Rangers:** `app/repositories/ranger_repository.py` (lines 17-20)

### 7.3 Pagination Best Practices

**From Feature 1:**
- Default `limit=50`, max `limit=200`
- Always return `total` count for pagination UI
- Use `offset` and `limit` in SQL query
- Count before applying offset/limit

### 7.4 Index Usage

**Query Optimization Tips:**
- Filter by indexed columns first
- Use composite indexes for multi-column filters
- `idx_sightings_ranger_date` for ranger + date range queries
- `idx_sightings_region_date` for region + date range queries

---

## 8. Testing Patterns

### 8.1 Test Structure

**File:** `tests/test_public.py`

**Test Categories:**
- Unit tests for business logic
- Integration tests for API endpoints
- Contract tests for schema validation

**Test Fixtures:** `tests/conftest.py`
- `db_session` - In-memory SQLite database
- `client` - FastAPI test client
- `sample_pokemon` - Pre-populated Pokemon data
- `sample_ranger`, `second_ranger` - Test rangers
- `sample_sighting` - Test sighting

### 8.2 Test Patterns for Filtering/Pagination

**Example:** `tests/test_public.py` (lines 286-369)
```python
def test_pagination(self, client, sample_sighting):
    response = client.get("/v1/sightings?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert data["limit"] == 10
    assert data["offset"] == 0

def test_filter_by_region(self, client, sample_sighting):
    response = client.get("/v1/sightings?region=Kanto")
    assert response.status_code == 200
    data = response.json()
    assert all(s["region"] == "Kanto" for s in data["results"])

def test_multiple_filters(self, client, sample_ranger, second_ranger):
    # Create test data
    # Apply multiple filters
    # Verify results match all filter criteria
```

### 8.3 Test Data Generation

**Pattern:** Create test data in test, then verify filtering/aggregation
```python
sighting1 = client.post("/v1/sightings", json={...})
sighting2 = client.post("/v1/sightings", json={...})

response = client.get("/v1/sightings?region=Kanto&weather=sunny")
assert all(s["region"] == "Kanto" and s["weather"] == "sunny" for s in data["results"])
```

---

## 9. Implementation Recommendations

### 9.1 Leaderboard Query Strategy

**Recommended Approach:**

1. **Single Aggregation Query per Ranger:**
```python
from sqlalchemy import func, case, desc

leaderboard_data = (
    db.query(
        Sighting.ranger_id,
        func.count(Sighting.id).label("total_sightings"),
        func.sum(case((Sighting.is_confirmed == True, 1), else_=0)).label("confirmed_sightings"),
        func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
    )
    .filter(/* apply filters */)
    .group_by(Sighting.ranger_id)
    .order_by(desc("total_sightings"))  # or other sort field
    .offset(skip)
    .limit(limit)
    .all()
)
```

2. **Rarest Pokemon Subquery:**
```python
# For each ranger, find their rarest Pokemon
# Use CASE statement to assign rarity score
# Higher score = rarer (mythical=5, legendary=4, rare=3, uncommon=2, common=1)
# Shiny adds +0.5 to score
```

3. **Batch Load Related Data:**
```python
ranger_ids = [row.ranger_id for row in leaderboard_data]
rangers = ranger_repo.get_by_ids(ranger_ids)
ranger_map = {r.id: r for r in rangers}
```

### 9.2 Sorting Implementation

**Dynamic Sorting:**
```python
sort_field = sort_by or "total_sightings"  # default
valid_sort_fields = ["total_sightings", "confirmed_sightings", "unique_species"]

if sort_field not in valid_sort_fields:
    raise ValueError(f"Invalid sort field: {sort_field}")

# Use in order_by clause
query = query.order_by(desc(sort_field))
```

### 9.3 Filter Implementation

**Apply Filters Before Aggregation:**
```python
query = db.query(...).group_by(Sighting.ranger_id)

if region:
    query = query.filter(Sighting.region == region)
if date_from:
    query = query.filter(Sighting.date >= date_from)
if date_to:
    query = query.filter(Sighting.date <= date_to)
if campaign_id:
    query = query.filter(Sighting.campaign_id == campaign_id)
```

### 9.4 Rarest Pokemon Logic

**Approach:**
1. For each ranger, query their sightings joined with Pokemon
2. Calculate rarity score:
   - Mythical: 5.0
   - Legendary: 4.0
   - Rare: 3.0
   - Uncommon: 2.0
   - Common: 1.0
   - Shiny bonus: +0.5
3. Select Pokemon with highest rarity score
4. If tie, prefer shiny, then alphabetical by name

**SQL Pattern:**
```python
from sqlalchemy import case

rarity_score = case(
    (Pokemon.is_mythical == True, 5.0),
    (Pokemon.is_legendary == True, 4.0),
    (Pokemon.capture_rate < 75, 3.0),
    (Pokemon.capture_rate < 150, 2.0),
    else_=1.0
) + case((Sighting.is_shiny == True, 0.5), else_=0.0)

rarest = (
    db.query(Sighting, Pokemon, rarity_score.label("score"))
    .join(Pokemon)
    .filter(Sighting.ranger_id == ranger_id)
    .order_by(desc("score"), desc(Sighting.is_shiny), Pokemon.name)
    .first()
)
```

### 9.5 Response Schema

**Recommended Schema:**
```python
class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    ranger_id: str
    ranger_name: str
    total_sightings: int
    confirmed_sightings: int
    unique_species: int
    rarest_pokemon: RarestPokemon | None

class RarestPokemon(BaseModel):
    pokemon_id: int
    pokemon_name: str
    rarity_tier: str
    is_shiny: bool

class PaginatedLeaderboardResponse(BaseModel):
    results: list[LeaderboardEntry]
    total: int
    limit: int
    offset: int
```

### 9.6 Performance Considerations

**Optimization Strategies:**
1. **Use Existing Indexes:**
   - `idx_sightings_ranger_id` for grouping
   - `idx_sightings_region` for region filter
   - `idx_sightings_date` for date range
   - `idx_sightings_campaign_id` for campaign filter

2. **Avoid N+1 Queries:**
   - Batch load ranger details
   - Consider subquery for rarest Pokemon (may need optimization)

3. **Pagination at Database Level:**
   - Apply `offset` and `limit` to aggregation query
   - Count total rangers matching filters (not total sightings)

4. **Potential Caching:**
   - Cache leaderboard results for popular filter combinations
   - Consider materialized view for global leaderboard

---

## 10. Gotchas and Considerations

### 10.1 Data Integrity

**Confirmation Status:**
- `is_confirmed` can be False even if `confirmed_by` is set (edge case)
- Database constraints ensure consistency, but verify in queries

**Campaign Status:**
- Only `active` campaigns accept new sightings
- Completed campaigns lock their sightings

### 10.2 Edge Cases

**Empty Results:**
- Return empty list with `total=0` if no rangers match filters
- Handle case where ranger has no sightings

**Rarest Pokemon Ties:**
- Define clear tie-breaking rules
- Document in NOTES.md

**Date Range Validation:**
- Validate `date_from <= date_to` in service layer
- Return 400 error with clear message

### 10.3 Performance Gotchas

**Large Datasets:**
- 55,000 sightings across 38 rangers
- Average ~1,447 sightings per ranger
- Aggregation queries should be efficient with proper indexes

**Rarest Pokemon Query:**
- Could be expensive if done per ranger
- Consider:
  - Subquery in main aggregation
  - Separate query batch-loaded after main results
  - Pre-computed rarest Pokemon per ranger

### 10.4 API Design Considerations

**Endpoint Path:**
- Use `/v1/leaderboard` (following existing convention)
- Not `/v1/rangers/leaderboard` (leaderboard is a separate concept)

**Query Parameters:**
- `region`, `date_from`, `date_to`, `campaign_id` - filters
- `sort_by` - sorting field (default: "total_sightings")
- `limit`, `offset` - pagination

**Authentication:**
- Public endpoint (no authentication required based on requirements)
- Or optional authentication for personalized results?

---

## 11. File Structure for Implementation

### 11.1 New Files to Create

```
app/
├── api/v1/
│   └── leaderboard.py          # New endpoint
├── services/
│   └── leaderboard_service.py  # New service
├── repositories/
│   └── leaderboard_repository.py  # New repository (or add to sighting_repository.py)
└── schemas.py                  # Add leaderboard schemas

tests/
└── test_public.py              # Add TestCandidateLeaderboard class
```

### 11.2 Files to Modify

```
app/
├── api/v1/router.py            # Include leaderboard router
├── api/deps.py                 # Add get_leaderboard_service
└── schemas.py                  # Add leaderboard response models

docs/
└── research/
    └── feature-6-leaderboard-research.md  # This file
```

---

## 12. Technology Stack Summary

**Core Technologies:**
- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** SQLite
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic
- **Testing:** pytest
- **Logging:** structlog (wide events)

**Key Libraries:**
- `fastapi` - Web framework
- `sqlalchemy` - ORM and query builder
- `pydantic` - Data validation
- `pytest` - Testing framework
- `structlog` - Structured logging
- `slowapi` - Rate limiting

**Python 3.12 Features Used:**
- `X | None` instead of `Optional[X]`
- Modern generic syntax `class Repository[ModelType]`
- `datetime.UTC` for timezone-aware datetimes

---

## 13. Next Steps

### 13.1 Implementation Order

1. **Create Schemas** (`app/schemas.py`)
   - `LeaderboardEntry`
   - `RarestPokemon`
   - `PaginatedLeaderboardResponse`

2. **Create Repository** (`app/repositories/leaderboard_repository.py` or add to `sighting_repository.py`)
   - `get_leaderboard_stats()`
   - `get_rarest_pokemon_for_ranger()`

3. **Create Service** (`app/services/leaderboard_service.py`)
   - `get_leaderboard()`
   - Rarity calculation logic
   - Filter validation

4. **Create API Endpoint** (`app/api/v1/leaderboard.py`)
   - `GET /leaderboard`
   - Query parameter handling
   - Response formatting

5. **Wire Dependencies** (`app/api/deps.py`, `app/api/v1/router.py`)
   - Add `get_leaderboard_service()`
   - Include leaderboard router

6. **Write Tests** (`tests/test_public.py`)
   - Test pagination
   - Test filtering
   - Test sorting
   - Test rarest Pokemon logic

### 13.2 Testing Strategy

**Test Categories:**
1. **Unit Tests** - Rarity calculation, sorting logic
2. **Integration Tests** - API endpoint with database
3. **Edge Case Tests** - Empty results, ties, invalid filters

**Test Data:**
- Create rangers with different sighting counts
- Include confirmed/unconfirmed sightings
- Include various Pokemon rarity tiers
- Include shiny/non-shiny variants

---

## 14. References

### 14.1 Key Files

**Models:**
- `app/models.py` - Lines 27-171 (Pokemon, Ranger, Sighting, Campaign)

**Schemas:**
- `app/schemas.py` - Lines 1-250 (All response models)

**Existing Aggregations:**
- `app/repositories/sighting_repository.py` - Lines 125-218 (Regional stats, rarity analysis)
- `app/services/campaign_service.py` - Lines 108-152 (Campaign summary)
- `app/services/region_service.py` - Lines 64-189 (Regional summary and analysis)

**Filtering/Pagination:**
- `app/api/v1/sightings.py` - Lines 18-113 (Sighting filters)
- `app/repositories/sighting_repository.py` - Lines 42-77 (Filter implementation)

**Testing:**
- `tests/test_public.py` - Lines 275-500 (Candidate tests)
- `tests/conftest.py` - Lines 1-225 (Test fixtures)

### 14.2 Documentation

**Project Documentation:**
- `README.md` - Lines 256-271 (Feature 6 requirements)
- `NOTES.md` - Development notes and design decisions
- `TESTING_STRATEGY.md` - Testing patterns for statistical features

**Database:**
- Schema: `sqlite3 poketracker.db ".schema"`
- Data: 55,000 sightings, 38 rangers, 493 Pokemon

---

## Conclusion

The codebase provides excellent patterns for implementing the Ranger Leaderboard feature:

✅ **Well-established patterns** for filtering, pagination, and aggregation  
✅ **Clear separation of concerns** across API, Service, and Repository layers  
✅ **Existing implementations** to reference (regional summaries, campaign summaries)  
✅ **Proper database indexing** for performance  
✅ **Comprehensive testing patterns** to follow  
✅ **Rarity tier logic** already implemented  

**Primary Implementation Challenges:**
1. Efficiently calculating rarest Pokemon per ranger
2. Handling ties in rarity scores
3. Optimizing aggregation queries for large datasets

**Recommended Approach:**
- Follow existing patterns closely
- Implement rarest Pokemon as separate query (optimize later if needed)
- Use existing indexes and batch loading patterns
- Write comprehensive tests covering edge cases

The feature is well-scoped and the codebase provides all necessary building blocks for a clean, performant implementation.
