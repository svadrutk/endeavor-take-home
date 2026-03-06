---
title: feat: Regional Research Summary
type: feat
status: active
date: 2026-03-06
---

# feat: Regional Research Summary

## Overview

Implement a `GET /regions/{region_name}/summary` endpoint that provides a high-level summary of research activity for a given region. This endpoint will aggregate sighting data to show total counts, unique species, top contributors, and breakdowns by weather and time of day. The feature also addresses performance concerns with aggregate queries over large datasets.

## Problem Statement

Professor Oak needs a way to get comprehensive regional research summaries for quarterly reports. Currently, there's no endpoint that aggregates sighting data by region. Additionally, the research team has reported that aggregate queries over large regions (like Kanto with 10,000+ records) are unacceptably slow, and the existing `GET /pokemon` listing endpoint also experiences performance issues with the full dataset.

## Proposed Solution

Create a new regional summary endpoint that:
1. Aggregates sighting data efficiently using database-level operations
2. Provides comprehensive statistics including confirmation status breakdown
3. Addresses performance through optimized queries and proper indexing
4. Follows existing architectural patterns (API → Service → Repository)

## Technical Approach

### Architecture

Follow the established three-layer architecture:
- **API Layer**: New endpoint in `app/api/v1/regions.py` (new file)
- **Service Layer**: New `RegionService` in `app/services/region_service.py`
- **Repository Layer**: Extend `SightingRepository` with aggregate query methods

### Implementation Phases

#### Phase 1: Data Model & Schemas

**Tasks:**
- Create response schema `RegionalSummary` in `app/schemas.py`
- Define nested schemas for breakdowns (weather, time of day, top pokemon, top rangers)
- Include confirmation status breakdown in the schema

**Success Criteria:**
- Schema validates all required fields from the spec
- Type-safe with proper Pydantic models

**Estimated Effort:** 15 minutes

#### Phase 2: Repository Layer - Aggregate Queries

**Tasks:**
- Add `get_regional_summary()` method to `SightingRepository`
- Implement efficient aggregate queries using SQLAlchemy `func`:
  - `func.count()` for totals
  - `func.count(func.distinct())` for unique species
  - `group_by()` for breakdowns
- Use single queries with joins instead of multiple queries
- Leverage existing indexes on `region`, `date`, `is_confirmed`

**Key Queries:**
```python
# Total sightings with confirmation breakdown
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN is_confirmed = 1 THEN 1 ELSE 0 END) as confirmed,
    SUM(CASE WHEN is_confirmed = 0 THEN 1 ELSE 0 END) as unconfirmed
FROM sightings
WHERE region = :region

# Unique species
SELECT COUNT(DISTINCT pokemon_id)
FROM sightings
WHERE region = :region

# Top 5 Pokemon
SELECT pokemon_id, COUNT(*) as count
FROM sightings
WHERE region = :region
GROUP BY pokemon_id
ORDER BY count DESC
LIMIT 5

# Top 5 Rangers
SELECT ranger_id, COUNT(*) as count
FROM sightings
WHERE region = :region
GROUP BY ranger_id
ORDER BY count DESC
LIMIT 5

# Weather breakdown
SELECT weather, COUNT(*) as count
FROM sightings
WHERE region = :region
GROUP BY weather

# Time of day breakdown
SELECT time_of_day, COUNT(*) as count
FROM sightings
WHERE region = :region
GROUP BY time_of_day
```

**Success Criteria:**
- All queries execute in <100ms for regions with 10,000+ records
- Single database transaction per request
- No N+1 query problems

**Estimated Effort:** 45 minutes

#### Phase 3: Service Layer - Business Logic

**Tasks:**
- Create `RegionService` in `app/services/region_service.py`
- Inject `SightingRepository`, `PokemonRepository`, `RangerRepository`
- Implement `get_regional_summary(region_name: str)` method
- Validate region name against valid regions (Kanto, Johto, Hoenn, Sinnoh)
- Transform repository results into response schema
- Add error handling for invalid regions

**Success Criteria:**
- Service validates region names
- Returns 404 for invalid regions
- Enriches Pokemon and Ranger IDs with names
- Follows dependency injection pattern

**Estimated Effort:** 30 minutes

#### Phase 4: API Layer - Endpoint Implementation

