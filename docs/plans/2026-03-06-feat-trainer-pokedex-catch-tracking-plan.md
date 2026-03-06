---
title: feat: Trainer Pokédex (Catch Tracking)
type: feat
status: completed
date: 2026-03-06
---

# feat: Trainer Pokédex (Catch Tracking)

## Enhancement Summary

**Deepened on:** 2026-03-06
**Sections enhanced:** 8
**Research agents used:** best-practices-researcher, framework-docs-researcher, performance-oracle, security-sentinel, code-simplicity-reviewer, architecture-strategist, pattern-recognition-specialist, data-integrity-guardian

### Key Improvements
1. **Security hardening** - Custom exception hierarchy, proper authentication patterns, race condition prevention
2. **Performance optimization** - Eager loading, batch queries, proper indexing strategy
3. **Data integrity** - Foreign key constraints, CHECK constraints, transaction boundaries
4. **Architectural patterns** - Repository pattern improvements, service layer separation, dependency injection
5. **Code quality** - Error handling consistency, validation patterns, test data builders

### New Considerations Discovered
- **N+1 query problem** in catch log retrieval - requires eager loading
- **Race condition vulnerability** in duplicate catch prevention - needs row-level locking
- **Foreign key cascade strategy** - pokemon_id should use RESTRICT, not CASCADE
- **Missing database constraints** - CHECK constraints for timestamp and pokemon_id validation
- **Authentication bypass risk** - X-User-ID header spoofing requires validation

---

## Overview

Implement a personal catch-tracking system for Pokémon Trainers. Trainers can mark Pokémon species as caught, view their completion progress, browse their personal catch log, and see which Pokémon they've caught when viewing Pokédex entries.

## Problem Statement

Trainers have been requesting a way to track their collection through the Pokédex. Currently, the system only allows viewing Pokémon species information, but Trainers want to:
- Mark Pokémon as caught (recording the date)
- See their completion progress (percentage out of 493 total species)
- Browse their personal catch log
- View which Pokémon they've caught when browsing the Pokédex
- Compare their collection with other Trainers

The system needs to enforce that only Trainers can use catch-tracking features (not Rangers), and that Trainers can only modify their own catch logs.

## Proposed Solution

Create a many-to-many relationship between Trainers and Pokémon species to track catches. Extend the existing Pokédex endpoint to conditionally include catch status when the X-User-ID header is provided. Implement CRUD endpoints for managing catches with proper authorization.

## Technical Approach

### Architecture

**Data Model:**
- TrainerCatch junction table linking Trainer to Pokémon with caught_at timestamp
- Composite primary key (trainer_id, pokemon_id) to prevent duplicates
- Database indexes for efficient querying by trainer and by pokemon

**Integration Points:**
- Extend GET /pokedex/{pokemon_id} to include is_caught field when X-User-ID is a Trainer
- Create new endpoints under /trainers/{trainer_id}/pokedex for catch management
- Add catch summary endpoint with completion percentage and breakdowns

**Authorization:**
- Validate X-User-ID matches trainer_id in path for modifications (POST/DELETE)
- Allow public read access to any Trainer's catch log and summary
- Reject Ranger access to catch-tracking features

### Research Insights: Architecture

**Best Practices:**
- Use **layered architecture** (API → Service → Repository) consistently
- Implement **dependency injection** via FastAPI's Depends system
- Create **custom exception hierarchy** for better error handling
- Use **eager loading** to avoid N+1 queries

**Performance Considerations:**
- Add **composite indexes** for common query patterns (trainer_id + caught_at)
- Use **batch loading** for related entities (avoid N queries)
- Implement **pagination** with cursor-based approach for large datasets
- Consider **caching** for frequently accessed summaries

**Implementation Details:**
```python
# Use eager loading to avoid N+1 queries
from sqlalchemy.orm import joinedload

def get_catch_log(self, trainer_id: str, skip: int = 0, limit: int = 100):
    return (
        self.db.query(TrainerCatch)
        .options(
            joinedload(TrainerCatch.pokemon),
            joinedload(TrainerCatch.trainer)
        )
        .filter(TrainerCatch.trainer_id == trainer_id)
        .order_by(TrainerCatch.caught_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
```

