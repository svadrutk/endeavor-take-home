"""
Tests for Feature 2: Research Campaigns.
Tests campaign lifecycle, state transitions, and sighting associations.
"""


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

    def test_campaign_starts_in_draft_status(self, client, sample_ranger):
        """Test that a newly created campaign starts in 'draft' status."""
        response = client.post(
            "/v1/campaigns",
            json={
                "name": "Cerulean Cave Survey",
                "description": "Researching rare Pokémon in Cerulean Cave",
                "region": "Kanto",
                "start_date": "2026-02-01T00:00:00",
                "end_date": "2026-02-28T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert data["name"] == "Cerulean Cave Survey"
        assert data["region"] == "Kanto"

    def test_valid_state_transitions(self, client, sample_ranger):
        """Test that valid state transitions work correctly."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Johto Migration Study",
                "region": "Johto",
                "start_date": "2026-03-01T00:00:00",
                "end_date": "2026-03-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        response = client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")
        assert response.status_code == 200
        assert response.json()["status"] == "active"

        response = client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=archived")
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

    def test_invalid_state_transitions_rejected(self, client, sample_ranger):
        """Test that invalid state transitions are rejected."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Invalid Transition Test",
                "region": "Hoenn",
                "start_date": "2026-04-01T00:00:00",
                "end_date": "2026-04-30T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        response = client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")
        assert response.status_code == 400
        assert "Cannot transition" in response.json()["detail"]

    def test_sighting_can_be_added_to_active_campaign(self, client, sample_ranger, sample_pokemon):
        """Test that a sighting can be added to an active campaign."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Active Campaign Test",
                "region": "Kanto",
                "start_date": "2026-05-01T00:00:00",
                "end_date": "2026-05-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2026-05-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 200
        assert sighting.json()["campaign_id"] == campaign_id

    def test_sighting_cannot_be_added_to_non_active_campaign(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that a sighting cannot be added to a draft campaign."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Draft Campaign Test",
                "region": "Kanto",
                "start_date": "2026-06-01T00:00:00",
                "end_date": "2026-06-30T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2026-06-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 400
        assert "Only active campaigns can accept new sightings" in sighting.json()["detail"]

    def test_completed_campaign_locks_sightings(self, client, sample_ranger, sample_pokemon):
        """Test that sightings tied to a completed campaign cannot be deleted."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Completed Campaign Lock Test",
                "region": "Kanto",
                "start_date": "2026-07-01T00:00:00",
                "end_date": "2026-07-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2026-07-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 200
        sighting_id = sighting.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")

        delete_response = client.delete(
            f"/v1/sightings/{sighting_id}", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert delete_response.status_code == 403
        assert "locked" in delete_response.json()["detail"].lower()

    def test_campaign_summary(self, client, sample_ranger, sample_pokemon):
        """Test that campaign summary returns correct aggregated data."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Summary Test Campaign",
                "region": "Kanto",
                "start_date": "2026-08-01T00:00:00",
                "end_date": "2026-08-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        for i in range(3):
            client.post(
                "/v1/sightings",
                json={
                    "pokemon_id": 25,
                    "region": "Kanto",
                    "route": f"Route {i}",
                    "date": f"2026-08-{15 + i:02d}T10:30:00",
                    "weather": "sunny",
                    "time_of_day": "morning",
                    "height": 0.4,
                    "weight": 6.0,
                    "campaign_id": campaign_id,
                },
                headers={"X-User-ID": sample_ranger["id"]},
            )

        summary = client.get(f"/v1/campaigns/{campaign_id}/summary")
        assert summary.status_code == 200
        data = summary.json()
        assert data["campaign_id"] == campaign_id
        assert data["total_sightings"] == 3
        assert data["unique_species"] == 1
        assert len(data["contributing_rangers"]) == 1
        assert data["contributing_rangers"][0]["name"] == sample_ranger["name"]

    def test_get_campaign_details(self, client, sample_ranger):
        """Test retrieving campaign details by ID."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Get Campaign Test",
                "description": "Test description",
                "region": "Sinnoh",
                "start_date": "2026-09-01T00:00:00",
                "end_date": "2026-09-30T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        response = client.get(f"/v1/campaigns/{campaign_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == campaign_id
        assert data["name"] == "Get Campaign Test"
        assert data["description"] == "Test description"
        assert data["region"] == "Sinnoh"
        assert data["status"] == "draft"

    def test_get_campaign_not_found(self, client):
        """Test that getting a non-existent campaign returns 404."""
        response = client.get("/v1/campaigns/nonexistent-campaign-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_campaign_metadata(self, client, sample_ranger):
        """Test updating campaign metadata via PATCH."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Original Name",
                "description": "Original description",
                "region": "Kanto",
                "start_date": "2026-10-01T00:00:00",
                "end_date": "2026-10-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        update_response = client.patch(
            f"/v1/campaigns/{campaign_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["region"] == "Kanto"

    def test_sighting_cannot_be_added_to_completed_campaign(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that a sighting cannot be added to a completed campaign."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Completed Campaign Test",
                "region": "Kanto",
                "start_date": "2026-11-01T00:00:00",
                "end_date": "2026-11-30T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")
        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2026-11-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 400
        assert "Only active campaigns can accept new sightings" in sighting.json()["detail"]

    def test_sighting_cannot_be_added_to_archived_campaign(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that a sighting cannot be added to an archived campaign."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Archived Campaign Test",
                "region": "Kanto",
                "start_date": "2026-12-01T00:00:00",
                "end_date": "2026-12-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")
        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")
        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=archived")

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2026-12-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 400
        assert "Only active campaigns can accept new sightings" in sighting.json()["detail"]

    def test_completed_campaign_sightings_cannot_be_deleted(
        self, client, sample_ranger, sample_pokemon
    ):
        """Test that sightings tied to a completed campaign cannot be deleted."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Delete Lock Test",
                "region": "Kanto",
                "start_date": "2027-01-01T00:00:00",
                "end_date": "2027-01-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        sighting = client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2027-01-15T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert sighting.status_code == 200
        sighting_id = sighting.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")

        delete_response = client.delete(
            f"/v1/sightings/{sighting_id}", headers={"X-User-ID": sample_ranger["id"]}
        )
        assert delete_response.status_code == 403
        assert "locked" in delete_response.json()["detail"].lower()

    def test_campaign_summary_includes_date_range(self, client, sample_ranger, sample_pokemon):
        """Test that campaign summary includes date range of actual observations."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Date Range Test",
                "region": "Kanto",
                "start_date": "2027-02-01T00:00:00",
                "end_date": "2027-02-28T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2027-02-05T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 4,
                "region": "Kanto",
                "route": "Route 2",
                "date": "2027-02-20T14:30:00",
                "weather": "rainy",
                "time_of_day": "day",
                "height": 0.6,
                "weight": 8.5,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        summary = client.get(f"/v1/campaigns/{campaign_id}/summary")
        assert summary.status_code == 200
        data = summary.json()
        assert "observation_date_range" in data
        assert data["observation_date_range"]["start"] == "2027-02-05T10:30:00"
        assert data["observation_date_range"]["end"] == "2027-02-20T14:30:00"

    def test_create_campaign_requires_authentication(self, client):
        """Test that creating a campaign requires X-User-ID header."""
        response = client.post(
            "/v1/campaigns",
            json={
                "name": "Unauthorized Campaign",
                "region": "Kanto",
                "start_date": "2027-03-01T00:00:00",
                "end_date": "2027-03-31T23:59:59",
            },
        )
        assert response.status_code == 401
        assert "X-User-ID" in response.json()["detail"]

    def test_trainer_cannot_create_campaign(self, client, sample_trainer):
        """Test that trainers cannot create campaigns (only rangers can)."""
        response = client.post(
            "/v1/campaigns",
            json={
                "name": "Trainer Campaign",
                "region": "Kanto",
                "start_date": "2027-04-01T00:00:00",
                "end_date": "2027-04-30T23:59:59",
            },
            headers={"X-User-ID": sample_trainer["id"]},
        )
        assert response.status_code == 403
        assert "ranger" in response.json()["detail"].lower()

    def test_campaign_summary_not_found(self, client):
        """Test that getting summary for non-existent campaign returns 404."""
        response = client.get("/v1/campaigns/nonexistent-id/summary")
        assert response.status_code == 404

    def test_transition_campaign_not_found(self, client):
        """Test that transitioning non-existent campaign returns 404."""
        response = client.post("/v1/campaigns/nonexistent-id/transition?new_status=active")
        assert response.status_code == 404

    def test_update_campaign_not_found(self, client):
        """Test that updating non-existent campaign returns 404."""
        response = client.patch(
            "/v1/campaigns/nonexistent-id",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    def test_backward_transition_rejected(self, client, sample_ranger):
        """Test that campaigns cannot move backward in lifecycle."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Backward Transition Test",
                "region": "Kanto",
                "start_date": "2027-05-01T00:00:00",
                "end_date": "2027-05-31T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")
        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=completed")

        response = client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")
        assert response.status_code == 400
        assert "Cannot transition" in response.json()["detail"]

    def test_campaign_summary_with_multiple_rangers(
        self, client, sample_ranger, second_ranger, sample_pokemon
    ):
        """Test that campaign summary correctly tracks multiple contributing rangers."""
        campaign = client.post(
            "/v1/campaigns",
            json={
                "name": "Multi-Ranger Campaign",
                "region": "Kanto",
                "start_date": "2027-06-01T00:00:00",
                "end_date": "2027-06-30T23:59:59",
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )
        assert campaign.status_code == 201
        campaign_id = campaign.json()["id"]

        client.post(f"/v1/campaigns/{campaign_id}/transition?new_status=active")

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 25,
                "region": "Kanto",
                "route": "Route 1",
                "date": "2027-06-10T10:30:00",
                "weather": "sunny",
                "time_of_day": "morning",
                "height": 0.4,
                "weight": 6.0,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": sample_ranger["id"]},
        )

        client.post(
            "/v1/sightings",
            json={
                "pokemon_id": 4,
                "region": "Kanto",
                "route": "Route 2",
                "date": "2027-06-15T14:30:00",
                "weather": "rainy",
                "time_of_day": "day",
                "height": 0.6,
                "weight": 8.5,
                "campaign_id": campaign_id,
            },
            headers={"X-User-ID": second_ranger["id"]},
        )

        summary = client.get(f"/v1/campaigns/{campaign_id}/summary")
        assert summary.status_code == 200
        data = summary.json()
        assert data["total_sightings"] == 2
        assert data["unique_species"] == 2
        assert len(data["contributing_rangers"]) == 2
        ranger_names = [r["name"] for r in data["contributing_rangers"]]
        assert sample_ranger["name"] in ranger_names
        assert second_ranger["name"] in ranger_names