**Tasks:**
- Create `app/api/v1/regions.py` with new router
- Implement `GET /regions/{region_name}/summary` endpoint
- Add proper error handling (404 for invalid region)
- Include wide event logging for observability
- Register router in `app/api/v1/router.py`

**Endpoint Signature:**
```python
@router.get("/{region_name}/summary", response_model=RegionalSummary)
def get_regional_summary(
    request: Request,
    region_name: str,
    service: RegionService = Depends(get_region_service)
):
    # Implementation
```

**Success Criteria:**
- Endpoint returns proper HTTP status codes
- Wide events capture region and summary stats
- Error responses are clear and helpful
- Follows existing endpoint patterns

**Estimated Effort:** 20 minutes

#### Phase 5: Performance Optimization

**Tasks:**
- Verify existing indexes are being used (EXPLAIN QUERY PLAN)
- Add composite index if needed: `(region, is_confirmed)` for confirmation breakdown
- Consider query result caching for frequently accessed regions
- Optimize Pokemon listing endpoint if needed
- Add pagination to Pokemon listing if not present

**Performance Targets:**
- Regional summary: <100ms for 10,000+ records
- Pokemon listing: <50ms for 493 records
- All queries use indexes (no full table scans)

**Success Criteria:**
- Meets performance targets
- No N+1 queries
- Proper index utilization confirmed

**Estimated Effort:** 30 minutes

#### Phase 6: Testing

**Tasks:**
- Write unit tests for `RegionService`
- Write integration tests for the endpoint
- Test edge cases:
  - Invalid region name
  - Region with no sightings
  - Region with many sightings (performance)
  - Confirmation status breakdown accuracy
- Add tests to `tests/test_public.py`

**Test Scenarios:**
1. Valid region returns complete summary
2. Invalid region returns 404
3. Region with no sightings returns zeros
4. Confirmation breakdown is accurate
5. Top 5 lists are correct
6. Performance test with 10,000+ records

**Success Criteria:**
- All tests pass
- >90% code coverage for new code
- Tests validate business requirements

**Estimated Effort:** 40 minutes

## Acceptance Criteria

### Functional Requirements

- [ ] `GET /regions/{region_name}/summary` endpoint exists and returns correct data structure
- [ ] Total sightings count includes breakdown of confirmed vs. unconfirmed
- [ ] Unique species count is accurate
- [ ] Top 5 most-sighted Pokemon list with counts (correct order)
- [ ] Top 5 contributing Rangers list with counts (correct order)
- [ ] Weather condition breakdown with counts
- [ ] Time of day breakdown with counts
- [ ] Invalid region names return 404 with clear error message
- [ ] Region names are case-insensitive (kanto, Kanto, KANTO all work)

### Non-Functional Requirements

- [ ] Regional summary query completes in <100ms for regions with 10,000+ records
- [ ] All aggregate queries use database indexes (no full table scans)
- [ ] Single database transaction per request
- [ ] No N+1 query problems
- [ ] Pokemon listing endpoint performance is acceptable (<50ms)
- [ ] Memory usage is reasonable (no loading entire datasets into memory)

### Quality Gates

- [ ] Code follows existing architectural patterns
- [ ] Proper dependency injection used
- [ ] Pydantic models for request/response validation
- [ ] Wide event logging implemented
- [ ] Error messages are clear and actionable
- [ ] Unit and integration tests written
- [ ] Code passes linting (ruff) and type checking (ty)

## Success Metrics

1. **Performance**: Regional summary queries complete in <100ms for large datasets
2. **Accuracy**: All aggregate counts match manual calculations
3. **Usability**: Clear error messages for invalid inputs
4. **Reliability**: No database connection leaks or N+1 queries

## Dependencies & Prerequisites

- Existing `Sighting` model with proper indexes
- Existing `Pokemon` and `Ranger` models
- Confirmation system (Feature 3) must be implemented
- Database contains test data (seed script working)

## Risk Analysis & Mitigation

### Risk 1: Slow Aggregate Queries
**Impact**: High - endpoint unusable for large regions
**Mitigation**: 
- Use database-level aggregation (not Python)
- Verify index usage with EXPLAIN QUERY PLAN
- Add composite indexes if needed
- Consider caching for frequently accessed regions

