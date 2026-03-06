"""
Tests for Feature 4: Regional Research Summary.
Tests the regional summary endpoint for research activity analysis.
"""


class TestRegionalSummary:
    """Tests for the regional research summary endpoint."""

    def test_get_regional_summary_valid_region(self, client, sample_ranger, sample_pokemon):
        """Test getting summary for a valid region with sightings."""
        pokemon_ids = [25, 1, 4]
        for i, pokemon_id in enumerate(pokemon_ids):
            client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": pokemon_id,
                    "region": "Kanto",
                    "route": f"Route {i+1}",
                    "date": f"2025-06-{15+i:02d}T10:30:00",
                    "weather": ["sunny", "rainy", "clear"][i],
                    "time_of_day": ["morning", "day", "night"][i],
                    "height": 0.4,
                    "weight": 6.0,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )

        response = client.get("/v1/regions/kanto/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["region"] == "Kanto"
        assert data["total_sightings"] == 3
        assert data["confirmed_sightings"] == 0
        assert data["unconfirmed_sightings"] == 3
        assert data["unique_species"] == 3
        assert len(data["top_pokemon"]) <= 5
        assert len(data["top_rangers"]) <= 5
        assert "sunny" in data["weather_breakdown"]
        assert "morning" in data["time_of_day_breakdown"]

    def test_get_regional_summary_invalid_region(self, client):
        """Test getting summary for an invalid region."""
        response = client.get("/v1/regions/invalid_region/summary")
        assert response.status_code == 404
        assert "Invalid region" in response.json()["detail"]

    def test_get_regional_summary_empty_region(self, client):
        """Test getting summary for a region with no sightings."""
        response = client.get("/v1/regions/sinnoh/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["region"] == "Sinnoh"
        assert data["total_sightings"] == 0
        assert data["confirmed_sightings"] == 0
        assert data["unconfirmed_sightings"] == 0
        assert data["unique_species"] == 0
        assert data["top_pokemon"] == []
        assert data["top_rangers"] == []
        assert data["weather_breakdown"] == {}
        assert data["time_of_day_breakdown"] == {}

    def test_get_regional_summary_case_insensitive(self, client):
        """Test that region names are case-insensitive."""
        response = client.get("/v1/regions/KANTO/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["region"] == "Kanto"

    def test_get_regional_summary_with_confirmed_sightings(self, client, sample_pokemon):
        """Test that confirmed sightings are counted correctly."""
        ranger1 = client.post(
            "/v1/rangers",
            json={"name": "Ranger1", "email": "ranger1@test.com", "specialization": "Electric"},
        )
        ranger2 = client.post(
            "/v1/rangers",
            json={"name": "Ranger2", "email": "ranger2@test.com", "specialization": "Fire"},
        )

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Johto",
                "route": "Route 1",
                "date": "2025-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
            },
            headers={"X-User-ID": ranger1.json()["id"]},
        )

        client.post(
            f"/v1/sightings/{sighting.json()['id']}/confirm",
            headers={"X-User-ID": ranger2.json()["id"]},
        )

        response = client.get("/v1/regions/johto/summary")
        assert response.status_code == 200
        data = response.json()

        assert data["total_sightings"] == 1
        assert data["confirmed_sightings"] == 1
        assert data["unconfirmed_sightings"] == 0