**Edge Cases:**
- Trainer with no catches (return empty list, not error)
- Pokemon deleted after being caught (use RESTRICT constraint)
- Concurrent catch attempts (use row-level locking)
- Future timestamps (add CHECK constraint)

**References:**
- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- SQLAlchemy eager loading: https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html
- Repository pattern: https://martinfowler.com/eaaCatalog/repository.html

### Implementation Phases

#### Phase 1: Data Model & Repository

**Tasks:**
- Create TrainerCatch model in `app/models.py`
- Add composite primary key and indexes
- Create TrainerCatchRepository with specialized query methods
- Add methods for checking catch status, getting catch counts by type/generation

**Success Criteria:**
- TrainerCatch model with all required fields
- Database indexes created
- Repository passes unit tests

**Estimated Effort:** 30 minutes

### Research Insights: Data Model

**Best Practices:**
- Use **composite primary key** for uniqueness enforcement
- Add **CHECK constraints** for data validation at database level
- Use **proper foreign key constraints** (CASCADE for trainer, RESTRICT for pokemon)
- Create **covering indexes** for common query patterns

**Performance Considerations:**
- Index foreign keys for JOIN performance
- Add composite indexes for filter + sort patterns
- Use partial indexes for active trainers only
- Consider index-only scans for aggregations

**Implementation Details:**
```python
class TrainerCatch(Base):
    __tablename__ = "trainer_catches"
    __table_args__ = (
        PrimaryKeyConstraint("trainer_id", "pokemon_id"),
        
        # CHECK constraints for data integrity
        CheckConstraint(
            "caught_at <= CURRENT_TIMESTAMP",
            name="ck_catch_timestamp_not_future"
        ),
        CheckConstraint(
            "pokemon_id >= 1 AND pokemon_id <= 493",
            name="ck_pokemon_id_valid_range"
        ),
        
        # Indexes for performance
        Index("idx_trainer_catches_trainer_id", "trainer_id"),
        Index("idx_trainer_catches_pokemon_id", "pokemon_id"),
        Index("idx_trainer_catches_caught_at", "caught_at"),
        Index("idx_trainer_catches_trainer_date", "trainer_id", "caught_at"),
    )
    
    trainer_id: Mapped[str] = mapped_column(
        ForeignKey("trainers.id", ondelete="CASCADE"),
        nullable=False
    )
    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="RESTRICT"),  # Prevent data loss
        nullable=False
    )
    caught_at: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=lambda: datetime.now(UTC),
        nullable=False
    )
    
    # Relationships with eager loading
    trainer: Mapped["Trainer"] = relationship(init=False, lazy="joined")
    pokemon: Mapped["Pokemon"] = relationship(init=False, lazy="joined")
```

**Edge Cases:**
- Pokemon deletion should fail if catches exist (RESTRICT)
- Trainer deletion should cascade to catches (CASCADE)
- Future timestamps should be rejected (CHECK constraint)
- Invalid pokemon_id should be rejected (CHECK constraint)

**References:**
- SQLAlchemy constraints: https://docs.sqlalchemy.org/en/20/core/constraints.html
- Foreign key options: https://www.postgresql.org/docs/current/ddl-constraints.html

#### Phase 2: Service Layer & Business Logic

**Tasks:**
- Extend TrainerService with catch tracking methods
- Implement mark_pokemon_caught with duplicate prevention
- Implement unmark_pokemon_caught
- Implement get_catch_log with pagination
- Implement get_catch_summary with completion percentage
- Add methods for getting catches by type and generation
- Add authorization checks (trainer_id matches X-User-ID)

**Success Criteria:**
- Catch marking/unmarking works correctly
- Duplicate catches are prevented
- Summary calculations are accurate
- Authorization enforced

**Estimated Effort:** 45 minutes

### Research Insights: Service Layer

**Best Practices:**
- Use **custom exception classes** for domain errors
- Implement **transaction boundaries** explicitly
- Add **row-level locking** for race condition prevention
- Use **batch loading** for related entities

**Performance Considerations:**
- Avoid N+1 queries with eager loading
- Use database aggregations instead of Python loops
- Cache frequently accessed summaries
- Use connection pooling