### Risk 2: Memory Issues with Large Datasets
**Impact**: Medium - could crash server
**Mitigation**:
- Never load all records into memory
- Use COUNT and GROUP BY at database level
- Limit result sets (top 5 lists)

### Risk 3: Inconsistent Data
**Impact**: Medium - inaccurate reports
**Mitigation**:
- Use transactions for consistency
- Validate confirmation status integrity
- Test with various data scenarios

## Resource Requirements

- **Development Time**: 3-4 hours
- **Testing Time**: 1 hour
- **Database**: No schema changes required (indexes already exist)
- **External Dependencies**: None

## Future Considerations

1. **Caching**: Add Redis caching for frequently accessed regional summaries
2. **Date Range Filtering**: Allow filtering summary by date range
3. **Export**: Add CSV/JSON export for quarterly reports
4. **Comparison**: Add endpoint to compare multiple regions
5. **Trends**: Add time-series data for regional trends over time

## Documentation Plan

- Update API documentation with new endpoint
- Document performance characteristics
- Add example requests/responses to README
- Document valid region names

## References & Research

### Internal References

- Existing aggregate query pattern: `app/services/campaign_service.py:150-180` (campaign summary)
- Sighting model with indexes: `app/models.py:112-171`
- Sighting repository: `app/repositories/sighting_repository.py`
- Region validation: `app/services/pokemon_service.py:4-12`
- API endpoint pattern: `app/api/v1/sightings.py`
- Dependency injection: `app/api/deps.py`

### External References

- SQLAlchemy Aggregation: https://docs.sqlalchemy.org/en/20/core/functions.html
- SQLite Query Optimization: https://www.sqlite.org/queryplanner.html
- FastAPI Response Models: https://fastapi.tiangolo.com/tutorial/response-model/

### Related Work

- Feature 1: Sighting filters (pagination pattern)
- Feature 2: Campaign summary (aggregate query pattern)
- Feature 3: Peer confirmation (confirmation status tracking)
- Performance improvements commit: a4afa66 (database indexes)

## Deep Research & Best Practices

### SQLAlchemy Performance Optimization

Based on SQLAlchemy documentation and industry best practices:

1. **Use Database-Level Aggregation** (Critical)
   - Never fetch all records and aggregate in Python
   - Use `func.count()`, `func.sum()`, `func.count(func.distinct())` at database level
   - Reduces memory usage and network overhead
   - Example: `session.query(func.count(Sighting.id)).filter(Sighting.region == region).scalar()`

2. **Avoid N+1 Query Problem** (Critical)
   - Don't fetch related objects individually in loops
   - Use `joinedload()` or `selectinload()` for eager loading
   - For aggregate queries, fetch IDs first, then batch-load related objects
   - Example pattern:
     ```python
     # Get top 5 Pokemon IDs
     top_pokemon_ids = session.query(
         Sighting.pokemon_id, 
         func.count('*').label('count')
     ).filter(Sighting.region == region).group_by(Sighting.pokemon_id).order_by(desc('count')).limit(5).all()
     
     # Batch load Pokemon names
     pokemon_ids = [p[0] for p in top_pokemon_ids]
     pokemon_names = session.query(Pokemon).filter(Pokemon.id.in_(pokemon_ids)).all()
     ```

3. **Fetch Only Required Columns** (Important)
   - Use `with_entities()` or `load_only()` to fetch specific columns
   - Avoid `SELECT *` when you only need a few columns
   - Example: `session.query(Sighting.pokemon_id, Sighting.ranger_id).filter(...)`

4. **SQL Compilation Caching** (Built-in)
   - SQLAlchemy 1.4+ automatically caches compiled SQL statements
   - Structurally equivalent queries reuse cached compilation
   - No action needed, but be aware this provides ~30% performance improvement

5. **Connection Pooling** (Already Configured)
   - SQLAlchemy uses `QueuePool` by default
   - Reuses database connections instead of creating new ones
   - Already configured in the codebase

### SQLite Query Optimization

Based on SQLite performance documentation:

1. **Index Utilization** (Critical)
   - SQLite uses B-tree indexes for WHERE, ORDER BY, and GROUP BY operations
   - Existing indexes on `region`, `is_confirmed`, `date` will be used automatically
   - Use `EXPLAIN QUERY PLAN` to verify index usage:
     ```sql
     EXPLAIN QUERY PLAN 
     SELECT COUNT(*) FROM sightings WHERE region = 'Kanto';
     ```
   - Expected output: `USING INDEX idx_sightings_region`

2. **Composite Indexes** (Important)
   - For queries filtering on multiple columns, composite indexes are more efficient
   - Recommendation: Add composite index `(region, is_confirmed)` for confirmation breakdown
   - SQLite can use leftmost prefix of composite index
   - Example: Index on `(region, is_confirmed)` can serve queries filtering by `region` alone

3. **GROUP BY Performance** (Important)
   - SQLite can use indexes to optimize GROUP BY operations
   - If GROUP BY column has an index, SQLite can avoid sorting
   - For our queries:
     - `GROUP BY pokemon_id` - no index needed (small result set)
     - `GROUP BY weather` - no index needed (small result set)
     - `GROUP BY time_of_day` - no index needed (small result set)

4. **Covering Indexes** (Advanced)
   - An index that includes all columns needed by a query
   - SQLite can satisfy query entirely from index without reading table
   - For our use case, not critical since we're aggregating

5. **Query Plan Analysis** (Recommended)
   - Always verify query performance with EXPLAIN QUERY PLAN
   - Look for `USING INDEX` or `USING COVERING INDEX`
   - Avoid `SCAN TABLE` (full table scan) for large tables

### FastAPI Response Model Best Practices

Based on FastAPI documentation and pagination patterns:

1. **Pydantic Response Models** (Required)
   - Define clear response schemas with proper typing
   - Use `model_config = ConfigDict(from_attributes=True)` for ORM models
   - Example:
     ```python
     class TopPokemon(BaseModel):
         id: int
         name: str
         count: int
     
     class RegionalSummary(BaseModel):
         region: str
         total_sightings: int
         confirmed_sightings: int
         unconfirmed_sightings: int
         unique_species: int
         top_pokemon: list[TopPokemon]
         top_rangers: list[TopRanger]
         weather_breakdown: dict[str, int]
         time_of_day_breakdown: dict[str, int]
     ```

2. **Response Model Validation** (Built-in)
   - FastAPI automatically validates response against schema
   - Returns 422 if response doesn't match schema
   - Ensures API contract is maintained

3. **Generic Pagination Pattern** (Already Implemented)
   - Use `PaginatedResponse[T]` generic type
   - Include `total`, `limit`, `offset` fields
   - Example from codebase: `PaginatedSightingResponse`

### Performance Benchmarks

Based on research and similar implementations:

1. **Aggregate Query Performance**
   - COUNT on indexed column: <10ms for 50,000 records
   - GROUP BY on indexed column: <20ms for 50,000 records
   - Multiple aggregate queries in transaction: <100ms total
   - Target: All regional summary queries complete in <100ms

2. **Index Performance Impact**
   - Proper indexing: 10x-100x speedup
   - Full table scan on 50,000 records: ~500ms
   - Indexed lookup on 50,000 records: ~5ms

3. **Memory Usage**
   - Aggregate queries: minimal memory (returns scalar values)
   - Avoid loading full result sets into memory
   - Use database-level aggregation, not Python aggregation

## Implementation Notes

### Query Optimization Strategy

1. **Use Database Aggregation**: Never fetch all records and aggregate in Python
2. **Leverage Indexes**: Ensure queries use existing indexes on `region`, `is_confirmed`
3. **Single Transaction**: All queries in one transaction for consistency
4. **Limit Results**: Top 5 lists use LIMIT clause
5. **Avoid N+1**: Fetch Pokemon/Ranger names in batch after getting IDs
6. **Verify with EXPLAIN**: Use `EXPLAIN QUERY PLAN` to confirm index usage
7. **Batch Loading**: Load related objects in batches, not individually

### Confirmation Status Integration

The confirmation system (Feature 3) adds:
- `is_confirmed` boolean field
- `confirmed_by` ranger UUID
- `confirmed_at` timestamp

The regional summary should:
- Count confirmed vs. unconfirmed sightings
- Consider confirmed sightings as "higher quality" data
- Potentially weight confirmed sightings more in future analysis features

