---
title: feat: Research Campaigns with Lifecycle Management
type: feat
status: completed
date: 2026-03-06
---

# feat: Research Campaigns with Lifecycle Management

## Overview

Implement full CRUD for research campaigns with state machine lifecycle (draft → active → completed → archived). Campaigns organize ranger sightings into focused research efforts with clear status tracking and data integrity guarantees.

## Problem Statement

Rangers need to organize field research into structured campaigns (e.g., "Cerulean Cave Survey, February 2026"). Currently, sightings exist in isolation without grouping or lifecycle management. Professor Oak requires campaigns to have clear states so the team knows what's active, what's completed, and to prevent data modification after research is finalized.

## Proposed Solution

Create a Campaign model with state machine lifecycle, integrate with existing sighting system, and enforce business rules around campaign state transitions and sighting locking.

## Technical Approach

### Architecture

**Data Model:**
- Campaign entity with lifecycle state (draft, active, completed, archived)
- Optional foreign key from Sighting to Campaign
- Database indexes for efficient querying

**State Machine:**
- Linear progression: draft → active → completed → archived
- No backward transitions allowed
- State-specific business rules enforced in service layer

**Integration Points:**
- Sighting creation: optional campaign_id parameter
- Sighting modification/deletion: check campaign status
- Campaign summary: aggregate sighting statistics

### Implementation Phases

#### Phase 1: Data Model & Repository

**Tasks:**
- Create Campaign model in `app/models.py`
- Add campaign_id foreign key to Sighting model
- Create database indexes for performance
- Create CampaignRepository with base CRUD operations
- Add migration for new tables/columns

**Success Criteria:**
- Campaign model with all required fields
- Database schema updated
- Repository passes unit tests

**Estimated Effort:** 30 minutes

#### Phase 2: Service Layer & Business Logic

**Tasks:**
- Create CampaignService with lifecycle management
- Implement state transition validation
- Add sighting association logic (active campaigns only)
- Implement sighting locking for completed campaigns
- Create campaign summary aggregation methods

**Success Criteria:**
- State transitions validated correctly
- Business rules enforced (active-only sightings, locked sightings)
- Summary calculations work

**Estimated Effort:** 45 minutes

#### Phase 3: API Endpoints

**Tasks:**
- Create campaign router in `app/api/v1/campaigns.py`
- Implement CRUD endpoints (POST, GET, PATCH)
- Implement transition endpoint (POST /campaigns/{id}/transition)
- Implement summary endpoint (GET /campaigns/{id}/summary)
- Update sighting creation endpoint to accept campaign_id
- Add proper error handling and validation

**Success Criteria:**
- All endpoints functional with correct HTTP status codes
- Error messages are clear and helpful
- Integration with existing sighting system works

**Estimated Effort:** 45 minutes

#### Phase 4: Testing

**Tasks:**
- Implement TestCandidateCampaignLifecycle tests
- Add additional tests for edge cases
- Test state transition validation
- Test sighting locking behavior
- Test campaign summary calculations

**Success Criteria:**
- All required tests pass
- Edge cases covered
- Tests are meaningful and thorough

**Estimated Effort:** 30 minutes

## Acceptance Criteria

### Functional Requirements

- [x] Create campaign with name, description, region, start_date, end_date (starts in 'draft')
- [x] Get campaign details by ID
- [x] Update campaign metadata (name, description, dates) in draft or active state
- [x] Transition campaign through lifecycle: draft → active → completed → archived
- [x] Reject invalid state transitions (backward or skip-ahead)
- [x] Associate sighting with campaign when creating (optional campaign_id)
- [x] Reject sighting creation for non-active campaigns with clear error
- [x] Lock sightings when campaign transitions to 'completed' (no edit/delete)
- [x] Generate campaign summary: total sightings, unique species, contributing rangers, date range
- [x] Validate that only rangers can create/manage campaigns

### Non-Functional Requirements

- [x] Database queries use indexes (no full table scans)
- [x] API responses follow existing response model patterns
- [x] Error messages are descriptive and actionable
- [x] Code follows existing patterns (services, repositories, dependency injection)
- [x] Proper separation of concerns maintained

### Quality Gates

- [x] All TestCandidateCampaignLifecycle tests pass
- [x] Code passes linting (ruff) and type checking (ty)
- [x] No regression in existing tests
- [ ] Code review approval

## Success Metrics