**Implementation Details:**
```python
# Custom exception hierarchy
class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundError(AppException):
    """Resource not found."""
    pass

class AuthorizationError(AppException):
    """Permission denied."""
    pass

class ConflictError(AppException):
    """Resource conflict (e.g., duplicate)."""
    pass

# Service with proper transaction handling
def mark_pokemon_caught(
    self, 
    trainer_id: str, 
    pokemon_id: int,
    current_user_id: str
) -> tuple[TrainerCatch, Pokemon]:
    """Mark a pokemon as caught with race condition prevention."""
    
    # Authorization check (outside transaction)
    if trainer_id != current_user_id:
        raise AuthorizationError(
            "Permission denied: cannot modify another trainer's catch log."
        )
    
    try:
        # Use row-level locking to prevent race conditions
        existing = (
            self.db.query(TrainerCatch)
            .filter(
                TrainerCatch.trainer_id == trainer_id,
                TrainerCatch.pokemon_id == pokemon_id
            )
            .with_for_update()
            .first()
        )
        
        if existing:
            raise ConflictError(
                f"Pokemon already marked as caught"
            )
        
        # Validate pokemon exists
        pokemon = self.pokemon_repo.get(pokemon_id)
        if not pokemon:
            raise NotFoundError(f"Pokemon with ID {pokemon_id} not found")
        
        # Create catch record
        catch = TrainerCatch(trainer_id=trainer_id, pokemon_id=pokemon_id)
        self.db.add(catch)
        self.db.commit()
        
        return catch, pokemon
        
    except IntegrityError:
        self.db.rollback()
        raise ConflictError("Pokemon already marked as caught") from None
```

**Edge Cases:**
- Concurrent requests for same catch (use with_for_update())
- Pokemon deleted between check and create (use transaction)
- Trainer deleted during operation (CASCADE handles it)
- Database connection lost (rollback and retry)

**References:**
- SQLAlchemy transactions: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- Row-level locking: https://docs.sqlalchemy.org/en/20/orm/query.html#sqlalchemy.orm.Query.with_for_update

#### Phase 3: API Endpoints

**Tasks:**
- Extend GET /pokedex/{pokemon_id} to include is_caught field
- Create POST /trainers/{trainer_id}/pokedex/{pokemon_id} endpoint
- Create DELETE /trainers/{trainer_id}/pokedex/{pokemon_id} endpoint
- Create GET /trainers/{trainer_id}/pokedex endpoint (catch log)
- Create GET /trainers/{trainer_id}/pokedex/summary endpoint
- Add proper error handling and validation
- Update schemas with new response models

**Success Criteria:**
- All endpoints functional with correct HTTP status codes
- Pokédex endpoint conditionally includes catch status
- Error messages are clear and helpful
- Authorization works correctly

**Estimated Effort:** 45 minutes

### Research Insights: API Layer

**Best Practices:**
- Use **Pydantic schemas** for request/response validation
- Implement **conditional response fields** for optional data
- Add **comprehensive error handling** with custom exceptions
- Use **dependency injection** for services

**Performance Considerations:**
- Minimize database queries per request
- Use pagination for large result sets
- Cache reference data (Pokemon species)
- Implement rate limiting for abuse prevention

**Implementation Details:**
```python
# Exception handler for clean error responses
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Map domain exceptions to HTTP responses."""
    mapping = {
        NotFoundError: 404,
        AuthorizationError: 403,
        ConflictError: 409,
        ValidationError: 400,
    }
    
    status_code = mapping.get(type(exc), 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

# Endpoint with proper error handling
@router.post("/{trainer_id}/pokedex/{pokemon_id}", response_model=CatchResponse)
def mark_pokemon_caught(
    trainer_id: str,
    pokemon_id: int,
    current_user: dict = Depends(get_current_user),
    service: CatchService = Depends(get_catch_service),
):
    """Mark a Pokemon as caught."""
    # No try/except needed - exception handler does the work
    catch, pokemon = service.mark_pokemon_caught(
        trainer_id, pokemon_id, current_user["id"]
    )
    
    return CatchResponse(
        trainer_id=trainer_id,
        pokemon_id=pokemon_id,
        pokemon_name=pokemon.name,
        caught_at=catch.caught_at,
    )

# Conditional response field
@router.get("/{pokemon_id}", response_model=PokemonResponse)
def get_pokemon(
    pokemon_id: int,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    pokemon_service: PokemonService = Depends(get_pokemon_service),
    trainer_service: TrainerService = Depends(get_trainer_service),
):
    """Get Pokemon details with optional catch status."""
    pokemon = pokemon_service.get_pokemon(pokemon_id)
    if not pokemon:
        raise NotFoundError(f"Pokemon with ID '{pokemon_id}' not found")
    
    response = PokemonResponse.model_validate(pokemon)
    
    # Add is_caught field only if user is a trainer
    if x_user_id:
        trainer = trainer_service.get_trainer(x_user_id)
        if trainer:
            is_caught = trainer_service.has_caught_pokemon(x_user_id, pokemon_id)
            response.is_caught = is_caught
    
    return response
```

