---
title: feat: Sighting Filters & Pagination
type: feat
status: active
date: 2026-03-06
---

# feat: Sighting Filters & Pagination

## Overview

Implement a `GET /sightings` endpoint that allows field researchers to query and browse Pokémon sightings with flexible filtering and pagination. This addresses the Field Research Coordinator's request for better data exploration capabilities as the dataset has grown to over 50,000 records.

## Problem Statement / Motivation

**Request from**: Field Research Coordinator

> "Right now there's no way to browse sightings with any kind of filter. We need an endpoint that lets us query sightings by species, region, weather, time of day, date range, and ranger — ideally with support for combining multiple filters. We also need pagination since some regions have thousands of records."

**Current state**: 
- No endpoint exists to list/query sightings with filters
- Rangers can only view their own sightings via `/rangers/{ranger_id}/sightings`
- Dataset has grown to 55,004 sightings across dozens of regions
- Some regions (like Kanto) have 10,000+ records, making browsing impractical without pagination

**Impact**: Field researchers cannot efficiently explore historical data, identify patterns, or extract insights from the growing dataset.

## Proposed Solution

Create a new `GET /v1/sightings` endpoint that:
1. Accepts optional query parameters for filtering
2. Supports combining multiple filters
3. Implements pagination with sensible defaults
4. Returns both the filtered results and total count
5. Follows existing codebase patterns for consistency

## Technical Approach

### Architecture

The implementation follows the existing three-layer architecture:

```
API Layer (app/api/v1/sightings.py)
  ↓ Query parameter validation & request handling
Service Layer (app/services/sighting_service.py)
  ↓ Business logic & data enrichment
Repository Layer (app/repositories/sighting_repository.py)
  ↓ Database queries with filters
```

**Good news**: The repository and service layers already have `filter_sightings()` methods implemented! We only need to create the API endpoint.

### Implementation Details

#### 1. API Endpoint (`app/api/v1/sightings.py`)

Add a new GET endpoint at the router root:

```python
@router.get("/", response_model=PaginatedSightingResponse)
def list_sightings(
    request: Request,
    db: Session = Depends(get_db),
    pokemon_id: int | None = Query(None, description="Filter by Pokemon species ID"),
    region: str | None = Query(None, description="Filter by region name"),
    weather: str | None = Query(None, description="Filter by weather condition"),
    time_of_day: str | None = Query(None, description="Filter by time of day"),
    ranger_id: str | None = Query(None, description="Filter by Ranger UUID"),
    date_from: datetime | None = Query(None, description="Filter sightings from this date (inclusive)"),
    date_to: datetime | None = Query(None, description="Filter sightings to this date (inclusive)"),
    is_confirmed: bool | None = Query(None, description="Filter by confirmation status"),
    limit: int = Query(50, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List sightings with optional filters and pagination.
    
    Supports filtering by:
    - pokemon_id: Pokemon species ID
    - region: Region name (e.g., "Kanto", "Johto")
    - weather: Weather condition (sunny, rainy, snowy, sandstorm, foggy, clear)
    - time_of_day: Time of day (morning, day, night)
    - ranger_id: Ranger UUID
    - date_from: Start of date range (inclusive)
    - date_to: End of date range (inclusive)
    - is_confirmed: Confirmation status
    
    Returns paginated results with total count.
    """
    service = SightingService(db)
    
    sightings_data, total = service.filter_sightings(
        pokemon_id=pokemon_id,
        region=region,
        weather=weather,
        time_of_day=time_of_day,
        ranger_id=ranger_id,
        date_from=date_from,
        date_to=date_to,
        is_confirmed=is_confirmed,
        skip=offset,
        limit=limit,
    )
    
    # Construct response with Pokemon and Ranger names
    results = []
    for sighting, pokemon, ranger in sightings_data:
        results.append(
            SightingResponse(
                id=sighting.id,
                pokemon_id=sighting.pokemon_id,
                ranger_id=sighting.ranger_id,
                region=sighting.region,
                route=sighting.route,
                date=sighting.date,
                weather=sighting.weather,
                time_of_day=sighting.time_of_day,
                height=sighting.height,
                weight=sighting.weight,
                is_shiny=sighting.is_shiny,
                notes=sighting.notes,
                is_confirmed=sighting.is_confirmed,
                pokemon_name=pokemon.name if pokemon else None,
                ranger_name=ranger.name if ranger else None,
            )
        )
    
    # Wide event logging for observability
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["filter_params"] = {
            "pokemon_id": pokemon_id,
            "region": region,
            "weather": weather,
            "time_of_day": time_of_day,
            "ranger_id": ranger_id,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "is_confirmed": is_confirmed,
        }
        request.state.wide_event["results_count"] = len(results)
        request.state.wide_event["total"] = total
    
    return PaginatedSightingResponse(
        results=results,
        total=total,
        limit=limit,
        offset=offset,
    )
```

