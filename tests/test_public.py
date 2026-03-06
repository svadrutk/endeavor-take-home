"""
Public test suite for the PokéTracker API.
"""


# ============================================================
# Trainer & Ranger Registration
# ============================================================


class TestTrainerRegistration:
    def test_create_trainer(self, client):
        response = client.post(
            "/v1/trainers",
            json={
                "name": "Trainer Red",
                "email": "red@pokemon-league.org",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Trainer Red"
        assert data["email"] == "red@pokemon-league.org"
        assert "id" in data

    def test_get_trainer(self, client, sample_trainer):
        response = client.get(f"/v1/trainers/{sample_trainer['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_trainer["name"]

    def test_get_trainer_not_found(self, client):
        response = client.get("/v1/trainers/nonexistent-uuid")
        assert response.status_code == 404


class TestRangerRegistration:
    def test_create_ranger(self, client):
        response = client.post(
            "/v1/rangers",
            json={
                "name": "Ranger Ash",
                "email": "ash@pokemon-institute.org",
                "specialization": "Electric",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ranger Ash"
        assert data["specialization"] == "Electric"
        assert "id" in data

    def test_get_ranger(self, client, sample_ranger):
        response = client.get(f"/v1/rangers/{sample_ranger['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_ranger["name"]

    def test_get_ranger_not_found(self, client):
        response = client.get("/v1/rangers/nonexistent-uuid")
        assert response.status_code == 404


# ============================================================
# User Lookup
# ============================================================


class TestUserLookup:
    def test_lookup_trainer_by_name(self, client, sample_trainer):
        response = client.get("/v1/users/lookup", params={"name": sample_trainer["name"]})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_trainer["id"]
        assert data["role"] == "trainer"

    def test_lookup_ranger_by_name(self, client, sample_ranger):
        response = client.get("/v1/users/lookup", params={"name": sample_ranger["name"]})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_ranger["id"]
        assert data["role"] == "ranger"

    def test_lookup_not_found(self, client):
        response = client.get("/v1/users/lookup", params={"name": "Nobody"})
        assert response.status_code == 404


# ============================================================
# Pokédex
# ============================================================


class TestPokedex:
    def test_list_pokemon(self, client, sample_pokemon):
        response = client.get("/v1/pokedex")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] == len(sample_pokemon)

    def test_get_pokemon_by_id(self, client, sample_pokemon):
        response = client.get("/v1/pokedex/25")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pikachu"
        assert data["type1"] == "Electric"

    def test_get_pokemon_not_found(self, client, sample_pokemon):
        response = client.get("/v1/pokedex/999")
        assert response.status_code == 404

    def test_get_pokemon_by_region(self, client, sample_pokemon):
        response = client.get("/v1/pokedex/region/kanto")
        assert response.status_code == 200
        data = response.json()
        # All sample Gen 1 pokemon
        assert len(data) > 0
        for p in data:
            assert p["generation"] == 1

    def test_search_pokemon(self, client, sample_pokemon):
        response = client.get("/v1/pokedex/search", params={"name": "char"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] >= 1
        assert any(p["name"] == "Charmander" for p in data["results"])


# ============================================================
# Sightings (Basic CRUD)
# ============================================================


class TestSightings:
    def test_create_sighting(self, client, sample_pokemon, sample_ranger):
        response = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 1,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.7,
                "weight": 6.9,
                "is_shiny": False,
                "notes": "Spotted in tall grass",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pokemon_id"] == 1
        assert data["region"] == "Kanto"
        assert data["ranger_id"] == sample_ranger["id"]
        assert data["is_confirmed"] is False

    def test_create_sighting_requires_ranger(self, client, sample_pokemon, sample_trainer):
        """Trainers should not be able to log sightings."""
        response = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 1,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.7,
                "weight": 6.9,
            },
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 403

    def test_create_sighting_requires_auth(self, client, sample_pokemon):
        """Sightings require X-User-ID header."""
        response = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 1,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.7,
                "weight": 6.9,
            },
        )
        assert response.status_code == 401

    def test_create_sighting_invalid_weather(self, client, sample_pokemon, sample_ranger):
        response = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 1,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "tornado",
                "time_of_day": "morning",
                "height": 0.7,
                "weight": 6.9,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 422

    def test_get_sighting(self, client, sample_sighting):
        response = client.get(f"/v1/sightings/{sample_sighting['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_sighting["id"]

    def test_get_sighting_not_found(self, client):
        response = client.get("/v1/sightings/nonexistent-id")
        assert response.status_code == 404

    def test_delete_sighting(self, client, sample_sighting, sample_ranger):
        sighting_id = sample_sighting["id"]
        response = client.delete(
            f"/v1/sightings/{sighting_id}",
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 200

        # Verify it's gone
        response = client.get(f"/v1/sightings/{sighting_id}")
        assert response.status_code == 404

    def test_delete_sighting_wrong_ranger(self, client, sample_sighting, second_ranger):
        """A ranger cannot delete another ranger's sighting."""
        response = client.delete(
            f"/v1/sightings/{sample_sighting['id']}",
            headers={"X-User-ID": second_ranger["id"]},
        )
        assert response.status_code == 403


class TestRangerSightings:
    def test_get_ranger_sightings(self, client, sample_sighting, sample_ranger):
        response = client.get(f"/v1/rangers/{sample_ranger['id']}/sightings")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] >= 1
        assert data["results"][0]["ranger_id"] == sample_ranger["id"]

    def test_get_ranger_sightings_not_found(self, client):
        response = client.get("/v1/rangers/nonexistent-uuid/sightings")
        assert response.status_code == 404


# ============================================================
# Candidate-Written Tests
# ============================================================
#
# INSTRUCTIONS: Write tests for the scenarios described below.
# Each test class has a docstring explaining what you should test.
# You should write at least 2-3 tests per class.
#
# These tests factor into your evaluation — we're looking for:
# - Correct use of the test fixtures (client, sample_pokemon, etc.)
# - Coverage of both happy paths and error cases
# - Assertions that verify meaningful behavior, not just status codes
#
# You may add helper fixtures in conftest.py if needed.


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


class TestCandidateCampaignLifecycle:
    """
    Write tests for the campaign lifecycle (Feature 2).

    Test that:
    - A campaign starts in 'draft' status
    - Transitions move the campaign forward through the lifecycle
    - A sighting can be added to an active campaign
    - A sighting CANNOT be added to a non-active campaign (draft, completed, archived)
    - Sightings tied to a completed campaign are locked (cannot be deleted)
    """

    pass


class TestCandidateConfirmation:
    """
    Write tests for the peer confirmation system (Feature 3).

    Test that:
    - A ranger can confirm another ranger's sighting
    - A ranger cannot confirm their own sighting
    - A sighting cannot be confirmed more than once
    - Only rangers (not trainers) can confirm sightings
    """

    pass