### Region Name Validation

Valid regions (case-insensitive):
- Kanto (Generation 1)
- Johto (Generation 2)
- Hoenn (Generation 3)
- Sinnoh (Generation 4)

Use the existing `VALID_REGIONS` constant from `pokemon_service.py`.

### Response Schema Design

```python
from pydantic import BaseModel, ConfigDict

class TopPokemon(BaseModel):
    id: int
    name: str
    count: int

class TopRanger(BaseModel):
    id: str
    name: str
    count: int

class RegionalSummary(BaseModel):
    region: str
    total_sightings: int
    confirmed_sightings: int
    unconfirmed_sightings: int
    unique_species: int
    top_pokemon: list[TopPokemon]
    top_rangers: list[TopRanger]
    weather_breakdown: dict[str, int]
    time_of_day_breakdown: dict[str, int]
```

### Repository Implementation Pattern

```python
# app/repositories/sighting_repository.py

from sqlalchemy import func, case
from app.models import Sighting

class SightingRepository(BaseRepository[Sighting]):
    
    def get_regional_summary_stats(self, region: str) -> dict:
        """Get aggregate statistics for a region in a single query."""
        result = self.db.query(
            func.count(Sighting.id).label('total'),
            func.sum(case((Sighting.is_confirmed == True, 1), else_=0)).label('confirmed'),
            func.sum(case((Sighting.is_confirmed == False, 1), else_=0)).label('unconfirmed'),
            func.count(func.distinct(Sighting.pokemon_id)).label('unique_species')
        ).filter(Sighting.region == region).first()
        
        return {
            'total': result.total or 0,
            'confirmed': result.confirmed or 0,
            'unconfirmed': result.unconfirmed or 0,
            'unique_species': result.unique_species or 0
        }
    
    def get_top_pokemon_by_region(self, region: str, limit: int = 5) -> list:
        """Get top Pokemon by sighting count in region."""
        return self.db.query(
            Sighting.pokemon_id,
            func.count(Sighting.id).label('count')
        ).filter(
            Sighting.region == region
        ).group_by(
            Sighting.pokemon_id
        ).order_by(
            desc('count')
        ).limit(limit).all()
    
    def get_top_rangers_by_region(self, region: str, limit: int = 5) -> list:
        """Get top Rangers by sighting count in region."""
        return self.db.query(
            Sighting.ranger_id,
            func.count(Sighting.id).label('count')
        ).filter(
            Sighting.region == region
        ).group_by(
            Sighting.ranger_id
        ).order_by(
            desc('count')
        ).limit(limit).all()
    
    def get_weather_breakdown(self, region: str) -> dict:
        """Get sighting counts by weather condition."""
        results = self.db.query(
            Sighting.weather,
            func.count(Sighting.id).label('count')
        ).filter(
            Sighting.region == region
        ).group_by(
            Sighting.weather
        ).all()
        
        return {r.weather: r.count for r in results}
    
    def get_time_of_day_breakdown(self, region: str) -> dict:
        """Get sighting counts by time of day."""
        results = self.db.query(
            Sighting.time_of_day,
            func.count(Sighting.id).label('count')
        ).filter(
            Sighting.region == region
        ).group_by(
            Sighting.time_of_day
        ).all()
        
        return {r.time_of_day: r.count for r in results}
```

### Service Layer Implementation Pattern