#### 2. Input Validation

**Weather values** (from `app/schemas.py`):
- Valid: `sunny`, `rainy`, `snowy`, `sandstorm`, `foggy`, `clear`

**Time of day values**:
- Valid: `morning`, `day`, `night`

**Date range validation**:
- If both `date_from` and `date_to` are provided, validate that `date_from <= date_to`
- Return 400 Bad Request if invalid

**Optional: Add Pydantic validator for cleaner validation**:

```python
# In app/schemas.py
class SightingFilterParams(BaseModel):
    pokemon_id: int | None = None
    region: str | None = None
    weather: Literal["sunny", "rainy", "snowy", "sandstorm", "foggy", "clear"] | None = None
    time_of_day: Literal["morning", "day", "night"] | None = None
    ranger_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    is_confirmed: bool | None = None
    
    @model_validator(mode="after")
    def validate_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before or equal to date_to")
        return self
```

#### 3. Existing Implementation (No Changes Needed)

**Repository layer** (`app/repositories/sighting_repository.py:41-76`):
- Already implements `filter_sightings()` with all required filters
- Uses indexed columns for performance
- Returns tuple of (sightings, total_count)

**Service layer** (`app/services/sighting_service.py:93-125`):
- Already implements `filter_sightings()` 
- Enriches sightings with Pokemon and Ranger data
- Returns tuple of ([(sighting, pokemon, ranger)], total_count)

**Database indexes** (`app/models.py:64-72`):
- All filter fields are indexed
- Composite indexes for common patterns:
  - `idx_sightings_region_date` - region + date range queries
  - `idx_sightings_ranger_date` - ranger + date range queries

### Performance Considerations

**Database indexes** (already in place):
- `idx_sightings_region` - for region filtering
- `idx_sightings_ranger_id` - for ranger filtering
- `idx_sightings_date` - for date range filtering
- `idx_sightings_pokemon_id` - for species filtering
- `idx_sightings_region_date` - composite for region + date
- `idx_sightings_ranger_date` - composite for ranger + date
- `idx_sightings_is_confirmed` - for confirmation status

**Query optimization**:
- Repository uses `query.count()` before pagination to get total
- Results ordered by `date.desc()` (most recent first)
- Uses `offset()` and `limit()` for pagination
- All filter conditions use indexed columns

**Expected performance**:
- Single filter: < 50ms for 55K records (indexed)
- Multiple filters: < 100ms (composite indexes)
- Pagination: O(limit) for result retrieval

### Error Handling

**Invalid filter values**:
- Invalid weather/time_of_day: Return 422 Unprocessable Entity (FastAPI validation)
- Invalid date range (date_from > date_to): Return 400 Bad Request
- Non-existent pokemon_id/ranger_id: Return empty results (not an error)

**Edge cases**:
- No filters: Return all sightings (paginated)
- No results: Return empty array with total=0
- offset > total: Return empty array with correct total
- limit=0: Validation error (ge=1 constraint)