**Edge Cases:**
- Invalid X-User-ID format (validate UUID)
- Non-existent trainer (return 404)
- Ranger attempting catch tracking (return 403)
- Pokemon not found (return 404)
- Already caught (return 409)

**References:**
- FastAPI error handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Pydantic schemas: https://docs.pydantic.dev/latest/

#### Phase 4: Testing

**Tasks:**
- Write tests for marking Pokémon as caught
- Write tests for unmarking Pokémon
- Write tests for duplicate catch prevention
- Write tests for catch log retrieval
- Write tests for catch summary calculations
- Write tests for authorization (only owner can modify)
- Write tests for Pokédex endpoint with/without X-User-ID
- Write tests for Ranger rejection

**Success Criteria:**
- All tests pass
- Edge cases covered
- Tests demonstrate understanding of requirements

**Estimated Effort:** 30 minutes

### Research Insights: Testing

**Best Practices:**
- Use **test data builders** for readable test setup
- Implement **property-based testing** for edge cases
- Test **authorization** thoroughly
- Use **fixtures** for common test data

**Performance Considerations:**
- Use in-memory database for fast tests
- Mock external dependencies
- Parallelize test execution
- Use test coverage tools

**Implementation Details:**
```python
# Test data builder pattern
from factory import Factory, LazyFunction
import uuid

class TrainerBuilder(Factory):
    class Meta:
        model = dict
    
    id = LazyFunction(lambda: str(uuid.uuid4()))
    name = Faker("name")
    email = Faker("email")

class CatchBuilder(Factory):
    class Meta:
        model = dict
    
    trainer_id = LazyFunction(lambda: str(uuid.uuid4()))
    pokemon_id = 25  # Pikachu
    caught_at = LazyFunction(lambda: datetime.now(UTC))

# Test with builder
def test_mark_pokemon_caught(client, db):
    trainer = TrainerBuilder.create()
    pokemon_id = 25
    
    response = client.post(
        f"/v1/trainers/{trainer['id']}/pokedex/{pokemon_id}",
        headers={"X-User-ID": trainer["id"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pokemon_id"] == pokemon_id
    assert data["trainer_id"] == trainer["id"]

# Property-based testing
from hypothesis import given, strategies as st

@given(
    pokemon_id=st.integers(min_value=1, max_value=493),
)
def test_catch_pokemon_validates_id(client, pokemon_id):
    """Property: all valid pokemon IDs should work."""
    trainer = TrainerBuilder.create()
    
    response = client.post(
        f"/v1/trainers/{trainer['id']}/pokedex/{pokemon_id}",
        headers={"X-User-ID": trainer["id"]}
    )
    
    assert response.status_code in [200, 409]  # Created or already caught
```

**Edge Cases:**
- Duplicate catches (return 409)
- Invalid pokemon_id (return 404)
- Unauthorized modification (return 403)
- Ranger attempting catch tracking (return 403)
- Empty catch log (return empty list)

**References:**
- pytest fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html
- Hypothesis testing: https://hypothesis.readthedocs.io/

## Acceptance Criteria

### Functional Requirements

- [x] Trainer can mark a Pokémon species as caught (records date caught)
- [x] Trainer can unmark a Pokémon (remove from catch log)
- [x] Duplicate catches are prevented (same trainer, same pokemon)
- [x] GET /pokedex/{pokemon_id} includes is_caught field when X-User-ID is a Trainer
- [x] GET /pokedex/{pokemon_id} works normally without X-User-ID header
- [x] Trainer can view their full catch log (which species and when)
- [x] Trainer can view catch summary: total caught, by type, by generation, completion %
- [x] Anyone can view any Trainer's catch log and summary (public data)
- [x] Only the Trainer can modify their own catch log (authorization)
- [x] Rangers cannot access catch-tracking features (role enforcement)
- [x] Attempting to mark non-existent Pokémon returns 404
- [x] Attempting to mark already-caught Pokémon returns appropriate error

