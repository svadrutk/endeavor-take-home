"""
Tests for Feature 3: Peer Confirmation System.
Tests the peer confirmation functionality for sightings.
"""


class TestCandidateConfirmation:
    """
    Write tests for the peer confirmation system (Feature 3).

    Test that:
    - A ranger can confirm another ranger's sighting
    - A ranger cannot confirm their own sighting
    - A sighting cannot be confirmed more than once
    - Only rangers (not trainers) can confirm sightings
    """

    def test_ranger_can_confirm_another_rangers_sighting(
        self, client, sample_ranger, second_ranger, sample_pokemon
    ):
        sighting = client.post(
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
        assert sighting.status_code == 200
        sighting_id = sighting.json()["id"]

        response = client.post(
            f"/v1/sightings/{sighting_id}/confirm",
            headers={"X-User-ID": second_ranger["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_confirmed"] is True
        assert data["confirmed_by"] == second_ranger["id"]
        assert "confirmed_at" in data

    def test_ranger_cannot_confirm_own_sighting(self, client, sample_ranger, sample_pokemon):
        sighting = client.post(
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
        assert sighting.status_code == 200
        sighting_id = sighting.json()["id"]

        response = client.post(
            f"/v1/sightings/{sighting_id}/confirm",
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 403
        assert "own sighting" in response.json()["detail"].lower()

    def test_sighting_cannot_be_confirmed_twice(
        self, client, sample_ranger, second_ranger, sample_pokemon
    ):
        sighting = client.post(
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
        sighting_id = sighting.json()["id"]

        response1 = client.post(
            f"/v1/sightings/{sighting_id}/confirm",
            headers={"X-User-ID": second_ranger["id"]},
        )
        assert response1.status_code == 200

        third_ranger = client.post(
            "/v1/rangers",
            json={
                "name": "Ranger Brock",
                "email": "brock@pokemon-institute.org",
                "specialization": "Rock",
            },
        )
        response2 = client.post(
            f"/v1/sightings/{sighting_id}/confirm",
            headers={"X-User-ID": third_ranger.json()["id"]},
        )
        assert response2.status_code == 409
        assert "already confirmed" in response2.json()["detail"].lower()

    def test_trainer_cannot_confirm_sightings(
        self, client, sample_trainer, sample_ranger, sample_pokemon
    ):
        sighting = client.post(
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
        sighting_id = sighting.json()["id"]

        response = client.post(
            f"/v1/sightings/{sighting_id}/confirm",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 403
        assert "ranger" in response.json()["detail"].lower()