## Acceptance Criteria

### Functional Requirements

- [ ] `GET /v1/sightings` endpoint exists and returns paginated results
- [ ] Supports filtering by `pokemon_id` (integer)
- [ ] Supports filtering by `region` (string)
- [ ] Supports filtering by `weather` (enum: sunny, rainy, snowy, sandstorm, foggy, clear)
- [ ] Supports filtering by `time_of_day` (enum: morning, day, night)
- [ ] Supports filtering by `ranger_id` (UUID string)
- [ ] Supports filtering by `date_from` (datetime, inclusive)
- [ ] Supports filtering by `date_to` (datetime, inclusive)
- [ ] Supports filtering by `is_confirmed` (boolean)
- [ ] Supports combining multiple filters (AND logic)
- [ ] Returns total count of matching records
- [ ] Returns paginated results with limit/offset
- [ ] Default limit: 50, max: 200
- [ ] Default offset: 0
- [ ] Results ordered by date descending (most recent first)
- [ ] Response includes Pokemon name and Ranger name for each sighting

### Non-Functional Requirements

- [ ] Query performance < 100ms for typical filters on 55K records
- [ ] Uses existing database indexes (no new indexes needed)
- [ ] Follows existing codebase patterns and conventions
- [ ] Includes wide event logging for observability
- [ ] Returns proper HTTP status codes (200, 400, 422)
- [ ] API documentation via FastAPI auto-docs

### Quality Gates

- [ ] Unit tests for pagination (limit/offset)
- [ ] Unit tests for single filter (e.g., region)
- [ ] Unit tests for multiple filters combined
- [ ] Unit tests for response format (results + total)
- [ ] Unit tests for empty results
- [ ] Unit tests for invalid filter values
- [ ] All existing tests pass
- [ ] Code follows PEP 8 style guide
- [ ] Type hints on all function signatures

## Success Metrics

**Functional**:
- Field researchers can query sightings by any combination of filters
- Pagination works correctly for large result sets
- Response time < 100ms for typical queries

**Technical**:
- Code follows existing patterns (separation of concerns, error handling)
- Test coverage > 80% for new code
- No performance regressions in existing endpoints

## Dependencies & Prerequisites

**No external dependencies** - all infrastructure already in place:
- Repository method exists: `sighting_repository.filter_sightings()`
- Service method exists: `sighting_service.filter_sightings()`
- Database indexes exist for all filter fields
- Pydantic models exist: `SightingResponse`, `PaginatedSightingResponse`
- Test fixtures exist: `sample_sighting`, `sample_ranger`, `sample_pokemon`

**Internal dependencies**:
- `app/api/deps.py` - `get_db` dependency injection
- `app/services/sighting_service.py` - SightingService class
- `app/schemas.py` - Response models
- `app/models.py` - Sighting model

## Risk Analysis & Mitigation

### Risk 1: Performance degradation with complex filters
**Likelihood**: Low  
**Impact**: Medium  
**Mitigation**: 
- All filter fields are indexed
- Composite indexes exist for common patterns
- Query uses indexed columns only
- Test with realistic data volumes (55K records)

### Risk 2: Invalid filter combinations
**Likelihood**: Medium  
**Impact**: Low  
**Mitigation**:
- FastAPI validates enum values automatically
- Add custom validator for date range
- Return clear error messages
- Document valid values in API docs

### Risk 3: Breaking existing endpoints
**Likelihood**: Low  
**Impact**: High  
**Mitigation**:
- New endpoint, no changes to existing code
- Run full test suite before/after
- No changes to repository/service layers

## Implementation Phases

### Phase 1: Core Implementation (30 minutes)

**Tasks**:
- [ ] Add GET endpoint to `app/api/v1/sightings.py`
- [ ] Wire up query parameters to service method
- [ ] Construct response with Pokemon/Ranger names
- [ ] Add wide event logging
- [ ] Test manually with curl/httpie

