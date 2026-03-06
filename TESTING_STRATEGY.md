# Comprehensive Testing Strategy for Statistical Anomaly Detection

## Overview

This document provides a complete testing strategy for the GET /regions/{region_name}/analysis endpoint, covering statistical methods (Modified Z-Score with MAD, Poisson distribution, weighted counts), database aggregations, and edge cases.

**Sources:**
- FastAPI official documentation and testing patterns
- pytest best practices and parametrization
- Statistical testing methodologies from statsmodels and scipy
- Industry-standard mocking and fixture patterns
- Performance testing with Locust

---

## Table of Contents

1. [Testing Architecture](#testing-architecture)
2. [Unit Testing Statistical Methods](#unit-testing-statistical-methods)
3. [Integration Testing for API Endpoints](#integration-testing-for-api-endpoints)
4. [Edge Case Testing Strategies](#edge-case-testing-strategies)
5. [Mocking Strategies for Database Queries](#mocking-strategies-for-database-queries)
6. [Test Data Generation Approaches](#test-data-generation-approaches)
7. [Performance Testing Strategies](#performance-testing-strategies)
8. [Statistical Validation in Tests](#statistical-validation-in-tests)
9. [Test Organization and Structure](#test-organization-and-structure)

---

## 1. Testing Architecture

### Testing Pyramid

```
        ┌─────────────┐
        │   E2E Tests │  (Few - Critical user journeys)
        └─────────────┘
      ┌───────────────────┐
      │ Integration Tests  │  (Some - API + DB interactions)
      └───────────────────┘
    ┌─────────────────────────┐
    │     Unit Tests          │  (Many - Statistical methods, business logic)
    └─────────────────────────┘
```

### Test Categories

1. **Unit Tests** - Statistical calculations, rarity tier logic
2. **Integration Tests** - API endpoints with database
3. **Contract Tests** - API schema validation
4. **Performance Tests** - Load testing with Locust
5. **Statistical Validation Tests** - Verify statistical properties

---

## 2. Unit Testing Statistical Methods

### 2.1 Modified Z-Score with MAD Calculations

**Test File:** `tests/unit/test_modified_zscore.py`

```python
import pytest
import numpy as np
from scipy import stats
from app.services.anomaly_detection import calculate_modified_zscore, calculate_mad


class TestModifiedZScore:
    """Unit tests for Modified Z-Score calculations using MAD."""
    
    def test_calculate_mad_basic(self):
        """Test MAD calculation with known values."""
        data = [1, 2, 3, 4, 5]
        mad = calculate_mad(data)
        # MAD = median(|xi - median(x)|)
        # median = 3, deviations = [2, 1, 0, 1, 2], median = 1
        assert mad == 1.0
    
    def test_calculate_mad_with_outliers(self):
        """Test MAD robustness to outliers."""
        data = [1, 2, 3, 4, 5, 100]  # 100 is outlier
        mad = calculate_mad(data)
        # MAD should be robust to the outlier
        assert mad < 10  # Not heavily influenced by outlier
    
    def test_modified_zscore_normal_data(self):
        """Test modified z-score with normally distributed data."""
        np.random.seed(42)
        data = np.random.normal(100, 10, 100).tolist()
        z_scores = calculate_modified_zscore(data)
        
        # Most z-scores should be within ±3 for normal data
        assert np.percentile(np.abs(z_scores), 95) < 3.5
    
    def test_modified_zscore_with_outlier(self):
        """Test that modified z-score correctly identifies outliers."""
        data = [10, 11, 12, 13, 14, 100]  # 100 is clear outlier
        z_scores = calculate_modified_zscore(data)
        
        # The outlier should have highest absolute z-score
        assert np.argmax(np.abs(z_scores)) == 5
        assert np.abs(z_scores[5]) > 3.0
    
    def test_modified_zscore_empty_data(self):
        """Test handling of empty data."""
        with pytest.raises(ValueError, match="empty"):
            calculate_modified_zscore([])
    
    def test_modified_zscore_single_value(self):
        """Test handling of single value."""
        with pytest.raises(ValueError, match="at least 2"):
            calculate_modified_zscore([5])
    
    def test_modified_zscore_uniform_data(self):
        """Test with uniform distribution (edge case)."""
        data = [10, 10, 10, 10, 10]
        z_scores = calculate_modified_zscore(data)
        
        # All z-scores should be 0 for uniform data
        assert all(z == 0 for z in z_scores)
    
    @pytest.mark.parametrize("threshold,expected_outliers", [
        (2.5, 2),  # More sensitive
        (3.0, 1),  # Standard
        (3.5, 1),  # Less sensitive
    ])
    def test_outlier_detection_thresholds(self, threshold, expected_outliers):
        """Test different threshold values for outlier detection."""
        data = [10, 11, 12, 13, 14, 50, 60]
        z_scores = calculate_modified_zscore(data)
        outliers = [i for i, z in enumerate(z_scores) if abs(z) > threshold]
        assert len(outliers) == expected_outliers
```

### 2.2 Poisson Distribution Calculations

**Test File:** `tests/unit/test_poisson.py`

```python
import pytest
import numpy as np
from scipy.stats import poisson
from app.services.anomaly_detection import calculate_poisson_probability


class TestPoissonCalculations:
    """Unit tests for Poisson distribution calculations."""
    
    def test_poisson_probability_basic(self):
        """Test basic Poisson probability calculation."""
        # P(X = k) for Poisson(lambda)
        lambda_param = 10
        k = 10
        prob = calculate_poisson_probability(k, lambda_param)
        
        # Compare with scipy
        expected = poisson.pmf(k, lambda_param)
        assert np.isclose(prob, expected, rtol=1e-10)
    
    def test_poisson_probability_zero_events(self):
        """Test probability of zero events."""
        lambda_param = 5
        prob = calculate_poisson_probability(0, lambda_param)
        expected = poisson.pmf(0, lambda_param)
        assert np.isclose(prob, expected)
    
    def test_poisson_cumulative_probability(self):
        """Test cumulative probability calculation."""
        lambda_param = 10
        k = 15
        # P(X <= k)
        cum_prob = calculate_poisson_cumulative(k, lambda_param)
        expected = poisson.cdf(k, lambda_param)
        assert np.isclose(cum_prob, expected)
    
    def test_poisson_rare_event_detection(self):
        """Test detection of statistically rare events."""
        lambda_param = 10
        observed_count = 25  # Much higher than expected
        
        # Calculate probability of observing >= this count
        prob = 1 - poisson.cdf(observed_count - 1, lambda_param)
        
        # Should be very rare (p < 0.01)
        assert prob < 0.01
    
    def test_poisson_expected_vs_observed(self):
        """Test comparison of observed vs expected counts."""
        expected_rate = 10
        observed_counts = [8, 9, 10, 11, 12]
        
        # Calculate probabilities for each
        probs = [calculate_poisson_probability(k, expected_rate) 
                 for k in observed_counts]
        
        # Most likely count should be near lambda
        max_prob_idx = np.argmax(probs)
        assert observed_counts[max_prob_idx] in [9, 10, 11]
    
    @pytest.mark.parametrize("lambda_param,observed,expected_rare", [
        (5, 15, True),   # High count, should be rare
        (10, 10, False), # Expected count, not rare
        (20, 5, True),   # Low count, should be rare
    ])
    def test_rare_event_classification(self, lambda_param, observed, expected_rare):
        """Test classification of events as rare or not."""
        is_rare = is_poisson_rare_event(observed, lambda_param, threshold=0.01)
        assert is_rare == expected_rare
    
    def test_poisson_with_small_lambda(self):
        """Test Poisson with small lambda (edge case)."""
        lambda_param = 0.5
        probs = [calculate_poisson_probability(k, lambda_param) 
                 for k in range(5)]
        
        # P(X=0) should be highest for small lambda
        assert probs[0] > probs[1]
    
    def test_poisson_goodness_of_fit(self):
        """Test Poisson goodness of fit for data."""
        # Generate data from Poisson distribution
        np.random.seed(42)
        lambda_param = 10
        data = poisson.rvs(lambda_param, size=1000)
        
        # Test if data follows Poisson distribution
        # Using chi-square goodness of fit test
        observed_counts = np.bincount(data)
        expected_counts = poisson.pmf(np.arange(len(observed_counts)), lambda_param) * len(data)
        
        # Chi-square test
        chi2_stat, p_value = stats.chisquare(observed_counts, expected_counts)
        
        # Should not reject null hypothesis (data is Poisson)
        assert p_value > 0.05
```

### 2.3 Weighted Count Calculations

**Test File:** `tests/unit/test_weighted_counts.py`

```python
import pytest
import numpy as np
from app.services.anomaly_detection import calculate_weighted_count


class TestWeightedCounts:
    """Unit tests for weighted count calculations."""
    
    def test_weighted_count_basic(self):
        """Test basic weighted count calculation."""
        counts = [10, 20, 30]
        weights = [1.0, 1.5, 2.0]
        weighted = calculate_weighted_count(counts, weights)
        
        expected = sum(c * w for c, w in zip(counts, weights))
        assert weighted == expected
    
    def test_weighted_count_with_recency(self):
        """Test recency-based weighting."""
        counts = [10, 20, 30]  # Older to newer
        weighted = calculate_weighted_count_with_recency(counts, decay_factor=0.9)
        
        # More recent counts should have higher weight
        assert weighted > sum(counts) / len(counts)
    
    def test_weighted_count_empty(self):
        """Test with empty counts."""
        with pytest.raises(ValueError):
            calculate_weighted_count([], [])
    
    def test_weighted_count_mismatched_lengths(self):
        """Test with mismatched lengths."""
        with pytest.raises(ValueError, match="same length"):
            calculate_weighted_count([1, 2], [1.0])
    
    def test_weighted_count_negative_weights(self):
        """Test handling of negative weights."""
        counts = [10, 20, 30]
        weights = [1.0, -0.5, 2.0]
        
        with pytest.raises(ValueError, match="non-negative"):
            calculate_weighted_count(counts, weights)
    
    @pytest.mark.parametrize("counts,weights,expected", [
        ([10], [1.0], 10.0),
        ([10, 20], [1.0, 1.0], 30.0),
        ([10, 20, 30], [0.5, 1.0, 1.5], 70.0),
    ])
    def test_weighted_count_various_inputs(self, counts, weights, expected):
        """Test various input combinations."""
        result = calculate_weighted_count(counts, weights)
        assert result == expected
```

### 2.4 Rarity Tier Classification Logic

**Test File:** `tests/unit/test_rarity_tier.py`

```python
import pytest
from app.services.anomaly_detection import classify_rarity_tier, RarityTier


class TestRarityTierClassification:
    """Unit tests for rarity tier classification."""
    
    @pytest.mark.parametrize("z_score,expected_tier", [
        (0.5, RarityTier.COMMON),
        (1.5, RarityTier.UNCOMMON),
        (2.5, RarityTier.RARE),
        (3.5, RarityTier.VERY_RARE),
        (4.5, RarityTier.ULTRA_RARE),
    ])
    def test_rarity_tier_from_zscore(self, z_score, expected_tier):
        """Test rarity tier classification based on z-score."""
        tier = classify_rarity_tier(z_score=z_score)
        assert tier == expected_tier
    
    @pytest.mark.parametrize("poisson_prob,expected_tier", [
        (0.5, RarityTier.COMMON),
        (0.1, RarityTier.UNCOMMON),
        (0.01, RarityTier.RARE),
        (0.001, RarityTier.VERY_RARE),
        (0.0001, RarityTier.ULTRA_RARE),
    ])
    def test_rarity_tier_from_poisson(self, poisson_prob, expected_tier):
        """Test rarity tier classification based on Poisson probability."""
        tier = classify_rarity_tier(poisson_prob=poisson_prob)
        assert tier == expected_tier
    
    def test_rarity_tier_combined_metrics(self):
        """Test classification using combined metrics."""
        tier = classify_rarity_tier(
            z_score=2.0,
            poisson_prob=0.05,
            weighted_count_percentile=95
        )
        # Should use most conservative (rarest) classification
        assert tier in [RarityTier.RARE, RarityTier.VERY_RARE]
    
    def test_rarity_tier_boundary_values(self):
        """Test exact boundary values."""
        # Test boundaries between tiers
        assert classify_rarity_tier(z_score=1.0) == RarityTier.COMMON
        assert classify_rarity_tier(z_score=2.0) == RarityTier.UNCOMMON
        assert classify_rarity_tier(z_score=3.0) == RarityTier.RARE
    
    def test_rarity_tier_with_none_values(self):
        """Test handling of None values."""
        # Should handle missing metrics gracefully
        tier = classify_rarity_tier(z_score=None, poisson_prob=0.01)
        assert tier == RarityTier.RARE
```

---

## 3. Integration Testing for API Endpoints

### 3.1 Basic API Testing with TestClient

**Test File:** `tests/integration/test_regions_analysis_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from tests.factories import RegionFactory, SpeciesCountFactory


client = TestClient(app)


class TestRegionsAnalysisEndpoint:
    """Integration tests for GET /regions/{region_name}/analysis."""
    
    def test_get_analysis_success(self, db_session):
        """Test successful analysis retrieval."""
        # Arrange
        region = RegionFactory(name="TestRegion")
        species_counts = SpeciesCountFactory.create_batch(
            10, 
            region=region,
            count=[5, 10, 15, 20, 25, 30, 35, 40, 45, 100]  # Last is outlier
        )
        
        # Act
        response = client.get(f"/regions/{region.name}/analysis")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "region_name" in data
        assert data["region_name"] == region.name
        assert "analysis" in data
        assert "anomalies" in data["analysis"]
    
    def test_get_analysis_region_not_found(self):
        """Test 404 for non-existent region."""
        response = client.get("/regions/NonExistentRegion/analysis")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_analysis_empty_region(self, db_session):
        """Test analysis for region with no data."""
        region = RegionFactory(name="EmptyRegion")
        
        response = client.get(f"/regions/{region.name}/analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"]["total_observations"] == 0
        assert data["analysis"]["anomalies"] == []
    
    def test_get_analysis_with_outliers(self, db_session):
        """Test that outliers are correctly identified."""
        region = RegionFactory(name="OutlierRegion")
        
        # Create data with clear outliers
        normal_counts = [10, 11, 12, 13, 14, 15]
        outlier_counts = [100, 150]  # Clear outliers
        
        for count in normal_counts + outlier_counts:
            SpeciesCountFactory(region=region, count=count)
        
        response = client.get(f"/regions/{region.name}/analysis")
        
        assert response.status_code == 200
        anomalies = response.json()["analysis"]["anomalies"]
        
        # Should detect the outliers
        assert len(anomalies) >= 2
        
        # Outliers should have high rarity tiers
        anomaly_counts = [a["count"] for a in anomalies]
        assert 100 in anomaly_counts or 150 in anomaly_counts
    
    def test_get_analysis_response_schema(self, db_session):
        """Test that response matches expected schema."""
        region = RegionFactory(name="SchemaTest")
        SpeciesCountFactory.create_batch(5, region=region)
        
        response = client.get(f"/regions/{region.name}/analysis")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate schema
        required_fields = [
            "region_name",
            "analysis",
            "analysis.total_observations",
            "analysis.mean_count",
            "analysis.median_count",
            "analysis.mad",
            "analysis.anomalies"
        ]
        
        for field in required_fields:
            parts = field.split(".")
            obj = data
            for part in parts:
                assert part in obj, f"Missing field: {field}"
                obj = obj[part]
    
    @pytest.mark.parametrize("region_name", [
        "Region-With-Dashes",
        "Region_With_Underscores",
        "Region With Spaces",
        "UPPERCASE_REGION",
    ])
    def test_get_analysis_various_region_names(self, region_name, db_session):
        """Test with various region name formats."""
        region = RegionFactory(name=region_name)
        SpeciesCountFactory.create_batch(5, region=region)
        
        # URL encode the region name
        from urllib.parse import quote
        encoded_name = quote(region_name)
        
        response = client.get(f"/regions/{encoded_name}/analysis")
        
        assert response.status_code == 200
        assert response.json()["region_name"] == region_name
```

### 3.2 Database Integration Tests

**Test File:** `tests/integration/test_database_aggregations.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models import Region, SpeciesCount
from app.services.analysis_service import AnalysisService


class TestDatabaseAggregations:
    """Test database aggregation queries."""
    
    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a fresh database session for each test."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session
        
        session.close()
        Base.metadata.drop_all(engine)
    
    def test_aggregate_counts_by_region(self, db_session):
        """Test aggregation of counts by region."""
        # Create test data
        region = Region(name="TestRegion")
        db_session.add(region)
        db_session.commit()
        
        counts = [10, 20, 30, 40, 50]
        for count in counts:
            species_count = SpeciesCount(
                region_id=region.id,
                species_id=1,
                count=count
            )
            db_session.add(species_count)
        db_session.commit()
        
        # Test aggregation
        service = AnalysisService(db_session)
        result = service.aggregate_counts(region.name)
        
        assert result["total"] == sum(counts)
        assert result["mean"] == sum(counts) / len(counts)
        assert result["count"] == len(counts)
    
    def test_aggregate_with_time_filtering(self, db_session):
        """Test time-based filtering in aggregations."""
        from datetime import datetime, timedelta
        
        region = Region(name="TimeTest")
        db_session.add(region)
        db_session.commit()
        
        # Create data with different timestamps
        now = datetime.utcnow()
        for i, days_ago in enumerate([1, 5, 10, 30, 60]):
            species_count = SpeciesCount(
                region_id=region.id,
                species_id=1,
                count=10 + i,
                recorded_at=now - timedelta(days=days_ago)
            )
            db_session.add(species_count)
        db_session.commit()
        
        # Test filtering by date
        service = AnalysisService(db_session)
        
        # Last 7 days
        recent = service.aggregate_counts(
            region.name, 
            start_date=now - timedelta(days=7)
        )
        assert recent["count"] == 2  # Only 1 and 5 days ago
        
        # Last 30 days
        month = service.aggregate_counts(
            region.name,
            start_date=now - timedelta(days=30)
        )
        assert month["count"] == 4
    
    def test_aggregate_with_species_filtering(self, db_session):
        """Test species-based filtering."""
        region = Region(name="SpeciesTest")
        db_session.add(region)
        db_session.commit()
        
        # Create counts for different species
        for species_id in [1, 2, 3]:
            for count in [10, 20, 30]:
                species_count = SpeciesCount(
                    region_id=region.id,
                    species_id=species_id,
                    count=count
                )
                db_session.add(species_count)
        db_session.commit()
        
        service = AnalysisService(db_session)
        
        # Aggregate for specific species
        result = service.aggregate_counts(region.name, species_id=1)
        assert result["count"] == 3
        assert result["total"] == 60
    
    def test_complex_aggregation_query(self, db_session):
        """Test complex aggregation with multiple filters."""
        from datetime import datetime, timedelta
        
        region = Region(name="ComplexTest")
        db_session.add(region)
        db_session.commit()
        
        now = datetime.utcnow()
        
        # Create complex dataset
        for species_id in [1, 2]:
            for days_ago in [1, 10, 30]:
                for count in [10, 20]:
                    species_count = SpeciesCount(
                        region_id=region.id,
                        species_id=species_id,
                        count=count,
                        recorded_at=now - timedelta(days=days_ago)
                    )
                    db_session.add(species_count)
        db_session.commit()
        
        service = AnalysisService(db_session)
        
        # Complex query: species 1, last 15 days
        result = service.aggregate_counts(
            region.name,
            species_id=1,
            start_date=now - timedelta(days=15)
        )
        
        # Should get 4 records (2 counts × 2 recent dates)
        assert result["count"] == 4
```

---

## 4. Edge Case Testing Strategies

### 4.1 Edge Case Test Matrix

**Test File:** `tests/unit/test_edge_cases.py`

```python
import pytest
import numpy as np
from app.services.anomaly_detection import (
    calculate_modified_zscore,
    calculate_poisson_probability,
    classify_rarity_tier
)


class TestEdgeCases:
    """Comprehensive edge case testing."""
    
    # ==================== Empty Data ====================
    
    def test_empty_dataset(self):
        """Test handling of empty dataset."""
        with pytest.raises(ValueError, match="empty"):
            calculate_modified_zscore([])
    
    def test_empty_region_analysis(self, client, db_session):
        """Test API with region containing no data."""
        from tests.factories import RegionFactory
        region = RegionFactory(name="EmptyRegion")
        
        response = client.get(f"/regions/{region.name}/analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"]["total_observations"] == 0
    
    # ==================== Small Samples ====================
    
    @pytest.mark.parametrize("data_size", [1, 2, 3, 5, 10])
    def test_small_sample_sizes(self, data_size):
        """Test with various small sample sizes."""
        data = list(range(1, data_size + 1))
        
        if data_size < 2:
            with pytest.raises(ValueError):
                calculate_modified_zscore(data)
        else:
            result = calculate_modified_zscore(data)
            assert len(result) == data_size
    
    def test_minimum_viable_sample(self):
        """Test with minimum viable sample size (n=2)."""
        data = [10, 20]
        z_scores = calculate_modified_zscore(data)
        
        assert len(z_scores) == 2
        # One should be negative, one positive
        assert z_scores[0] < 0
        assert z_scores[1] > 0
    
    # ==================== Uniform Distribution ====================
    
    def test_uniform_distribution(self):
        """Test with uniform distribution (all same values)."""
        data = [10, 10, 10, 10, 10]
        z_scores = calculate_modified_zscore(data)
        
        # All z-scores should be 0 (no deviation from median)
        assert all(z == 0 for z in z_scores)
    
    def test_near_uniform_distribution(self):
        """Test with near-uniform distribution."""
        data = [10, 10, 10, 10, 11]  # One slightly different
        z_scores = calculate_modified_zscore(data)
        
        # Most should be near 0, one should be slightly different
        assert sum(1 for z in z_scores if abs(z) < 0.5) >= 4
    
    # ==================== Extreme Values ====================
    
    def test_extreme_outlier(self):
        """Test with extreme outlier."""
        data = [10, 11, 12, 13, 14, 1000000]
        z_scores = calculate_modified_zscore(data)
        
        # The outlier should have very high z-score
        assert z_scores[5] > 10
    
    def test_extreme_values_range(self):
        """Test with very large value range."""
        data = [1, 1000000, 2000000, 3000000]
        z_scores = calculate_modified_zscore(data)
        
        # Should handle large values without overflow
        assert all(np.isfinite(z) for z in z_scores)
    
    # ==================== Zero and Negative Values ====================
    
    def test_zero_values(self):
        """Test with zero values."""
        data = [0, 0, 0, 10, 20]
        z_scores = calculate_modified_zscore(data)
        
        # Should handle zeros correctly
        assert len(z_scores) == 5
    
    def test_negative_values(self):
        """Test with negative values."""
        data = [-10, -5, 0, 5, 10]
        z_scores = calculate_modified_zscore(data)
        
        # Should handle negatives
        assert all(np.isfinite(z) for z in z_scores)
    
    # ==================== Poisson Edge Cases ====================
    
    def test_poisson_zero_lambda(self):
        """Test Poisson with lambda = 0."""
        with pytest.raises(ValueError, match="positive"):
            calculate_poisson_probability(5, lambda_param=0)
    
    def test_poisson_very_small_lambda(self):
        """Test Poisson with very small lambda."""
        lambda_param = 0.001
        prob = calculate_poisson_probability(0, lambda_param)
        
        # P(X=0) should be very high for tiny lambda
        assert prob > 0.99
    
    def test_poisson_very_large_lambda(self):
        """Test Poisson with very large lambda."""
        lambda_param = 1000
        prob = calculate_poisson_probability(1000, lambda_param)
        
        # Should handle large lambda
        assert 0 < prob < 1
    
    def test_poisson_negative_count(self):
        """Test Poisson with negative count."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_poisson_probability(-1, lambda_param=10)
    
    # ==================== Boundary Conditions ====================
    
    @pytest.mark.parametrize("z_score", [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    def test_rarity_tier_exact_boundaries(self, z_score):
        """Test rarity tier at exact boundaries."""
        tier = classify_rarity_tier(z_score=z_score)
        
        # Should not raise and should return valid tier
        assert tier is not None
    
    # ==================== Data Type Edge Cases ====================
    
    def test_float_vs_int_counts(self):
        """Test handling of float vs int counts."""
        int_data = [10, 20, 30]
        float_data = [10.0, 20.0, 30.0]
        
        z_int = calculate_modified_zscore(int_data)
        z_float = calculate_modified_zscore(float_data)
        
        # Should produce same results
        assert np.allclose(z_int, z_float)
    
    def test_mixed_types(self):
        """Test with mixed numeric types."""
        data = [10, 20.5, 30, 40.25]
        z_scores = calculate_modified_zscore(data)
        
        assert len(z_scores) == 4
    
    # ==================== Concurrent/Parallel Edge Cases ====================
    
    def test_duplicate_values(self):
        """Test with many duplicate values."""
        data = [10, 10, 10, 10, 10, 20]
        z_scores = calculate_modified_zscore(data)
        
        # Should handle duplicates
        assert len(z_scores) == 6
    
    # ==================== Special Statistical Cases ====================
    
    def test_bimodal_distribution(self):
        """Test with bimodal distribution."""
        # Two distinct clusters
        data = [10, 11, 12, 90, 91, 92]
        z_scores = calculate_modified_zscore(data)
        
        # Both clusters should have similar z-scores
        # (median will be between them)
        assert len(z_scores) == 6
    
    def test_highly_skewed_distribution(self):
        """Test with highly skewed distribution."""
        # Right-skewed data
        data = [1, 1, 1, 1, 1, 2, 3, 5, 10, 50]
        z_scores = calculate_modified_zscore(data)
        
        # Should handle skewness
        assert all(np.isfinite(z) for z in z_scores)
```

### 4.2 Edge Case Test Data Fixtures

**Test File:** `tests/fixtures/edge_case_fixtures.py`

```python
import pytest
import numpy as np


@pytest.fixture
def empty_dataset():
    """Empty dataset."""
    return []


@pytest.fixture
def single_value_dataset():
    """Single value dataset."""
    return [42]


@pytest.fixture
def uniform_dataset():
    """Uniform distribution (all same values)."""
    return [10] * 100


@pytest.fixture
def small_sample_dataset():
    """Small sample size (n=5)."""
    return [10, 20, 30, 40, 50]


@pytest.fixture
def dataset_with_extreme_outlier():
    """Dataset with one extreme outlier."""
    normal = list(np.random.normal(100, 10, 99))
    outlier = [10000]
    return normal + outlier


@pytest.fixture
def poisson_low_lambda_data():
    """Poisson data with low lambda."""
    from scipy.stats import poisson
    return poisson.rvs(mu=2, size=100)


@pytest.fixture
def poisson_high_lambda_data():
    """Poisson data with high lambda."""
    from scipy.stats import poisson
    return poisson.rvs(mu=100, size=100)


@pytest.fixture
def bimodal_data():
    """Bimodal distribution."""
    cluster1 = np.random.normal(20, 2, 50)
    cluster2 = np.random.normal(80, 2, 50)
    return list(cluster1) + list(cluster2)


@pytest.fixture
def highly_skewed_data():
    """Highly right-skewed distribution."""
    return list(np.random.exponential(scale=10, size=100))


@pytest.fixture
def zero_inflated_data():
    """Zero-inflated data (many zeros)."""
    data = [0] * 80 + list(np.random.poisson(lam=5, size=20))
    return data
```

---

## 5. Mocking Strategies for Database Queries

### 5.1 Using Dependency Overrides

**Test File:** `tests/integration/test_with_mocks.py`

```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.services.analysis_service import AnalysisService


class TestWithMocking:
    """Tests using FastAPI dependency overrides."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        return session
    
    @pytest.fixture
    def mock_analysis_service(self, mock_db_session):
        """Create a mock analysis service."""
        service = Mock(spec=AnalysisService)
        return service
    
    def test_with_dependency_override(self, mock_analysis_service):
        """Test using FastAPI dependency override."""
        # Override the dependency
        app.dependency_overrides[get_db] = lambda: mock_analysis_service.db
        
        try:
            client = TestClient(app)
            
            # Mock the service method
            mock_analysis_service.analyze_region.return_value = {
                "region_name": "TestRegion",
                "analysis": {
                    "total_observations": 100,
                    "anomalies": []
                }
            }
            
            response = client.get("/regions/TestRegion/analysis")
            
            assert response.status_code == 200
            mock_analysis_service.analyze_region.assert_called_once()
        
        finally:
            # Clean up override
            app.dependency_overrides.clear()
    
    def test_mock_database_query_results(self, mock_db_session):
        """Test mocking database query results."""
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_all = Mock(return_value=[
            Mock(count=10, species_id=1),
            Mock(count=20, species_id=2),
            Mock(count=30, species_id=3),
        ])
        
        mock_filter.all = mock_all
        mock_query.filter = Mock(return_value=mock_filter)
        mock_db_session.query = Mock(return_value=mock_query)
        
        # Use the mock
        service = AnalysisService(mock_db_session)
        result = service.get_species_counts("TestRegion")
        
        assert len(result) == 3
        assert result[0].count == 10
    
    def test_mock_database_aggregation(self, mock_db_session):
        """Test mocking database aggregation."""
        # Mock aggregation result
        mock_result = Mock()
        mock_result.total = 100
        mock_result.mean = 20.0
        mock_result.count = 5
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_result)
        mock_query.filter = Mock(return_value=mock_filter)
        mock_db_session.query = Mock(return_value=mock_query)
        
        service = AnalysisService(mock_db_session)
        result = service.aggregate_counts("TestRegion")
        
        assert result["total"] == 100
        assert result["mean"] == 20.0
```

### 5.2 Using pytest-mock

**Test File:** `tests/unit/test_with_pytest_mock.py`

```python
import pytest
from unittest.mock import MagicMock
from app.services.analysis_service import AnalysisService


class TestWithPytestMock:
    """Tests using pytest-mock for cleaner mocking."""
    
    def test_mock_database_session(self, mocker):
        """Test using pytest-mock to mock database."""
        # Mock the database session
        mock_session = mocker.Mock()
        
        # Mock query results
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mocker.Mock(count=10),
            mocker.Mock(count=20),
            mocker.Mock(count=30),
        ]
        
        service = AnalysisService(mock_session)
        result = service.get_counts("TestRegion")
        
        assert len(result) == 3
    
    def test_mock_external_api_call(self, mocker):
        """Test mocking external API calls."""
        # Mock requests library
        mock_requests = mocker.patch('app.services.external_api.requests.get')
        mock_requests.return_value.json.return_value = {"data": "test"}
        
        # Test code that uses external API
        from app.services.external_api import fetch_species_data
        result = fetch_species_data("species_id")
        
        assert result["data"] == "test"
        mock_requests.assert_called_once()
    
    def test_mock_statistical_calculation(self, mocker):
        """Test mocking statistical calculations."""
        # Mock numpy median calculation
        mock_median = mocker.patch('numpy.median', return_value=50.0)
        
        from app.services.anomaly_detection import calculate_median
        result = calculate_median([10, 20, 30, 40, 100])
        
        assert result == 50.0
        mock_median.assert_called_once()
    
    def test_spy_on_method_call(self, mocker):
        """Test spying on method calls."""
        service = AnalysisService(mocker.Mock())
        
        # Spy on the method
        spy = mocker.spy(service, 'aggregate_counts')
        
        # Call the method
        service.aggregate_counts("TestRegion")
        
        # Verify it was called
        spy.assert_called_once_with("TestRegion")
```

### 5.3 In-Memory Database for Integration Tests

**Test File:** `tests/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture(scope="function")
def db_session():
    """
    Create an in-memory SQLite database for testing.
    This is faster than mocking and provides real database behavior.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with database dependency override.
    """
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_session_with_data(db_session):
    """
    Database session pre-populated with test data.
    """
    from tests.factories import RegionFactory, SpeciesCountFactory
    
    # Create test regions
    regions = [
        RegionFactory(name="RegionA"),
        RegionFactory(name="RegionB"),
        RegionFactory(name="RegionC"),
    ]
    
    for region in regions:
        db_session.add(region)
    db_session.commit()
    
    # Create species counts
    for region in regions:
        SpeciesCountFactory.create_batch(10, region=region)
    
    db_session.commit()
    
    yield db_session
```

---

## 6. Test Data Generation Approaches

### 6.1 Using Factory Boy

**Test File:** `tests/factories.py`

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.database import db
from app.models import Region, SpeciesCount, Species


class RegionFactory(SQLAlchemyModelFactory):
    """Factory for creating Region test data."""
    
    class Meta:
        model = Region
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    name = factory.Sequence(lambda n: f"Region_{n}")
    created_at = factory.Faker("date_time_this_year")


class SpeciesFactory(SQLAlchemyModelFactory):
    """Factory for creating Species test data."""
    
    class Meta:
        model = Species
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    name = factory.Sequence(lambda n: f"Species_{n}")
    scientific_name = factory.LazyAttribute(
        lambda o: f"{o.name.lower()}_scientificus"
    )


class SpeciesCountFactory(SQLAlchemyModelFactory):
    """Factory for creating SpeciesCount test data."""
    
    class Meta:
        model = SpeciesCount
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    region = factory.SubFactory(RegionFactory)
    species = factory.SubFactory(SpeciesFactory)
    count = factory.Faker("pyint", min_value=1, max_value=100)
    recorded_at = factory.Faker("date_time_this_year")
    
    class Params:
        # Presets for common scenarios
        high_count = factory.Trait(count=1000)
        low_count = factory.Trait(count=1)
        outlier_count = factory.Trait(count=10000)


# Usage examples
def test_with_factory_boy(db_session):
    """Test using Factory Boy for test data."""
    # Create a single region
    region = RegionFactory(name="TestRegion")
    
    # Create multiple species counts
    counts = SpeciesCountFactory.create_batch(
        10,
        region=region,
        count=factory.Iterator([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    )
    
    assert len(counts) == 10
    assert all(c.region.name == "TestRegion" for c in counts)
```

### 6.2 Using Faker for Realistic Data

**Test File:** `tests/fixtures/faker_fixtures.py`

```python
import pytest
from faker import Faker
import random

fake = Faker()


@pytest.fixture
def generate_species_name():
    """Generate realistic species names."""
    return f"{fake.first_name()} {fake.last_name()}"


@pytest.fixture
def generate_region_name():
    """Generate realistic region names."""
    return f"{fake.city()} {fake.random_element(['North', 'South', 'East', 'West'])}"


@pytest.fixture
def generate_count_data():
    """Generate realistic count data."""
    def _generate(n=100, include_outliers=False):
        # Generate base counts
        base_mean = random.randint(20, 50)
        base_std = random.randint(5, 15)
        
        counts = [int(random.gauss(base_mean, base_std)) for _ in range(n)]
        counts = [max(0, c) for c in counts]  # Ensure non-negative
        
        if include_outliers:
            # Add some outliers
            outlier_indices = random.sample(range(n), k=3)
            for idx in outlier_indices:
                counts[idx] = random.randint(200, 500)
        
        return counts
    
    return _generate


@pytest.fixture
def generate_time_series_data():
    """Generate time series count data."""
    def _generate(days=30, base_rate=10):
        from datetime import datetime, timedelta
        
        data = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            # Poisson-distributed counts
            count = random.poisson(base_rate)
            data.append({
                "date": date,
                "count": count
            })
        
        return data
    
    return _generate
```

### 6.3 Parametrized Test Data

**Test File:** `tests/unit/test_parametrized_data.py`

```python
import pytest
import numpy as np


# Parametrized test data for statistical methods
statistical_test_data = [
    # (data, expected_median, expected_mad, description)
    ([1, 2, 3, 4, 5], 3, 1, "simple ascending"),
    ([5, 4, 3, 2, 1], 3, 1, "simple descending"),
    ([10, 10, 10, 10, 10], 10, 0, "uniform"),
    ([1, 1, 1, 100, 100, 100], 50.5, 49.5, "bimodal"),
    ([0, 0, 0, 0, 100], 0, 0, "zero-inflated"),
]


@pytest.mark.parametrize("data,expected_median,expected_mad,description", 
                         statistical_test_data)
def test_statistical_calculations_parametrized(
    data, expected_median, expected_mad, description
):
    """Test statistical calculations with various data patterns."""
    from app.services.anomaly_detection import calculate_median, calculate_mad
    
    median = calculate_median(data)
    mad = calculate_mad(data)
    
    assert np.isclose(median, expected_median, rtol=0.01), f"Failed for {description}"
    assert np.isclose(mad, expected_mad, rtol=0.01), f"Failed for {description}"


# Parametrized edge cases
edge_case_data = [
    # (data, should_raise, error_message)
    ([], True, "empty"),
    ([1], True, "at least 2"),
    ([1, 2], False, None),
    ([0, 0, 0], False, None),
    ([-5, -3, -1, 0, 1], False, None),
]


@pytest.mark.parametrize("data,should_raise,error_message", edge_case_data)
def test_edge_cases_parametrized(data, should_raise, error_message):
    """Test edge cases with parametrized data."""
    from app.services.anomaly_detection import calculate_modified_zscore
    
    if should_raise:
        with pytest.raises(ValueError, match=error_message):
            calculate_modified_zscore(data)
    else:
        result = calculate_modified_zscore(data)
        assert len(result) == len(data)
```

### 6.4 Test Data Builders

**Test File:** `tests/builders/test_data_builder.py`

```python
from typing import List, Optional
from datetime import datetime, timedelta
import random


class SpeciesCountDataBuilder:
    """
    Builder pattern for creating test data.
    Provides fluent interface for complex test data setup.
    """
    
    def __init__(self):
        self.counts: List[int] = []
        self.region_name: str = "TestRegion"
        self.species_id: int = 1
        self.start_date: Optional[datetime] = None
        self.with_outliers: bool = False
        self.distribution: str = "normal"
    
    def with_region(self, region_name: str):
        """Set region name."""
        self.region_name = region_name
        return self
    
    def with_species(self, species_id: int):
        """Set species ID."""
        self.species_id = species_id
        return self
    
    def with_normal_distribution(self, mean: int = 50, std: int = 10, n: int = 100):
        """Generate normally distributed counts."""
        self.counts = [
            max(0, int(random.gauss(mean, std))) 
            for _ in range(n)
        ]
        self.distribution = "normal"
        return self
    
    def with_poisson_distribution(self, lambda_param: int = 10, n: int = 100):
        """Generate Poisson distributed counts."""
        self.counts = [
            random.poisson(lambda_param) 
            for _ in range(n)
        ]
        self.distribution = "poisson"
        return self
    
    def with_uniform_distribution(self, low: int = 10, high: int = 100, n: int = 100):
        """Generate uniformly distributed counts."""
        self.counts = [
            random.randint(low, high) 
            for _ in range(n)
        ]
        self.distribution = "uniform"
        return self
    
    def with_outliers(self, n_outliers: int = 3, magnitude: int = 10):
        """Add outliers to the data."""
        self.with_outliers = True
        
        if len(self.counts) > 0:
            # Replace random values with outliers
            outlier_indices = random.sample(
                range(len(self.counts)), 
                min(n_outliers, len(self.counts))
            )
            
            mean_val = np.mean(self.counts)
            for idx in outlier_indices:
                self.counts[idx] = int(mean_val * magnitude)
        
        return self
    
    def with_dates(self, start_date: datetime, days: int = 30):
        """Add date range."""
        self.start_date = start_date
        return self
    
    def build(self) -> dict:
        """Build the final test data."""
        result = {
            "region_name": self.region_name,
            "species_id": self.species_id,
            "counts": self.counts,
            "distribution": self.distribution,
            "has_outliers": self.with_outliers,
        }
        
        if self.start_date:
            dates = [
                self.start_date + timedelta(days=i) 
                for i in range(len(self.counts))
            ]
            result["dates"] = dates
        
        return result


# Usage
def test_with_builder():
    """Test using the builder pattern."""
    data = (SpeciesCountDataBuilder()
        .with_region("TestRegion")
        .with_species(1)
        .with_normal_distribution(mean=50, std=10, n=100)
        .with_outliers(n_outliers=3, magnitude=10)
        .build())
    
    assert len(data["counts"]) == 100
    assert data["has_outliers"] == True
```

---

## 7. Performance Testing Strategies

### 7.1 Using pytest-benchmark

**Test File:** `tests/performance/test_benchmarks.py`

```python
import pytest
import numpy as np
from app.services.anomaly_detection import (
    calculate_modified_zscore,
    calculate_poisson_probability,
    analyze_region
)


class TestPerformanceBenchmarks:
    """Performance benchmarks for statistical methods."""
    
    @pytest.mark.parametrize("size", [100, 1000, 10000, 100000])
    def test_modified_zscore_performance(self, benchmark, size):
        """Benchmark modified z-score calculation."""
        data = np.random.normal(100, 10, size).tolist()
        
        result = benchmark(calculate_modified_zscore, data)
        
        assert len(result) == size
    
    @pytest.mark.parametrize("size", [100, 1000, 10000])
    def test_poisson_calculation_performance(self, benchmark, size):
        """Benchmark Poisson probability calculations."""
        counts = np.random.poisson(10, size).tolist()
        lambda_param = 10
        
        def calculate_all():
            return [calculate_poisson_probability(c, lambda_param) 
                    for c in counts]
        
        result = benchmark(calculate_all)
        assert len(result) == size
    
    def test_database_aggregation_performance(self, benchmark, db_session):
        """Benchmark database aggregation queries."""
        from tests.factories import SpeciesCountFactory, RegionFactory
        
        # Setup: Create 10,000 records
        region = RegionFactory(name="PerfTest")
        SpeciesCountFactory.create_batch(10000, region=region)
        db_session.commit()
        
        from app.services.analysis_service import AnalysisService
        service = AnalysisService(db_session)
        
        result = benchmark(service.aggregate_counts, "PerfTest")
        
        assert result["count"] == 10000
    
    def test_full_analysis_pipeline_performance(self, benchmark, db_session):
        """Benchmark complete analysis pipeline."""
        from tests.factories import SpeciesCountFactory, RegionFactory
        
        # Setup
        region = RegionFactory(name="PipelineTest")
        SpeciesCountFactory.create_batch(1000, region=region)
        db_session.commit()
        
        from app.services.analysis_service import AnalysisService
        service = AnalysisService(db_session)
        
        result = benchmark(service.analyze_region, "PipelineTest")
        
        assert "anomalies" in result
```

### 7.2 Using Locust for Load Testing

**Test File:** `locustfile.py`

```python
from locust import HttpUser, task, between
import random


class AnomalyDetectionUser(HttpUser):
    """
    Simulate users hitting the analysis endpoint.
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    # List of test regions
    regions = ["RegionA", "RegionB", "RegionC", "RegionD", "RegionE"]
    
    @task(10)  # Weight: 10 (most common)
    def get_region_analysis(self):
        """Test the main analysis endpoint."""
        region = random.choice(self.regions)
        self.client.get(f"/regions/{region}/analysis", name="/regions/[name]/analysis")
    
    @task(3)  # Weight: 3 (less common)
    def get_all_regions(self):
        """Test listing all regions."""
        self.client.get("/regions/")
    
    @task(1)  # Weight: 1 (rare)
    def get_nonexistent_region(self):
        """Test 404 response."""
        self.client.get("/regions/NonExistentRegion/analysis", 
                        name="/regions/[name]/analysis [404]")


class StatisticalAnalysisUser(HttpUser):
    """
    Simulate heavy statistical analysis load.
    """
    
    wait_time = between(0.5, 2)
    
    @task
    def intensive_analysis(self):
        """Simulate intensive analysis requests."""
        # Request analysis for multiple regions rapidly
        for region in ["RegionA", "RegionB", "RegionC"]:
            self.client.get(f"/regions/{region}/analysis")
```

**Running Locust:**
```bash
# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run Locust (in another terminal)
locust -f locustfile.py --host http://localhost:8000

# Or run headless for CI/CD
locust -f locustfile.py --host http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m --headless
```

### 7.3 Performance Test Configuration

**Test File:** `tests/performance/conftest.py`

```python
import pytest
import time
from functools import wraps


def measure_time(func):
    """Decorator to measure execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        execution_time = end - start
        print(f"\n{func.__name__} executed in {execution_time:.4f} seconds")
        
        # Assert performance requirement
        assert execution_time < 1.0, f"Too slow: {execution_time:.4f}s > 1.0s"
        
        return result
    return wrapper


@pytest.fixture
def performance_threshold():
    """Maximum acceptable execution time in seconds."""
    return {
        "modified_zscore": 0.1,  # 100ms for 10,000 points
        "poisson_calculation": 0.05,  # 50ms for 1,000 calculations
        "database_aggregation": 0.5,  # 500ms for 10,000 records
        "full_analysis": 2.0,  # 2 seconds for complete pipeline
    }
```

---

## 8. Statistical Validation in Tests

### 8.1 Validating Statistical Properties

**Test File:** `tests/validation/test_statistical_validity.py`

```python
import pytest
import numpy as np
from scipy import stats


class TestStatisticalValidity:
    """Validate statistical properties of calculations."""
    
    def test_modified_zscore_robustness(self):
        """
        Test that modified z-score is robust to outliers.
        Unlike standard z-score, it should not be heavily influenced.
        """
        # Create dataset with outlier
        data_without_outlier = list(np.random.normal(100, 10, 100))
        data_with_outlier = data_without_outlier + [1000]
        
        # Calculate z-scores
        z_without = calculate_modified_zscore(data_without_outlier)
        z_with = calculate_modified_zscore(data_with_outlier)[:-1]  # Exclude outlier
        
        # The z-scores of non-outlier points should be similar
        # (modified z-score is robust)
        correlation = np.corrcoef(z_without, z_with)[0, 1]
        assert correlation > 0.95  # Should be highly correlated
    
    def test_poisson_distribution_properties(self):
        """Test that generated Poisson data has correct properties."""
        from scipy.stats import poisson
        
        lambda_param = 10
        n_samples = 10000
        
        # Generate Poisson data
        data = poisson.rvs(lambda_param, size=n_samples)
        
        # Test mean (should be close to lambda)
        assert np.abs(np.mean(data) - lambda_param) < 0.5
        
        # Test variance (should be close to lambda for Poisson)
        assert np.abs(np.var(data) - lambda_param) < 1.0
        
        # Test using Kolmogorov-Smirnov test
        ks_stat, p_value = stats.kstest(data, 'poisson', args=(lambda_param,))
        assert p_value > 0.05  # Should not reject Poisson hypothesis
    
    def test_mad_calculation_correctness(self):
        """Test MAD calculation against known values."""
        # Test with known distribution
        data = [1, 2, 3, 4, 5]
        mad = calculate_mad(data)
        
        # Manual calculation:
        # median = 3
        # deviations = |1-3|, |2-3|, |3-3|, |4-3|, |5-3| = [2, 1, 0, 1, 2]
        # median of deviations = 1
        expected_mad = 1.0
        
        assert mad == expected_mad
    
    def test_outlier_detection_sensitivity(self):
        """Test sensitivity and specificity of outlier detection."""
        # Generate normal data
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)
        
        # Add known outliers
        outliers = [200, 250, 300]
        data = list(normal_data) + outliers
        
        # Detect outliers
        z_scores = calculate_modified_zscore(data)
        detected_outliers = [
            i for i, z in enumerate(z_scores) 
            if abs(z) > 3.0 and i >= 1000  # Only check added outliers
        ]
        
        # Should detect most outliers
        # (at least 2 out of 3)
        assert len(detected_outliers) >= 2
    
    def test_rarity_tier_distribution(self):
        """Test that rarity tiers follow expected distribution."""
        # Generate normal data
        np.random.seed(42)
        data = np.random.normal(100, 10, 10000)
        
        # Classify into rarity tiers
        z_scores = calculate_modified_zscore(data)
        tiers = [classify_rarity_tier(abs(z)) for z in z_scores]
        
        # Count tiers
        from collections import Counter
        tier_counts = Counter(tiers)
        
        # For normal distribution:
        # - ~68% should be COMMON (|z| < 1)
        # - ~27% should be UNCOMMON (1 < |z| < 2)
        # - ~4% should be RARE (2 < |z| < 3)
        # - ~0.3% should be VERY_RARE (|z| > 3)
        
        total = len(tiers)
        common_pct = tier_counts.get(RarityTier.COMMON, 0) / total
        
        # Should be approximately 68%
        assert 0.60 < common_pct < 0.75
    
    def test_weighted_average_properties(self):
        """Test weighted average calculation properties."""
        counts = [10, 20, 30, 40, 50]
        weights = [1.0, 1.0, 1.0, 1.0, 1.0]
        
        weighted_avg = calculate_weighted_count(counts, weights) / sum(weights)
        
        # With equal weights, should equal simple average
        simple_avg = sum(counts) / len(counts)
        assert np.isclose(weighted_avg, simple_avg)
        
        # Test with different weights
        weights_unequal = [1.0, 2.0, 3.0, 4.0, 5.0]
        weighted_avg_unequal = calculate_weighted_count(counts, weights_unequal) / sum(weights_unequal)
        
        # Should be weighted toward higher counts
        assert weighted_avg_unequal > simple_avg
    
    def test_statistical_power(self):
        """Test that statistical tests have adequate power."""
        # Test power to detect outliers
        # Generate data with known outlier proportion
        n_trials = 100
        detections = 0
        
        for _ in range(n_trials):
            data = list(np.random.normal(100, 10, 100))
            data.append(200)  # Add outlier
            
            z_scores = calculate_modified_zscore(data)
            if abs(z_scores[-1]) > 3.0:
                detections += 1
        
        # Should detect outlier in at least 80% of trials
        power = detections / n_trials
        assert power > 0.80
```

### 8.2 Property-Based Testing with Hypothesis

**Test File:** `tests/property/test_properties.py`

```python
from hypothesis import given, strategies as st, settings, assume
import numpy as np


class TestStatisticalProperties:
    """Property-based tests for statistical methods."""
    
    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=2, max_size=1000))
    @settings(max_examples=100)
    def test_zscore_symmetry(self, data):
        """
        Property: Z-scores should be symmetric around median.
        """
        assume(len(set(data)) > 1)  # Skip uniform data
        
        z_scores = calculate_modified_zscore(data)
        median_idx = np.argsort(data)[len(data) // 2]
        
        # Values above median should have positive z-scores
        # Values below median should have negative z-scores
        for i, (value, z) in enumerate(zip(data, z_scores)):
            if value > data[median_idx]:
                assert z >= 0 or np.isclose(z, 0, atol=0.1)
            elif value < data[median_idx]:
                assert z <= 0 or np.isclose(z, 0, atol=0.1)
    
    @given(st.lists(st.floats(min_value=1, max_value=100), min_size=10, max_size=100))
    @settings(max_examples=50)
    def test_mad_non_negative(self, data):
        """
        Property: MAD should always be non-negative.
        """
        mad = calculate_mad(data)
        assert mad >= 0
    
    @given(
        st.integers(min_value=0, max_value=100),
        st.floats(min_value=0.1, max_value=100)
    )
    def test_poisson_probability_valid(self, k, lambda_param):
        """
        Property: Poisson probability should be between 0 and 1.
        """
        prob = calculate_poisson_probability(k, lambda_param)
        assert 0 <= prob <= 1
    
    @given(st.lists(st.floats(min_value=0, max_value=100), min_size=2, max_size=100))
    @settings(max_examples=50)
    def test_zscore_scale_invariant(self, data):
        """
        Property: Z-scores should be scale-invariant.
        Multiplying all data by constant should give same z-scores.
        """
        assume(len(set(data)) > 1)
        
        z1 = calculate_modified_zscore(data)
        z2 = calculate_modified_zscore([x * 10 for x in data])
        
        # Should be approximately equal
        assert np.allclose(z1, z2, rtol=0.01)
    
    @given(
        st.lists(st.floats(min_value=0, max_value=100), min_size=2),
        st.lists(st.floats(min_value=0.1, max_value=10), min_size=2)
    )
    @settings(max_examples=50)
    def test_weighted_count_monotonic(self, counts, weights):
        """
        Property: Weighted count should be monotonic in weights.
        """
        assume(len(counts) == len(weights))
        
        # Increase one weight, total should increase
        original = calculate_weighted_count(counts, weights)
        
        # Increase first weight
        increased_weights = weights.copy()
        increased_weights[0] *= 2
        increased = calculate_weighted_count(counts, increased_weights)
        
        assert increased >= original
```

---

## 9. Test Organization and Structure

### 9.1 Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── factories.py                   # Factory Boy factories
├── fixtures/
│   ├── edge_case_fixtures.py
│   ├── faker_fixtures.py
│   └── test_data_fixtures.py
├── unit/
│   ├── test_modified_zscore.py
│   ├── test_poisson.py
│   ├── test_weighted_counts.py
│   ├── test_rarity_tier.py
│   └── test_edge_cases.py
├── integration/
│   ├── test_regions_analysis_api.py
│   ├── test_database_aggregations.py
│   └── test_with_mocks.py
├── performance/
│   ├── test_benchmarks.py
│   └── conftest.py
├── validation/
│   └── test_statistical_validity.py
├── property/
│   └── test_properties.py
└── builders/
    └── test_data_builder.py
```

### 9.2 pytest Configuration

**File:** `pytest.ini`

```ini
[pytest]
# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Slow running tests
    edge_case: Edge case tests

# Options
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing
    --cov-report=html

# Test paths
testpaths = tests

# Logging
log_cli = true
log_cli_level = INFO
```

### 9.3 Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m performance

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_modified_zscore.py

# Run specific test
pytest tests/unit/test_modified_zscore.py::TestModifiedZScore::test_modified_zscore_with_outlier

# Run with verbose output
pytest -v

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Run only fast tests
pytest -m "not slow"

# Run edge case tests
pytest -m edge_case

# Generate coverage report
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

### 9.4 CI/CD Configuration

**File:** `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-benchmark
      
      - name: Run unit tests
        run: pytest -m unit --cov=app
      
      - name: Run integration tests
        run: pytest -m integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
      
      - name: Run performance tests
        run: pytest -m performance --benchmark-only
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Summary

### Key Testing Strategies

1. **Unit Tests**: Test statistical methods in isolation with known inputs/outputs
2. **Integration Tests**: Test API endpoints with database interactions
3. **Edge Cases**: Comprehensive coverage of boundary conditions
4. **Mocking**: Use dependency overrides and pytest-mock for isolation
5. **Test Data**: Factory Boy, Faker, and builder patterns for realistic data
6. **Performance**: Benchmark critical paths and load test with Locust
7. **Statistical Validation**: Verify statistical properties and use property-based testing

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage of statistical methods
- **Integration Tests**: All API endpoints and database queries
- **Edge Cases**: All boundary conditions and error cases
- **Performance**: Critical paths under 1 second
- **Statistical Validity**: All statistical properties validated

### Best Practices

1. Use AAA pattern (Arrange-Act-Assert)
2. Parametrize tests for multiple scenarios
3. Use fixtures for reusable test data
4. Mock external dependencies
5. Test both success and failure paths
6. Validate statistical properties
7. Benchmark performance
8. Use property-based testing for robustness

This comprehensive testing strategy ensures your statistical anomaly detection system is reliable, performant, and statistically valid.