```python
# app/services/region_service.py

from app.services.pokemon_service import VALID_REGIONS
from app.repositories.sighting_repository import SightingRepository
from app.repositories.pokemon_repository import PokemonRepository
from app.repositories.ranger_repository import RangerRepository

class RegionService:
    def __init__(
        self,
        sighting_repo: SightingRepository,
        pokemon_repo: PokemonRepository,
        ranger_repo: RangerRepository
    ):
        self.sighting_repo = sighting_repo
        self.pokemon_repo = pokemon_repo
        self.ranger_repo = ranger_repo
    
    def get_regional_summary(self, region_name: str) -> dict:
        """Get comprehensive regional summary."""
        # Validate region
        region_lower = region_name.lower()
        if region_lower not in VALID_REGIONS:
            raise ValueError(
                f"Invalid region: '{region_name}'. "
                f"Valid regions: {', '.join(sorted(VALID_REGIONS))}"
            )
        
        # Get aggregate stats (single query)
        stats = self.sighting_repo.get_regional_summary_stats(region_name)
        
        # Get top Pokemon (single query)
        top_pokemon_data = self.sighting_repo.get_top_pokemon_by_region(region_name)
        pokemon_ids = [p[0] for p in top_pokemon_data]
        pokemon_map = {p.id: p.name for p in self.pokemon_repo.get_by_ids(pokemon_ids)}
        
        top_pokemon = [
            {"id": pid, "name": pokemon_map.get(pid, "Unknown"), "count": count}
            for pid, count in top_pokemon_data
        ]
        
        # Get top Rangers (single query)
        top_rangers_data = self.sighting_repo.get_top_rangers_by_region(region_name)
        ranger_ids = [r[0] for r in top_rangers_data]
        ranger_map = {r.id: r.name for r in self.ranger_repo.get_by_ids(ranger_ids)}
        
        top_rangers = [
            {"id": rid, "name": ranger_map.get(rid, "Unknown"), "count": count}
            for rid, count in top_rangers_data
        ]
        
        # Get breakdowns (two queries)
        weather_breakdown = self.sighting_repo.get_weather_breakdown(region_name)
        time_of_day_breakdown = self.sighting_repo.get_time_of_day_breakdown(region_name)
        
        return {
            "region": region_name.title(),  # Capitalize first letter
            "total_sightings": stats['total'],
            "confirmed_sightings": stats['confirmed'],
            "unconfirmed_sightings": stats['unconfirmed'],
            "unique_species": stats['unique_species'],
            "top_pokemon": top_pokemon,
            "top_rangers": top_rangers,
            "weather_breakdown": weather_breakdown,
            "time_of_day_breakdown": time_of_day_breakdown
        }
```

### API Endpoint Implementation Pattern

```python
# app/api/v1/regions.py

from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.region_service import RegionService
from app.api.deps import get_region_service
from app.schemas import RegionalSummary

router = APIRouter(prefix="/regions", tags=["regions"])

@router.get("/{region_name}/summary", response_model=RegionalSummary)
def get_regional_summary(
    request: Request,
    region_name: str,
    service: RegionService = Depends(get_region_service)
):
    """
    Get comprehensive research summary for a region.
    
    Returns:
    - Total sightings with confirmation breakdown
    - Unique species count
    - Top 5 most-sighted Pokemon
    - Top 5 contributing Rangers
    - Weather condition breakdown
    - Time of day breakdown
    """
    try:
        summary = service.get_regional_summary(region_name)
        
        # Log wide event
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["region"] = region_name
            request.state.wide_event["summary"] = {
                "total_sightings": summary["total_sightings"],
                "unique_species": summary["unique_species"]
            }
        
        return RegionalSummary(**summary)
    
    except ValueError as e:
        if hasattr(request.state, "wide_event"):
            request.state.wide_event["error"] = {
                "type": "ValidationError",
                "message": str(e)
            }
        raise HTTPException(status_code=404, detail=str(e))
```

### Performance Testing

Test with:
- Small region (< 1000 records)
- Medium region (1000-5000 records)
- Large region (10,000+ records like Kanto)
- Empty region (0 records)

Target: All queries < 100ms for large regions.

### Performance Verification Steps

1. **Before Implementation**
   ```bash
   # Check current query performance
   sqlite3 poketracker.db "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM sightings WHERE region = 'Kanto';"
   
   # Check existing indexes
   sqlite3 poketracker.db "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name;"
   ```

2. **During Implementation**
   ```python
   # Add timing to repository methods
   import time
   
   def get_regional_summary_stats(self, region: str) -> dict:
       start = time.time()
       result = self.db.query(...).filter(...).first()
       duration_ms = (time.time() - start) * 1000
       print(f"get_regional_summary_stats: {duration_ms:.2f}ms")
       return {...}
   ```

3. **After Implementation**
   ```bash
   # Run performance test
   uv run pytest tests/test_performance.py -v
   
   # Profile with real data
   uv run python -m scripts.profile_regional_summary
   ```