### Non-Functional Requirements

- [x] Database queries use indexes (no full table scans)
- [x] API responses follow existing response model patterns
- [x] Error messages are descriptive and actionable
- [x] Code follows existing patterns (services, repositories, dependency injection)
- [x] Proper separation of concerns maintained
- [x] Performance acceptable with 493 Pokémon species

### Quality Gates

- [x] All tests pass
- [x] Code passes linting (ruff) and type checking (ty)
- [x] No regression in existing tests
- [ ] Code review approval

## Success Metrics

- Trainers can successfully track their caught Pokémon
- Completion percentage accurately reflects progress (caught / 493)
- Pokédex endpoint correctly shows catch status for authenticated Trainers
- Authorization prevents unauthorized modifications
- Performance is acceptable even with all 493 species

## Dependencies & Prerequisites

- Existing Trainer model and repository
- Existing Pokémon model and repository
- Existing authentication system (X-User-ID header)
- Existing Pokédex endpoints to extend
- Test fixtures for trainers and pokemon

## Risk Analysis & Mitigation

**Risk:** Duplicate catches creating inconsistent data
**Mitigation:** Use composite primary key (trainer_id, pokemon_id) to enforce uniqueness at database level. Check for existing catch before creating.

**Risk:** Performance with 493 species per trainer
**Mitigation:** Add proper database indexes. Use efficient aggregation queries. Consider pagination for catch log.

**Risk:** Breaking existing Pokédex endpoint
**Mitigation:** Make is_caught field optional in response. Only include when X-User-ID is provided and is a Trainer. Maintain backward compatibility.

**Risk:** Authorization bypass
**Mitigation:** Validate X-User-ID matches trainer_id in path for all modification operations. Use existing get_current_user dependency.

**Risk:** Ranger attempting to use catch tracking
**Mitigation:** Check user role in service layer. Return 403 Forbidden with clear error message.

### Research Insights: Security

**Critical Findings:**
- **Authentication bypass** via X-User-ID header spoofing
- **Race condition** in duplicate catch prevention
- **Missing input validation** for pokemon_id range
- **No rate limiting** for catch operations

**Recommendations:**
1. Implement **JWT or API key authentication** instead of raw UUID
2. Use **row-level locking** for race condition prevention
3. Add **CHECK constraints** for pokemon_id validation
4. Implement **rate limiting** (10 catches per minute)

**Implementation:**
```python
# Rate limiting
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.post(
    "/{trainer_id}/pokedex/{pokemon_id}",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
def mark_pokemon_caught(...):
    # Max 10 catches per minute
    pass

# Input validation
class CatchCreate(BaseModel):
    pokemon_id: int = Field(..., ge=1, le=493)
    
    @field_validator('pokemon_id')
    @classmethod
    def validate_pokemon_id(cls, v: int) -> int:
        if not 1 <= v <= 493:
            raise ValueError('pokemon_id must be between 1 and 493')
        return v
```

**References:**
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- FastAPI security: https://fastapi.tiangolo.com/tutorial/security/

## Best Practices & Research Findings

### Many-to-Many Relationship Pattern

**Pattern:** Use a junction table for the many-to-many relationship between Trainers and Pokémon.

```python
class TrainerCatch(Base):
    __tablename__ = "trainer_catches"
    __table_args__ = (
        PrimaryKeyConstraint("trainer_id", "pokemon_id"),
        Index("idx_trainer_catches_trainer_id", "trainer_id"),
        Index("idx_trainer_catches_pokemon_id", "pokemon_id"),
        Index("idx_trainer_catches_caught_at", "caught_at"),
    )
    
    trainer_id: Mapped[str] = mapped_column(ForeignKey("trainers.id", ondelete="CASCADE"))
    pokemon_id: Mapped[int] = mapped_column(ForeignKey("pokemon.id", ondelete="CASCADE"))
    caught_at: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=lambda: datetime.now(UTC),
        insert_default=lambda: datetime.now(UTC),
    )
    
    trainer: Mapped["Trainer"] = relationship("Trainer", init=False, lazy="select")
    pokemon: Mapped["Pokemon"] = relationship("Pokemon", init=False, lazy="select")
```