**Success criteria**:
- Endpoint returns paginated results
- Filters work correctly
- Response format matches spec

### Phase 2: Input Validation (15 minutes)

**Tasks**:
- [ ] Add date range validation (date_from <= date_to)
- [ ] Consider adding SightingFilterParams schema
- [ ] Test invalid filter values
- [ ] Verify error messages are clear

**Success criteria**:
- Invalid inputs return 400/422
- Error messages are helpful
- Valid inputs work correctly

### Phase 3: Testing (45 minutes)

**Tasks**:
- [ ] Write `TestCandidateSightingFilters` test class
- [ ] Test pagination (limit/offset)
- [ ] Test single filter (region)
- [ ] Test multiple filters combined
- [ ] Test response includes total count
- [ ] Test empty results
- [ ] Test invalid filter values
- [ ] Run full test suite

**Success criteria**:
- All new tests pass
- All existing tests pass
- Test coverage > 80% for new code

### Phase 4: Documentation & Polish (15 minutes)

**Tasks**:
- [ ] Verify FastAPI auto-docs are correct
- [ ] Add docstring to endpoint
- [ ] Review code for style consistency
- [ ] Run linting/type checking

**Success criteria**:
- API docs are clear and accurate
- Code follows PEP 8
- Type hints are complete

**Total estimated time**: 1 hour 45 minutes

## Future Considerations

**Potential enhancements** (out of scope for this feature):
- Add sorting options (by date, region, pokemon_name)
- Add cursor-based pagination for better performance
- Add full-text search on notes field
- Add geospatial filtering (lat/long radius)
- Add aggregation endpoints (counts by region, weather, etc.)
- Cache frequently-accessed queries
- Add rate limiting specific to this endpoint

**Extensibility**:
- Filter schema can be extended with new fields
- Service layer can be enhanced with caching
- Repository layer supports additional filter types

## Documentation Plan

**API Documentation**:
- FastAPI auto-generates OpenAPI docs at `/docs`
- Query parameters documented with `description` parameter
- Response schema documented via Pydantic models

**Code Documentation**:
- Docstring on endpoint function
- Inline comments for complex logic
- Type hints on all signatures

**User Documentation** (if needed):
- Update README with endpoint usage examples
- Document valid filter values
- Provide example queries

## References & Research

### Internal References

**Existing implementation** (no changes needed):
- Repository: `app/repositories/sighting_repository.py:41-76` - `filter_sightings()` method
- Service: `app/services/sighting_service.py:93-125` - `filter_sightings()` method
- Models: `app/models.py:62-95` - Sighting model with indexes

**Patterns to follow**:
- Pagination: `app/api/v1/pokemon.py:16-35` - Pokemon listing endpoint
- Response construction: `app/api/v1/rangers.py:60-104` - Ranger sightings endpoint
- Error handling: `app/api/v1/sightings.py:88-108` - Existing sighting endpoints
- Wide event logging: `app/middleware.py` - Logging pattern

**Test patterns**:
- Test fixtures: `tests/conftest.py:1-225` - Available fixtures
- Test structure: `tests/test_public.py:275-286` - Required test class

### External References

- FastAPI Query parameters: https://fastapi.tiangolo.com/tutorial/query-params/
- SQLAlchemy filtering: https://docs.sqlalchemy.org/en/20/core/selectable.html#where-clauses
- Pydantic validators: https://docs.pydantic.dev/latest/concepts/validators/

### Related Work

- Feature 2: Research Campaigns - will use similar filtering patterns
- Feature 4: Regional Research Summary - uses similar aggregation queries
- Feature 6: Ranger Leaderboard - uses similar filtering/pagination

## MVP

### app/api/v1/sightings.py