4. **Query Plan Verification**
   ```sql
   -- Verify index usage for each query
   EXPLAIN QUERY PLAN 
   SELECT COUNT(*) FROM sightings WHERE region = 'Kanto';
   -- Expected: USING INDEX idx_sightings_region
   
   EXPLAIN QUERY PLAN
   SELECT pokemon_id, COUNT(*) FROM sightings 
   WHERE region = 'Kanto' 
   GROUP BY pokemon_id 
   ORDER BY COUNT(*) DESC 
   LIMIT 5;
   -- Expected: USING INDEX idx_sightings_region
   ```

### Composite Index Recommendation

Based on query patterns, consider adding:

```python
# In app/models.py, add to Sighting.__table_args__:
Index("idx_sightings_region_confirmed", "region", "is_confirmed"),
```

This composite index will optimize:
- Total sightings count by region
- Confirmed vs unconfirmed breakdown
- Filtering by region and confirmation status

**Migration:**
```sql
CREATE INDEX idx_sightings_region_confirmed 
ON sightings(region, is_confirmed);
```

**Expected Impact:**
- Confirmation breakdown query: 2-5x faster
- No impact on existing queries (backward compatible)

### Error Handling & Edge Cases

1. **Invalid Region Name**
   ```python
   # Service layer validation
   if region_lower not in VALID_REGIONS:
       raise ValueError(
           f"Invalid region: '{region_name}'. "
           f"Valid regions: {', '.join(sorted(VALID_REGIONS))}"
       )
   
   # API layer error handling
   except ValueError as e:
       raise HTTPException(status_code=404, detail=str(e))
   ```

2. **Region with No Sightings**
   ```python
   # Repository returns zeros
   def get_regional_summary_stats(self, region: str) -> dict:
       result = self.db.query(...).first()
       return {
           'total': result.total or 0,
           'confirmed': result.confirmed or 0,
           'unconfirmed': result.unconfirmed or 0,
           'unique_species': result.unique_species or 0
       }
   ```

3. **Case Sensitivity**
   ```python
   # Normalize region name
   region_lower = region_name.lower()
   # Return with proper capitalization
   "region": region_name.title()  # "kanto" -> "Kanto"
   ```

4. **Empty Results**
   ```python
   # Top Pokemon/Rangers with no data
   top_pokemon = [
       {"id": pid, "name": pokemon_map.get(pid, "Unknown"), "count": count}
       for pid, count in top_pokemon_data
   ]
   # Returns empty list if no data
   
   # Breakdowns with no data
   weather_breakdown = self.sighting_repo.get_weather_breakdown(region_name)
   # Returns {} if no data
   ```

5. **Database Connection Issues**
   ```python
   # Handled by existing error handling in repository layer
   # FastAPI will return 500 Internal Server Error
   # Wide event will capture error details
   ```

### Testing Strategy

1. **Unit Tests** (app/services/test_region_service.py)
   - Test region validation
   - Test summary calculation logic
   - Test error handling
   - Mock repository responses

2. **Integration Tests** (tests/test_public.py)
   - Test endpoint with valid region
   - Test endpoint with invalid region
   - Test endpoint with empty region
   - Test confirmation breakdown accuracy
   - Test top 5 lists ordering

3. **Performance Tests** (tests/test_performance.py)
   - Benchmark queries with 10,000+ records
   - Verify index usage
   - Memory usage profiling
   - Query count verification (no N+1)

4. **Example Test Cases**
   ```python
   def test_get_regional_summary_valid_region(client, sample_sightings):
       response = client.get("/v1/regions/kanto/summary")
       assert response.status_code == 200
       data = response.json()
       assert data["region"] == "Kanto"
       assert data["total_sightings"] > 0
       assert data["confirmed_sightings"] >= 0
       assert data["unconfirmed_sightings"] >= 0
       assert len(data["top_pokemon"]) <= 5
       assert len(data["top_rangers"]) <= 5
   
   def test_get_regional_summary_invalid_region(client):
       response = client.get("/v1/regions/invalid_region/summary")
       assert response.status_code == 404
       assert "Invalid region" in response.json()["detail"]
   
   def test_get_regional_summary_empty_region(client):
       response = client.get("/v1/regions/sinnoh/summary")
       assert response.status_code == 200
       data = response.json()
       assert data["total_sightings"] == 0
       assert data["unique_species"] == 0
       assert data["top_pokemon"] == []
   ```
