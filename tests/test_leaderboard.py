"""
Tests for Feature 6: Ranger Leaderboard.
Tests the leaderboard endpoint with filtering, sorting, and pagination.
"""


class TestCandidateLeaderboard:
    def test_global_leaderboard(self, client, sample_ranger, sample_sighting):
        """Test global leaderboard returns all rangers with sightings."""
        response = client.get("/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

        entry = data["results"][0]
        assert "rank" in entry
        assert "ranger_id" in entry
        assert "ranger_name" in entry
        assert "total_sightings" in entry
        assert "confirmed_sightings" in entry
        assert "unique_species" in entry
        assert "rarest_pokemon" in entry

    def test_filter_by_region(self, client, sample_ranger, sample_pokemon):
        """Test region filter works correctly."""
        client.post(
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

        response = client.get("/v1/leaderboard?region=Kanto")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_filter_by_date_range(self, client, sample_ranger, sample_pokemon):
        """Test date range filter works correctly."""
        client.post(
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

        response = client.get("/v1/leaderboard?date_from=2025-06-01&date_to=2025-06-30")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_sort_by_confirmed_sightings(
        self, client, sample_ranger, second_ranger, sample_pokemon
    ):
        """Test sorting by confirmed_sightings."""
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

        client.post(
            f"/v1/sightings/{sighting1.json()['id']}/confirm",
            headers={"X-User-ID": second_ranger["id"]},
        )

        response = client.get("/v1/leaderboard?sort_by=confirmed_sightings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

    def test_sort_by_unique_species(self, client, sample_ranger, sample_pokemon):
        """Test sorting by unique_species."""
        client.post(
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

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 4,
                "region": "Kanto",
                "route": "Route 2",
                "date": "2025-06-16T14:30:00",
                "weather": "rainy",
                "time_of_day": "day",
                "height": 0.6,
                "weight": 8.5,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        response = client.get("/v1/leaderboard?sort_by=unique_species")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_pagination(self, client, sample_ranger, sample_sighting):
        """Test pagination with limit and offset."""
        response = client.get("/v1/leaderboard?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["results"]) <= 10

    def test_invalid_region(self, client):
        """Test invalid region returns 400."""
        response = client.get("/v1/leaderboard?region=InvalidRegion")
        assert response.status_code == 400
        assert "Invalid region" in response.json()["detail"]

    def test_invalid_date_range(self, client):
        """Test invalid date range returns 400."""
        response = client.get("/v1/leaderboard?date_from=2025-06-30&date_to=2025-06-01")
        assert response.status_code == 400
        assert "date_from must be before" in response.json()["detail"]

    def test_empty_results(self, client):
        """Test that filtering with no matches returns empty results."""
        response = client.get(
            "/v1/leaderboard?region=Kanto&date_from=2020-01-01&date_to=2020-01-31"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_rarest_pokemon_included(self, client, sample_ranger, sample_pokemon):
        """Test that rarest_pokemon is included in response."""
        client.post(
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

        response = client.get("/v1/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        entry = data["results"][0]
        if entry["rarest_pokemon"]:
            assert "pokemon_id" in entry["rarest_pokemon"]
            assert "pokemon_name" in entry["rarest_pokemon"]
            assert "rarity_score" in entry["rarest_pokemon"]
            assert "is_shiny" in entry["rarest_pokemon"]
            assert "date" in entry["rarest_pokemon"]

    def test_case_insensitive_region(self, client, sample_ranger, sample_pokemon):
        """Test that region filter is case-insensitive."""
        client.post(
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

        response = client.get("/v1/leaderboard?region=kanto")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_limit_validation(self, client):
        """Test that limit is validated."""
        response = client.get("/v1/leaderboard?limit=300")
        assert response.status_code == 422

    def test_offset_validation(self, client):
        """Test that offset is validated."""
        response = client.get("/v1/leaderboard?offset=15000")
        assert response.status_code == 422