**Benefits:**
- Enforces uniqueness at database level
- Allows storing additional data (caught_at timestamp)
- Efficient querying by trainer or by pokemon
- Proper foreign key constraints with cascade delete

### Conditional Response Fields

**Pattern:** Use Optional fields in Pydantic response models for conditional data.

```python
class PokemonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    type1: str
    type2: str | None
    generation: int
    is_legendary: bool
    is_mythical: bool
    is_baby: bool
    capture_rate: int
    evolution_chain_id: int | None
    is_caught: bool | None = None  # Only included when X-User-ID is a Trainer
```

**Implementation:**
```python
@router.get("/{pokemon_id}", response_model=PokemonResponse)
def get_pokemon(
    request: Request,
    pokemon_id: int,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    service: PokemonService = Depends(get_pokemon_service),
    trainer_service: TrainerService = Depends(get_trainer_service),
):
    pokemon = service.get_pokemon(pokemon_id)
    if not pokemon:
        raise HTTPException(status_code=404, detail=f"Pokemon with ID '{pokemon_id}' not found")
    
    response_data = PokemonResponse.model_validate(pokemon)
    
    # Check if user is a trainer and if they've caught this pokemon
    if x_user_id:
        user = trainer_service.get_trainer(x_user_id)
        if user:
            is_caught = trainer_service.has_caught_pokemon(x_user_id, pokemon_id)
            response_data.is_caught = is_caught
    
    return response_data
```

### Efficient Aggregation Queries

**Pattern:** Use SQLAlchemy's func module for efficient counting and grouping.

```python
def get_catch_summary(self, trainer_id: str) -> dict:
    """Get catch summary with single query."""
    from sqlalchemy import func
    
    # Total caught
    total_caught = self.db.query(func.count(TrainerCatch.pokemon_id)).filter(
        TrainerCatch.trainer_id == trainer_id
    ).scalar()
    
    # Caught by type (need to join with Pokemon table)
    caught_by_type = self.db.query(
        Pokemon.type1,
        func.count(TrainerCatch.pokemon_id).label("count")
    ).join(
        TrainerCatch, Pokemon.id == TrainerCatch.pokemon_id
    ).filter(
        TrainerCatch.trainer_id == trainer_id
    ).group_by(
        Pokemon.type1
    ).all()
    
    # Caught by generation
    caught_by_generation = self.db.query(
        Pokemon.generation,
        func.count(TrainerCatch.pokemon_id).label("count")
    ).join(
        TrainerCatch, Pokemon.id == TrainerCatch.pokemon_id
    ).filter(
        TrainerCatch.trainer_id == trainer_id
    ).group_by(
        Pokemon.generation
    ).all()
    
    return {
        "total_caught": total_caught,
        "completion_percentage": round((total_caught / 493) * 100, 2),
        "caught_by_type": {row.type1: row.count for row in caught_by_type},
        "caught_by_generation": {row.generation: row.count for row in caught_by_generation},
    }
```

### Authorization Pattern

**Pattern:** Validate ownership before allowing modifications.

```python
def mark_pokemon_caught(self, trainer_id: str, pokemon_id: int, current_user_id: str) -> TrainerCatch:
    """Mark a pokemon as caught with authorization check."""
    # Authorization: only the trainer can modify their own catch log
    if trainer_id != current_user_id:
        raise ValueError(
            f"Permission denied: cannot modify another trainer's catch log. "
            f"Path trainer_id: {trainer_id}, your ID: {current_user_id}"
        )
    
    # Check if pokemon exists
    pokemon = self.pokemon_repo.get(pokemon_id)
    if not pokemon:
        raise ValueError(f"Pokemon with ID {pokemon_id} not found")
    
    # Check for duplicate
    existing = self.trainer_catch_repo.get_by_trainer_and_pokemon(trainer_id, pokemon_id)
    if existing:
        raise ValueError(
            f"Pokemon '{pokemon.name}' (ID: {pokemon_id}) is already marked as caught"
        )
    
    # Create catch record
    return self.trainer_catch_repo.create({
        "trainer_id": trainer_id,
        "pokemon_id": pokemon_id,
    })
```