- Campaign lifecycle transitions work correctly
- Sighting locking prevents data modification
- Campaign summary calculations are accurate
- API error handling is comprehensive
- Tests demonstrate understanding of requirements

## Dependencies & Prerequisites

- Existing Sighting model and repository
- Existing Ranger model and authentication (X-User-ID header)
- Database migration system (SQLite via SQLAlchemy)
- Test fixtures for rangers and sightings

## Risk Analysis & Mitigation

**Risk:** State machine logic complexity
**Mitigation:** Centralize state transition validation in service layer, use Python Enum for type safety, add comprehensive tests. Use StrEnum for database compatibility.

**Risk:** Sighting locking race conditions
**Mitigation:** Use database transactions with proper isolation, check campaign status within transaction before any sighting modification. Use `with_for_update()` for row-level locking when needed.

**Risk:** Performance with large sighting counts
**Mitigation:** Add database indexes on campaign_id, use efficient aggregation queries with proper joins, avoid N+1 query problems by using SQLAlchemy's `selectinload` or `joinedload`.

**Risk:** Breaking existing sighting endpoints
**Mitigation:** Make campaign_id optional, maintain backward compatibility, run existing tests

**Risk:** Concurrent campaign state transitions
**Mitigation:** Use database-level constraints and transactions. Implement optimistic locking with version field or use advisory locks for critical sections.

## Best Practices & Research Findings

### State Machine Implementation with Python Enum

**Pattern:** Use Python's `StrEnum` for campaign status to get type safety and database compatibility.

```python
from enum import StrEnum

class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    
    def can_transition_to(self, next_status: "CampaignStatus") -> bool:
        """Validate state transitions."""
        valid_transitions = {
            CampaignStatus.DRAFT: {CampaignStatus.ACTIVE},
            CampaignStatus.ACTIVE: {CampaignStatus.COMPLETED},
            CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
            CampaignStatus.ARCHIVED: set(),  # Terminal state
        }
        return next_status in valid_transitions.get(self, set())
```

**Benefits:**
- Type-safe state comparisons
- Self-documenting code
- IDE autocomplete support
- Prevents typos in state strings
- Centralized transition logic

### Transaction Management & Race Condition Prevention

**Key Principles:**
1. **Keep transactions short** - Complete within tens to hundreds of milliseconds
2. **Check conditions within transaction** - Don't check campaign status outside transaction
3. **Use proper isolation levels** - SQLite default (SERIALIZABLE) is sufficient for this use case
4. **Handle IntegrityError gracefully** - Wrap commits in try/except blocks

**Pattern for Sighting Locking:**

```python
def delete_sighting(self, sighting_id: str, ranger_id: str) -> bool:
    """Delete sighting with campaign lock check."""
    sighting = self.sighting_repo.get(sighting_id)
    if not sighting:
        raise ValueError(f"Sighting {sighting_id} not found")
    
    # Check campaign status within transaction
    if sighting.campaign_id:
        campaign = self.campaign_repo.get(sighting.campaign_id)
        if campaign and campaign.status == CampaignStatus.COMPLETED:
            raise ValueError(
                f"Cannot delete sighting: campaign '{campaign.name}' is completed. "
                "Completed campaign sightings are locked."
            )
    
    # Authorization check
    if sighting.ranger_id != ranger_id:
        raise ValueError("Permission denied: can only delete your own sightings")
    
    return self.sighting_repo.delete(sighting_id)
```

### Performance Optimization Strategies

**Database Indexes:**
```python
# In Campaign model
__table_args__ = (
    Index("idx_campaigns_status", "status"),
    Index("idx_campaigns_region", "region"),
    Index("idx_campaigns_dates", "start_date", "end_date"),
)

# In Sighting model (add to existing indexes)
Index("idx_sightings_campaign_id", "campaign_id"),
Index("idx_sightings_campaign_date", "campaign_id", "date"),
```

