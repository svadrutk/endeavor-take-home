"""
Tests for Feature 1: Sighting Filters & Pagination.
Tests the GET /sightings endpoint with filtering and pagination support.
"""


class TestCandidateSightingFilters:
    """
    Write tests for the GET /sightings endpoint (Feature 1).

    Test that the endpoint supports:
    - Pagination (limit and offset query params)
    - At least two different filters (e.g., region, weather, pokemon_id)
    - Combining multiple filters narrows results correctly
    - The response includes both the page of results and the total count
    """

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

    def test_multiple_filters(self, client, sample_ranger, second_ranger, sample_pokemon):
        """Test combining multiple filters narrows results correctly."""

        sighting1 = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting1.status_code == 200

        sighting2 = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 4,
                "region": "Johto",
                "route": "Route 29",
                "date": "2025-06-16T14:30:00",
                "weather": "rainy",
                "time_of_day": "day",
                "height": 0.6,
                "weight": 8.5,
            },
            headers={"X-User-ID": second_ranger["id"]},
        )
        assert sighting2.status_code == 200

        response = client.get("/v1/sightings?region=Kanto&weather=sunny")
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

    def test_filter_by_pokemon_id(self, client, sample_sighting):
        """Test filtering by Pokemon ID."""
        response = client.get("/v1/sightings?pokemon_id=25")
        assert response.status_code == 200
        data = response.json()
        assert all(s["pokemon_id"] == 25 for s in data["results"])

    def test_filter_by_ranger_id(self, client, sample_ranger, sample_sighting):
        """Test filtering by Ranger ID."""
        response = client.get(f"/v1/sightings?ranger_id={sample_ranger['id']}")
        assert response.status_code == 200
        data = response.json()
        assert all(s["ranger_id"] == sample_ranger["id"] for s in data["results"])

    def test_filter_by_time_of_day(self, client, sample_sighting):
        """Test filtering by time of day."""
        response = client.get("/v1/sightings?time_of_day=morning")
        assert response.status_code == 200
        data = response.json()
        assert all(s["time_of_day"] == "morning" for s in data["results"])

    def test_filter_by_date_range(self, client, sample_ranger, sample_pokemon):
        """Test filtering by date range."""

        sighting1 = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-01-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting1.status_code == 200

        sighting2 = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 4,
                "region": "Kanto",
                "route": "Route 2",
                "date": "2025-12-15T14:30:00",
                "weather": "rainy",
                "time_of_day": "day",
                "height": 0.6,
                "weight": 8.5,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting2.status_code == 200

        response = client.get(
            "/v1/sightings?date_from=2025-01-01T00:00:00&date_to=2025-06-30T23:59:59"
        )
        assert response.status_code == 200
        data = response.json()
        assert all("2025-01-01" <= s["date"] <= "2025-06-30T23:59:59" for s in data["results"])

    def test_invalid_date_range(self, client):
        """Test that invalid date range returns error."""
        response = client.get(
            "/v1/sightings?date_from=2025-12-31T00:00:00&date_to=2025-01-01T00:00:00"
        )
        assert response.status_code == 400
        assert "date_from must be before or equal to date_to" in response.json()["detail"]

    def test_pagination_offset(self, client, sample_ranger, sample_pokemon):
        """Test that offset works correctly for pagination."""
        for i in range(5):
            response = client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": 25,
                    "region": "Kanto",
                    "route": f"Route {i}",
                    "date": f"2025-06-{15+i:02d}T10:30:00",
                    "weather": "sunny",
                    "time_of_day": "morning",
                    "height": 0.4,
                    "weight": 6.0,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )
            assert response.status_code == 200

        response = client.get("/v1/sightings?limit=2&offset=0")
        assert response.status_code == 200
        page1 = response.json()

        response = client.get("/v1/sightings?limit=2&offset=2")
        assert response.status_code == 200
        page2 = response.json()

        assert len(page1["results"]) == 2
        assert len(page2["results"]) == 2
        assert page1["results"][0]["id"] != page2["results"][0]["id"]

    def test_response_structure(self, client, sample_sighting):
        """Test that response has correct structure."""
        response = client.get("/v1/sightings")
        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "id" in result
            assert "pokemon_id" in result
            assert "ranger_id" in result
            assert "region" in result
            assert "route" in result
            assert "date" in result
            assert "weather" in result
            assert "time_of_day" in result
            assert "height" in result
            assert "weight" in result
            assert "is_shiny" in result
            assert "is_confirmed" in result
            assert "pokemon_name" in result
            assert "ranger_name" in result