### Edge Cases & Gotchas

**1. Duplicate Catches:**
- Use composite primary key to prevent at database level
- Check for existing catch before creating
- Return appropriate error message

**2. Non-Existent Pokémon:**
- Validate pokemon_id exists before creating catch
- Return 404 with clear message

**3. Authorization Edge Cases:**
- Trainer trying to modify another trainer's catch log
- Ranger trying to use catch tracking features
- Unauthenticated user trying to modify catches

**4. Performance Considerations:**
- Catch log should be paginated (493 entries max)
- Summary queries should use indexes
- Consider caching summary for frequently accessed trainers

**5. Data Integrity:**
- Use CASCADE delete for foreign keys (if trainer deleted, catches deleted)
- Use SET NULL or CASCADE for pokemon deletion (unlikely but handle it)
- Validate caught_at timestamp is in the past or now

**6. Pokédex Endpoint Behavior:**
- Without X-User-ID: return normal pokemon data (no is_caught field)
- With X-User-ID but not a trainer: return normal pokemon data
- With X-User-ID and is a trainer: include is_caught field

## Resource Requirements

- Development time: ~2.5 hours
- No external dependencies required
- Database migration needed for new table

## Future Considerations

- Catch statistics and leaderboards for trainers
- Shiny tracking (separate from regular catches)
- Catch location tracking
- Trade history between trainers
- Collection comparison between trainers
- Export catch log to external format

## Documentation Plan

- Update NOTES.md with design decisions
- Document authorization rules in code comments
- Document the conditional is_caught field behavior
- Update README if API contract changes significantly

## References & Research

### Internal References

- Trainer model: `app/models.py:42-58`
- Trainer service: `app/services/trainer_service.py:8-39`
- Trainer repository: `app/repositories/trainer_repository.py:7-15`
- Pokemon endpoint: `app/api/v1/pokemon.py:58-74`
- Authentication pattern: `app/api/deps.py:81-110`
- Middleware for X-User-ID: `app/middleware.py:25`
- Schemas: `app/schemas.py:54-67` (PokemonResponse)

### External References

- SQLAlchemy many-to-many: https://docs.sqlalchemy.org/en/20/orm/relationships.html#many-to-many
- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- Pydantic optional fields: https://docs.pydantic.dev/latest/concepts/fields/#optional-fields
- SQLAlchemy composite primary keys: https://docs.sqlalchemy.org/en/20/core/constraints.html#primary-key-constraint

### Related Work

- Feature 1: Sighting Filters & Pagination (pagination pattern)
- Feature 2: Research Campaigns (authorization pattern)
- Feature 3: Peer Confirmation System (validation pattern)

## Implementation Notes

### Database Schema

```sql
-- New trainer_catches table
CREATE TABLE trainer_catches (
    trainer_id TEXT NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id) ON DELETE RESTRICT,
    caught_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trainer_id, pokemon_id),
    CONSTRAINT ck_catch_timestamp_not_future CHECK (caught_at <= CURRENT_TIMESTAMP),
    CONSTRAINT ck_pokemon_id_valid_range CHECK (pokemon_id >= 1 AND pokemon_id <= 493)
);

-- Indexes for performance
CREATE INDEX idx_trainer_catches_trainer_id ON trainer_catches(trainer_id);
CREATE INDEX idx_trainer_catches_pokemon_id ON trainer_catches(pokemon_id);
CREATE INDEX idx_trainer_catches_caught_at ON trainer_catches(caught_at);
CREATE INDEX idx_trainer_catches_trainer_date ON trainer_catches(trainer_id, caught_at);
```

### API Response Models

```python
# Add to app/schemas.py

class TrainerCatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    pokemon_id: int
    pokemon_name: str
    caught_at: datetime

class CatchLogResponse(BaseModel):
    trainer_id: str
    trainer_name: str
    catches: list[TrainerCatchResponse]
    total: int

class CatchSummaryResponse(BaseModel):
    trainer_id: str
    trainer_name: str
    total_caught: int
    completion_percentage: float
    caught_by_type: dict[str, int]
    caught_by_generation: dict[int, int]

# Update existing PokemonResponse
class PokemonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    type1: str
    type2: str | None
    generation: int
    is_legendary: bool
    is_mythical: bool
    is_baby: bool
    capture_rate: int
    evolution_chain_id: int | None
    is_caught: bool | None = None  # Conditional field
```