**Efficient Aggregation Queries:**
```python
def get_campaign_summary(self, campaign_id: str) -> dict:
    """Get campaign summary with single query."""
    # Use SQLAlchemy's func.count and func.min/max for aggregation
    from sqlalchemy import func
    
    summary = self.db.query(
        func.count(Sighting.id).label("total_sightings"),
        func.count(func.distinct(Sighting.pokemon_id)).label("unique_species"),
        func.min(Sighting.date).label("earliest_date"),
        func.max(Sighting.date).label("latest_date"),
    ).filter(
        Sighting.campaign_id == campaign_id
    ).first()
    
    # Get contributing rangers with single query
    rangers = self.db.query(
        Ranger.name,
        func.count(Sighting.id).label("sighting_count")
    ).join(
        Sighting, Ranger.id == Sighting.ranger_id
    ).filter(
        Sighting.campaign_id == campaign_id
    ).group_by(
        Ranger.id
    ).order_by(
        func.count(Sighting.id).desc()
    ).all()
    
    return {
        "total_sightings": summary.total_sightings,
        "unique_species": summary.unique_species,
        "contributing_rangers": [
            {"name": r.name, "sightings": r.sighting_count}
            for r in rangers
        ],
        "observation_date_range": {
            "start": summary.earliest_date,
            "end": summary.latest_date,
        }
    }
```

**Avoid N+1 Queries:**
- Use `joinedload` or `selectinload` for relationships
- Batch load related entities
- Use aggregation functions instead of Python loops

### Edge Cases & Gotchas

**1. Campaign Date Validation:**
- Ensure `end_date > start_date`
- Consider timezone handling (use UTC consistently)
- Handle campaigns with no sightings (summary should return zeros)

**2. Sighting Campaign Association:**
- Sighting can be created without campaign (campaign_id is optional)
- Sighting can only be associated at creation time (not updated later)
- What happens if campaign is deleted? (Use SET NULL or CASCADE)

**3. State Transition Edge Cases:**
- What if campaign has no sightings when transitioning to completed? (Allow it)
- Can a draft campaign be deleted? (Yes, no data integrity concerns)
- Can campaign dates be updated after activation? (Yes, but not after completion)

**4. Concurrent Access:**
- Two rangers try to add sighting to same campaign simultaneously (OK, both succeed)
- Two admins try to transition campaign state simultaneously (First wins, second gets error)
- Ranger tries to delete sighting while campaign is being completed (Transaction isolation handles this)

**5. Data Integrity:**
- Use foreign key constraints with `ON DELETE SET NULL` for campaign_id
- Add unique constraint on campaign name within region? (Consider this)
- Validate that campaign region matches sighting region? (Optional business rule)

