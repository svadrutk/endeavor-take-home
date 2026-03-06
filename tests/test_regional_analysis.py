"""
Tests for Feature 5: Pokémon Rarity & Encounter Rate Analysis.
Tests the regional analysis endpoint for rarity tier analysis and anomaly detection.
"""


class TestRegionalAnalysis:
    """Tests for the regional rarity analysis endpoint."""

    def test_get_regional_analysis_valid_region(self, client, sample_ranger, sample_pokemon):
        """Test getting analysis for a valid region with sightings."""
        pokemon_ids = [25, 1, 4, 144, 151]
        for i, pokemon_id in enumerate(pokemon_ids):
            client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": pokemon_id,
                    "region": "Kanto",
                    "route": f"Route {i + 1}",
                    "date": f"2025-06-{15 + i:02d}T10:30:00",
                    "weather": ["sunny", "rainy", "clear", "foggy", "snowy"][i],
                    "time_of_day": ["morning", "day", "night", "morning", "day"][i],
                    "height": 0.4,
                    "weight": 6.0,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )

        response = client.get(
            "/v1/regions/kanto/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["region"] == "Kanto"
        assert data["total_sightings"] == 5
        assert "rarity_breakdown" in data
        assert "anomalies" in data

        assert "mythical" in data["rarity_breakdown"]
        assert "legendary" in data["rarity_breakdown"]
        assert "rare" in data["rarity_breakdown"]
        assert "uncommon" in data["rarity_breakdown"]
        assert "common" in data["rarity_breakdown"]

        for tier_data in data["rarity_breakdown"].values():
            assert "sighting_count" in tier_data
            assert "percentage" in tier_data
            assert "species" in tier_data

    def test_get_regional_analysis_requires_authentication(self, client):
        """Test that the analysis endpoint requires authentication."""
        response = client.get("/v1/regions/kanto/analysis")
        assert response.status_code == 401

    def test_get_regional_analysis_invalid_region(self, client, sample_ranger):
        """Test getting analysis for an invalid region."""
        response = client.get(
            "/v1/regions/invalid_region/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 404
        assert "Invalid region" in response.json()["detail"]

    def test_get_regional_analysis_empty_region(self, client, sample_ranger):
        """Test getting analysis for a region with no sightings."""
        response = client.get(
            "/v1/regions/sinnoh/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["region"] == "Sinnoh"
        assert data["total_sightings"] == 0
        assert data["anomalies"] == []

        for tier_data in data["rarity_breakdown"].values():
            assert tier_data["sighting_count"] == 0
            assert tier_data["percentage"] == 0.0
            assert tier_data["species"] == []

    def test_get_regional_analysis_rarity_tier_classification(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that Pokemon are correctly classified into rarity tiers."""
        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 151,
                "region": "Johto",
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
                "pokemon_id": 144,
                "region": "Johto",
                "route": "Route 2",
                "date": "2025-06-16T10:30:00",
                "weather": "sunny",
                "time_of_day": "day",
                "height": 1.7,
                "weight": 55.0,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Johto",
                "route": "Route 3",
                "date": "2025-06-17T10:30:00",
                "weather": "rainy",
                "time_of_day": "night",
                "height": 0.4,
                "weight": 6.0,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        response = client.get(
            "/v1/regions/johto/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 200
        data = response.json()

        mythical_species = data["rarity_breakdown"]["mythical"]["species"]
        legendary_species = data["rarity_breakdown"]["legendary"]["species"]
        common_species = data["rarity_breakdown"]["common"]["species"]

        assert any(s["id"] == 151 for s in mythical_species)
        assert any(s["id"] == 144 for s in legendary_species)
        assert any(s["id"] == 25 for s in common_species)

    def test_get_regional_analysis_case_insensitive(self, client, sample_ranger):
        """Test that region names are case-insensitive."""
        response = client.get(
            "/v1/regions/KANTO/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["region"] == "Kanto"

    def test_get_regional_analysis_percentage_calculation(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that percentages are calculated correctly."""
        for i in range(3):
            client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": 25,
                    "region": "Hoenn",
                    "route": f"Route {i + 1}",
                    "date": f"2025-06-{15 + i:02d}T10:30:00",
                    "weather": "sunny",
                    "time_of_day": "morning",
                    "height": 0.4,
                    "weight": 6.0,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )

        for i in range(2):
            client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": 1,
                    "region": "Hoenn",
                    "route": f"Route {i + 4}",
                    "date": f"2025-06-{18 + i:02d}T10:30:00",
                    "weather": "rainy",
                    "time_of_day": "day",
                    "height": 0.7,
                    "weight": 6.9,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )

        response = client.get(
            "/v1/regions/hoenn/analysis", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert response.status_code == 200
        data = response.json()

        total_sightings = data["total_sightings"]
        assert total_sightings == 5

        total_percentage = sum(tier["percentage"] for tier in data["rarity_breakdown"].values())
        assert abs(total_percentage - 100.0) < 0.1
