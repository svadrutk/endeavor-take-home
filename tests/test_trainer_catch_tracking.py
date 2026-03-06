"""
Tests for Trainer Pokédex catch tracking functionality.
"""


class TestTrainerCatchTracking:
    def test_trainer_can_mark_pokemon_as_caught(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        response = client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pokemon_id"] == pokemon_id
        assert data["pokemon_name"] == "Pikachu"
        assert "caught_at" in data

    def test_trainer_can_unmark_pokemon(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )

        response = client.delete(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 200
        assert "removed from catch log" in response.json()["detail"]

    def test_duplicate_catch_prevention(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )

        response = client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()

    def test_catch_log_retrieval(self, client, sample_trainer, sample_pokemon):
        pokemon_ids = [1, 4, 7]
        for pid in pokemon_ids:
            client.post(
                f"/v1/trainers/{sample_trainer['id']}/pokedex/{pid}",
                headers={"X-User-ID": sample_trainer["id"]},
            )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex")
        assert response.status_code == 200
        data = response.json()
        assert data["trainer_id"] == sample_trainer["id"]
        assert data["trainer_name"] == sample_trainer["name"]
        assert len(data["catches"]) == 3
        assert data["total"] == 3

    def test_catch_summary_calculations(self, client, sample_trainer, sample_pokemon):
        pokemon_ids = [1, 4, 7, 25]
        for pid in pokemon_ids:
            client.post(
                f"/v1/trainers/{sample_trainer['id']}/pokedex/{pid}",
                headers={"X-User-ID": sample_trainer["id"]},
            )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["trainer_id"] == sample_trainer["id"]
        assert data["total_caught"] == 4
        assert data["completion_percentage"] == round((4 / 493) * 100, 2)
        assert "caught_by_type" in data
        assert "caught_by_generation" in data

    def test_authorization_only_owner_can_modify(self, client, sample_pokemon):
        response = client.post(
            "/v1/trainers", json={"name": "Trainer Blue", "email": "blue@pokemon-league.org"}
        )
        trainer1 = response.json()

        response = client.post(
            "/v1/trainers", json={"name": "Trainer Green", "email": "green@pokemon-league.org"}
        )
        trainer2 = response.json()

        pokemon_id = 25
        response = client.post(
            f"/v1/trainers/{trainer1['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": trainer2["id"]},
        )
        assert response.status_code == 403
        assert "permission denied" in response.json()["detail"].lower()

    def test_pokedex_endpoint_with_trainer_user_id(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )

        response = client.get(
            f"/v1/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pokemon_id
        assert data["is_caught"] is True

    def test_pokedex_endpoint_without_user_id(self, client, sample_pokemon):
        pokemon_id = 25
        response = client.get(f"/v1/pokedex/{pokemon_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pokemon_id
        assert "is_caught" not in data or data.get("is_caught") is None

    def test_pokedex_endpoint_with_ranger_user_id(self, client, sample_ranger, sample_pokemon):
        pokemon_id = 25
        response = client.get(
            f"/v1/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pokemon_id
        assert "is_caught" not in data or data.get("is_caught") is None

    def test_ranger_cannot_use_catch_tracking(self, client, sample_ranger, sample_pokemon):
        pokemon_id = 25
        response = client.post(
            f"/v1/trainers/{sample_ranger['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 403
        assert "only pokémon trainers" in response.json()["detail"].lower()

    def test_mark_nonexistent_pokemon(self, client, sample_trainer):
        pokemon_id = 999
        response = client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unmark_non_caught_pokemon(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        response = client.delete(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 404
        assert "not in" in response.json()["detail"].lower()

    def test_public_access_to_catch_log(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex")
        assert response.status_code == 200
        data = response.json()
        assert len(data["catches"]) == 1

    def test_public_access_to_catch_summary(self, client, sample_trainer, sample_pokemon):
        pokemon_id = 25
        client.post(
            f"/v1/trainers/{sample_trainer['id']}/pokedex/{pokemon_id}",
            headers={"X-User-ID": sample_trainer["id"]},
        )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_caught"] == 1

    def test_empty_catch_log(self, client, sample_trainer):
        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex")
        assert response.status_code == 200
        data = response.json()
        assert len(data["catches"]) == 0
        assert data["total"] == 0

    def test_catch_log_pagination(self, client, sample_trainer, sample_pokemon):
        pokemon_ids = [1, 4, 7, 25, 144, 150, 151, 152, 175]
        for pid in pokemon_ids:
            client.post(
                f"/v1/trainers/{sample_trainer['id']}/pokedex/{pid}",
                headers={"X-User-ID": sample_trainer["id"]},
            )

        response = client.get(
            f"/v1/trainers/{sample_trainer['id']}/pokedex",
            params={"limit": 5, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["catches"]) == 5
        assert data["total"] == 9

        response = client.get(
            f"/v1/trainers/{sample_trainer['id']}/pokedex",
            params={"limit": 5, "offset": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["catches"]) == 4

    def test_catch_summary_by_type(self, client, sample_trainer, sample_pokemon):
        pokemon_ids = [1, 4, 7]
        for pid in pokemon_ids:
            client.post(
                f"/v1/trainers/{sample_trainer['id']}/pokedex/{pid}",
                headers={"X-User-ID": sample_trainer["id"]},
            )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex/summary")
        assert response.status_code == 200
        data = response.json()
        assert "caught_by_type" in data
        assert data["caught_by_type"]["Grass"] == 1
        assert data["caught_by_type"]["Fire"] == 1
        assert data["caught_by_type"]["Water"] == 1

    def test_catch_summary_by_generation(self, client, sample_trainer, sample_pokemon):
        pokemon_ids = [1, 4, 7, 152]
        for pid in pokemon_ids:
            client.post(
                f"/v1/trainers/{sample_trainer['id']}/pokedex/{pid}",
                headers={"X-User-ID": sample_trainer["id"]},
            )

        response = client.get(f"/v1/trainers/{sample_trainer['id']}/pokedex/summary")
        assert response.status_code == 200
        data = response.json()
        assert "caught_by_generation" in data
        assert (
            data["caught_by_generation"].get("1") == 3 or data["caught_by_generation"].get(1) == 3
        )
        assert (
            data["caught_by_generation"].get("2") == 1 or data["caught_by_generation"].get(2) == 1
        )

    def test_nonexistent_trainer_catch_log(self, client):
        response = client.get("/v1/trainers/nonexistent-uuid/pokedex")
        assert response.status_code == 404

    def test_nonexistent_trainer_catch_summary(self, client):
        response = client.get("/v1/trainers/nonexistent-uuid/pokedex/summary")
        assert response.status_code == 404
