"""
Tests for identity and user lookup endpoints.
Covers trainer/ranger registration and user lookup functionality.
"""


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
