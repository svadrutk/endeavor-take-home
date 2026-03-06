"""
Tests for basic sightings CRUD operations.
Covers sighting creation, retrieval, deletion, and ranger sightings listing.
"""


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