```python
@router.get("/", response_model=PaginatedSightingResponse)
def list_sightings(
    request: Request,
    db: Session = Depends(get_db),
    pokemon_id: int | None = Query(None),
    region: str | None = Query(None),
    weather: str | None = Query(None),
    time_of_day: str | None = Query(None),
    ranger_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    is_confirmed: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    service = SightingService(db)
    
    sightings_data, total = service.filter_sightings(
        pokemon_id=pokemon_id,
        region=region,
        weather=weather,
        time_of_day=time_of_day,
        ranger_id=ranger_id,
        date_from=date_from,
        date_to=date_to,
        is_confirmed=is_confirmed,
        skip=offset,
        limit=limit,
    )
    
    results = []
    for sighting, pokemon, ranger in sightings_data:
        results.append(
            SightingResponse(
                id=sighting.id,
                pokemon_id=sighting.pokemon_id,
                ranger_id=sighting.ranger_id,
                region=sighting.region,
                route=sighting.route,
                date=sighting.date,
                weather=sighting.weather,
                time_of_day=sighting.time_of_day,
                height=sighting.height,
                weight=sighting.weight,
                is_shiny=sighting.is_shiny,
                notes=sighting.notes,
                is_confirmed=sighting.is_confirmed,
                pokemon_name=pokemon.name if pokemon else None,
                ranger_name=ranger.name if ranger else None,
            )
        )
    
    if hasattr(request.state, "wide_event"):
        request.state.wide_event["filter_params"] = {
            "pokemon_id": pokemon_id,
            "region": region,
            "weather": weather,
            "time_of_day": time_of_day,
            "ranger_id": ranger_id,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "is_confirmed": is_confirmed,
        }
        request.state.wide_event["results_count"] = len(results)
        request.state.wide_event["total"] = total
    
    return PaginatedSightingResponse(
        results=results,
        total=total,
        limit=limit,
        offset=offset,
    )
```

### tests/test_public.py

```python
class TestCandidateSightingFilters:
    """Tests for GET /sightings endpoint (Feature 1)."""
    
    def test_pagination(self, client, sample_sighting):
        """Test that pagination works with limit and offset."""
        response = client.get("/v1/sightings?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["results"]) <= 10
    
    def test_filter_by_region(self, client, sample_sighting):
        """Test filtering by region."""
        response = client.get("/v1/sightings?region=Kanto")
        assert response.status_code == 200
        data = response.json()
        assert all(s["region"] == "Kanto" for s in data["results"])
    
    def test_filter_by_weather(self, client, sample_sighting):
        """Test filtering by weather condition."""
        response = client.get("/v1/sightings?weather=sunny")
        assert response.status_code == 200
        data = response.json()
        assert all(s["weather"] == "sunny" for s in data["results"])
    
    def test_multiple_filters(self, client, sample_sighting, second_ranger, sample_pokemon):
        """Test combining multiple filters narrows results correctly."""
        from app.services.sighting_service import SightingService
        from app.api.deps import get_db
        
        db = next(get_db())
        service = SightingService(db)
        
        from datetime import datetime, timedelta
        from app.schemas import SightingCreate
        
        sighting2 = SightingCreate(
            pokemon_id=sample_pokemon[1].id,
            region="Johto",
            route="Route 29",
            date=datetime.now(),
            weather="rainy",
            time_of_day="night",
            height=0.6,
            weight=8.5,
        )
        service.create_sighting(str(second_ranger.id), sighting2)
        
        response = client.get(f"/v1/sightings?region=Kanto&weather=sunny")
        assert response.status_code == 200
        data = response.json()
        assert all(s["region"] == "Kanto" and s["weather"] == "sunny" for s in data["results"])
    
    def test_response_includes_total_count(self, client, sample_sighting):
        """Test that response includes total count of matching records."""
        response = client.get("/v1/sightings")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert isinstance(data["total"], int)
        assert data["total"] >= len(data["results"])
    
    def test_empty_results(self, client):
        """Test that filtering with no matches returns empty results."""
        response = client.get("/v1/sightings?region=NonexistentRegion")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0
```