### Business Rules

1. Only Trainers can use catch-tracking features (not Rangers)
2. Only the Trainer can modify their own catch log
3. Anyone can view any Trainer's catch log and summary (public data)
4. Duplicate catches are prevented (same trainer, same pokemon)
5. Completion percentage is calculated as (total_caught / 493) * 100
6. is_caught field only appears in Pokédex response when X-User-ID is a Trainer

### Error Handling

```python
# Specific error cases with clear messages

# Attempting to mark already-caught pokemon
409: "Pokemon 'Pikachu' (ID: 25) is already marked as caught"

# Attempting to modify another trainer's catch log
403: "Permission denied: cannot modify another trainer's catch log. You can only modify your own catch log."

# Ranger attempting catch tracking
403: "Only Pokémon Trainers can use catch-tracking features. Rangers do not have access to this functionality."

# Non-existent pokemon
404: "Pokemon with ID '999' not found"

# Non-existent trainer
404: "Trainer with ID 'invalid-uuid' not found"

# Attempting to unmark non-caught pokemon
404: "Pokemon 'Pikachu' (ID: 25) is not in your catch log"
```

## Implementation Checklist

### Pre-Implementation
- [ ] Review existing codebase patterns (models, services, repositories)
- [ ] Understand current Pokédex endpoint behavior
- [ ] Review test fixtures and test patterns
- [ ] Plan database migration strategy

### Phase 1: Data Model
- [ ] Create TrainerCatch model in `app/models.py`
- [ ] Add composite primary key and indexes
- [ ] Create TrainerCatchRepository extending BaseRepository
- [ ] Add specialized query methods (get_by_trainer_and_pokemon, get_catch_log, etc.)
- [ ] Test model creation and basic CRUD operations

### Phase 2: Service Layer
- [ ] Extend TrainerService with catch tracking methods
- [ ] Implement mark_pokemon_caught with validation
- [ ] Implement unmark_pokemon_caught
- [ ] Implement has_caught_pokemon check
- [ ] Implement get_catch_log with pagination
- [ ] Implement get_catch_summary with aggregations
- [ ] Add authorization checks
- [ ] Add comprehensive error handling

### Phase 3: API Layer
- [ ] Update PokemonResponse schema to include is_caught field
- [ ] Extend GET /pokedex/{pokemon_id} to conditionally include is_caught
- [ ] Create POST /trainers/{trainer_id}/pokedex/{pokemon_id} endpoint
- [ ] Create DELETE /trainers/{trainer_id}/pokedex/{pokemon_id} endpoint
- [ ] Create GET /trainers/{trainer_id}/pokedex endpoint
- [ ] Create GET /trainers/{trainer_id}/pokedex/summary endpoint
- [ ] Add proper error responses and logging
- [ ] Update router to include new endpoints

### Phase 4: Testing
- [ ] Write test: trainer can mark pokemon as caught
- [ ] Write test: trainer can unmark pokemon
- [ ] Write test: duplicate catch prevention
- [ ] Write test: catch log retrieval
- [ ] Write test: catch summary calculations
- [ ] Write test: authorization (only owner can modify)
- [ ] Write test: Pokédex endpoint with X-User-ID (trainer)
- [ ] Write test: Pokédex endpoint without X-User-ID
- [ ] Write test: Pokédex endpoint with X-User-ID (ranger)
- [ ] Write test: Ranger rejection
- [ ] Run all tests and ensure no regressions

### Phase 5: Integration & Polish
- [ ] Run linting (ruff) and fix issues
- [ ] Run type checking (ty) and fix issues
- [ ] Test with seed data
- [ ] Verify performance (queries use indexes)
- [ ] Update NOTES.md with design decisions
- [ ] Add code comments for complex logic
- [ ] Final code review

### Post-Implementation
- [ ] All tests pass
- [ ] No regressions in existing functionality
- [ ] Performance acceptable
- [ ] Error messages are clear and helpful
- [ ] Code follows project conventions