**6. Performance Considerations:**
- Campaign summary query should be fast even with 10,000+ sightings
- Consider caching summary for completed campaigns (they don't change)
- Add pagination to campaign listing endpoint (future consideration)

## Resource Requirements

- Development time: ~2.5 hours
- No external dependencies required
- Database migration needed

## Future Considerations

- Campaign filtering and search endpoints
- Campaign listing with pagination
- Bulk sighting assignment to campaigns
- Campaign analytics and reporting
- Multi-campaign sighting associations (if needed)

## Documentation Plan

- Update NOTES.md with design decisions
- Document state machine rules in code comments
- Document anomaly detection approach (for Feature 5)
- Update README if API contract changes significantly

## References & Research

### Internal References

- Model patterns: `app/models.py:62-95` (Sighting model with indexes)
- Service patterns: `app/services/sighting_service.py:21-52` (create_sighting with validation)
- Repository patterns: `app/repositories/sighting_repository.py:41-76` (filter_sightings with query building)
- API patterns: `app/api/v1/sightings.py:109-166` (create_sighting endpoint with error handling)
- Dependency injection: `app/api/deps.py:40-44` (service factory pattern)
- Test patterns: `tests/test_public.py:501-513` (TestCandidateCampaignLifecycle placeholder)

### External References

- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- SQLAlchemy relationships: https://docs.sqlalchemy.org/en/20/orm/relationships.html
- State machine patterns: https://refactoring.guru/design-patterns/state
- SQLAlchemy session management: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- Python Enum patterns: https://realpython.com/python-enum/
- Race condition prevention: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- Database locking strategies: https://blog.blasphemess.com/sqlalchemy-race-conditions-and-postgresql-advisory-locks/

### Related Work

- Feature 1: Sighting Filters & Pagination (already implemented)
- Feature 3: Peer Confirmation System (will need similar validation patterns)
- Feature 4: Regional Research Summary (will use similar aggregation patterns)

## Implementation Notes

### Database Schema

```sql
-- New campaigns table
CREATE TABLE campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    region TEXT NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Add campaign_id to sightings table
ALTER TABLE sightings ADD COLUMN campaign_id TEXT REFERENCES campaigns(id);

-- Indexes for performance
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_region ON campaigns(region);
CREATE INDEX idx_sightings_campaign_id ON sightings(campaign_id);
```

### State Machine Rules

```
Valid transitions:
  draft → active
  active → completed
  completed → archived

Invalid transitions (reject with 400):
  draft → completed (must go through active)
  active → draft (no backward)
  completed → active (no backward)
  archived → anything (terminal state)
```

### Business Rules

1. Only rangers can create campaigns (validate X-User-ID is a ranger)
2. Only active campaigns can accept new sightings
3. Completed campaigns lock all associated sightings (no edit/delete)
4. Campaign summary only includes sightings from contributing rangers
5. Date range in summary reflects actual observation dates, not campaign dates

### API Response Models

```python
# Campaign schemas (add to app/schemas.py)

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    region: str = Field(..., min_length=1)
    start_date: datetime
    end_date: datetime

class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: str | None
    region: str
    start_date: datetime
    end_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime

class CampaignSummary(BaseModel):
    campaign_id: str
    campaign_name: str
    total_sightings: int
    unique_species: int
    contributing_rangers: list[dict[str, str | int]]
    observation_date_range: dict[str, datetime]
```

### Error Handling

```python
# Specific error cases with clear messages

# Invalid state transition
400: "Cannot transition campaign from 'completed' to 'active'. Campaigns can only move forward through the lifecycle."

# Sighting creation for non-active campaign
400: "Cannot add sighting to campaign 'Cerulean Cave Survey' (status: completed). Only active campaigns can accept new sightings."

# Attempting to delete locked sighting
403: "Cannot delete sighting: it belongs to completed campaign 'Cerulean Cave Survey'. Completed campaign sightings are locked."

# Invalid campaign ID
404: "Campaign with ID 'invalid-uuid' not found"

# Non-ranger attempting campaign operations
  403: "Only Pokémon Rangers can create campaigns. Trainers do not have access to field research features."
```

## Implementation Checklist

### Pre-Implementation
- [x] Review existing codebase patterns (models, services, repositories)
- [x] Understand current sighting creation flow
- [x] Review test fixtures and test patterns
- [x] Plan database migration strategy

### Phase 1: Data Model
- [x] Create CampaignStatus enum in `app/models.py`
- [x] Create Campaign model with all fields and indexes
- [x] Add campaign_id foreign key to Sighting model
- [x] Create CampaignRepository extending BaseRepository
- [x] Test model creation and basic CRUD operations

### Phase 2: Service Layer
- [x] Create CampaignService with dependency injection
- [x] Implement state transition validation using enum
- [x] Add campaign creation with ranger validation
- [x] Implement sighting association logic
- [x] Add sighting locking for completed campaigns
- [x] Implement campaign summary aggregation
- [x] Add comprehensive error handling

### Phase 3: API Layer
- [x] Create campaign router in `app/api/v1/campaigns.py`
- [x] Add campaign dependency injection to `app/api/deps.py`
- [x] Implement POST /campaigns endpoint
- [x] Implement GET /campaigns/{id} endpoint
- [x] Implement PATCH /campaigns/{id} endpoint
- [x] Implement POST /campaigns/{id}/transition endpoint
- [x] Implement GET /campaigns/{id}/summary endpoint
- [x] Update POST /sightings to accept optional campaign_id
- [x] Update DELETE /sightings to check campaign status
- [x] Add proper error responses and logging

### Phase 4: Testing
- [x] Implement test: campaign starts in draft status
- [x] Implement test: valid state transitions work
- [x] Implement test: invalid state transitions rejected
- [x] Implement test: sighting can be added to active campaign
- [x] Implement test: sighting cannot be added to non-active campaign
- [x] Implement test: completed campaign locks sightings
- [x] Implement test: campaign summary calculations
- [x] Add edge case tests (empty campaigns, concurrent access)
- [x] Run all tests and ensure no regressions

### Phase 5: Integration & Polish
- [x] Run linting (ruff) and fix issues
- [x] Run type checking (ty) and fix issues
- [ ] Test with seed data (55,000 sightings)
- [ ] Verify performance (queries use indexes)
- [x] Update NOTES.md with design decisions
- [x] Add code comments for complex logic
- [ ] Final code review

### Post-Implementation
- [x] All tests pass
- [x] No regressions in existing functionality
- [ ] Performance acceptable with large datasets
- [x] Error messages are clear and helpful
- [x] Code follows project conventions
