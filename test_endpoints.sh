#!/bin/bash

BASE_URL="http://localhost:8000/v1"

echo "=========================================="
echo "TESTING ALL ENDPOINTS AGAINST REQUIREMENTS"
echo "=========================================="
echo ""

# Create test users
echo "Creating test users..."
TRAINER_ID=$(curl -s -X POST $BASE_URL/trainers/ -H "Content-Type: application/json" -d '{"name": "TestTrainer123", "email": "testtrainer123@example.com"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
RANGER_ID=$(curl -s -X POST $BASE_URL/rangers/ -H "Content-Type: application/json" -d '{"name": "TestRanger123", "email": "testranger123@example.com", "specialization": "Fire"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
RANGER_ID2=$(curl -s -X POST $BASE_URL/rangers/ -H "Content-Type: application/json" -d '{"name": "TestRanger456", "email": "testranger456@example.com", "specialization": "Water"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Trainer ID: $TRAINER_ID"
echo "Ranger ID: $RANGER_ID"
echo "Ranger ID2: $RANGER_ID2"
echo ""

echo "=========================================="
echo "1. IDENTITY & LOOKUP ENDPOINTS"
echo "=========================================="
echo ""

echo "1.1 POST /trainers - Register new Trainer"
curl -s -X POST $BASE_URL/trainers/ -H "Content-Type: application/json" -d '{"name": "NewTrainer", "email": "newtrainer@example.com"}' | python3 -m json.tool
echo ""

echo "1.2 POST /rangers - Register new Ranger"
curl -s -X POST $BASE_URL/rangers/ -H "Content-Type: application/json" -d '{"name": "NewRanger", "email": "newranger@example.com", "specialization": "Electric"}' | python3 -m json.tool
echo ""

echo "1.3 GET /users/lookup?name=TestTrainer123"
curl -s "$BASE_URL/users/lookup?name=TestTrainer123" | python3 -m json.tool
echo ""

echo "1.4 GET /trainers/{trainer_id}"
curl -s "$BASE_URL/trainers/$TRAINER_ID" | python3 -m json.tool
echo ""

echo "1.5 GET /rangers/{ranger_id}"
curl -s "$BASE_URL/rangers/$RANGER_ID" | python3 -m json.tool
echo ""

echo "=========================================="
echo "2. RANGERS & SIGHTINGS"
echo "=========================================="
echo ""

echo "2.1 GET /rangers/{ranger_id}/sightings"
curl -s "$BASE_URL/rangers/$RANGER_ID/sightings" | python3 -m json.tool
echo ""

echo "=========================================="
echo "3. POKEMON SPECIES (REFERENCE DATA)"
echo "=========================================="
echo ""

echo "3.1 GET /pokedex - List all Pokemon species"
curl -s "$BASE_URL/pokedex/" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Total species: {len(data)}\"); print(f\"First species: {data[0] if data else 'None'}\")"
echo ""

echo "3.2 GET /pokedex/{pokemon_id} - Get specific species"
curl -s "$BASE_URL/pokedex/1" | python3 -m json.tool
echo ""

echo "3.3 GET /pokedex/region/{region_name} - Get Pokemon by region"
curl -s "$BASE_URL/pokedex/region/Kanto" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Kanto Pokemon count: {len(data)}\"); print(f\"First: {data[0] if data else 'None'}\")"
echo ""

echo "3.4 GET /pokedex/search - Search species by name"
curl -s "$BASE_URL/pokedex/search?name=pikachu" | python3 -m json.tool
echo ""

echo "=========================================="
echo "4. SIGHTINGS"
echo "=========================================="
echo ""

echo "4.1 POST /sightings - Log new sighting"
SIGHTING_RESPONSE=$(curl -s -X POST $BASE_URL/sightings/ -H "Content-Type: application/json" -H "X-User-ID: $RANGER_ID" -d '{
  "pokemon_id": 25,
  "height": 0.4,
  "weight": 6.0,
  "shiny": false,
  "region": "Kanto",
  "location": "Route 1",
  "weather": "sunny",
  "time_of_day": "day",
  "notes": "Test sighting"
}')
echo "$SIGHTING_RESPONSE" | python3 -m json.tool
SIGHTING_ID=$(echo "$SIGHTING_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
echo "Sighting ID: $SIGHTING_ID"
echo ""

echo "4.2 GET /sightings/{sighting_id}"
curl -s "$BASE_URL/sightings/$SIGHTING_ID" | python3 -m json.tool
echo ""

echo "4.3 DELETE /sightings/{sighting_id}"
curl -s -X DELETE "$BASE_URL/sightings/$SIGHTING_ID" -H "X-User-ID: $RANGER_ID"
echo "Deleted sighting"
echo ""

echo "=========================================="
echo "5. FEATURE 1: SIGHTING FILTERS & PAGINATION"
echo "=========================================="
echo ""

echo "5.1 GET /sightings with filters"
curl -s "$BASE_URL/sightings/?pokemon_id=25&region=Kanto&limit=10&offset=0" | python3 -m json.tool
echo ""

echo "5.2 GET /sightings with date range"
curl -s "$BASE_URL/sightings/?date_from=2020-01-01&date_to=2026-12-31&limit=5" | python3 -m json.tool
echo ""

echo "=========================================="
echo "6. FEATURE 2: RESEARCH CAMPAIGNS"
echo "=========================================="
echo ""

echo "6.1 POST /campaigns - Create campaign"
CAMPAIGN_RESPONSE=$(curl -s -X POST $BASE_URL/campaigns/ -H "Content-Type: application/json" -d '{
  "name": "Kanto Survey 2026",
  "description": "Annual Kanto region survey",
  "region": "Kanto",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31"
}')
echo "$CAMPAIGN_RESPONSE" | python3 -m json.tool
CAMPAIGN_ID=$(echo "$CAMPAIGN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
echo "Campaign ID: $CAMPAIGN_ID"
echo ""

echo "6.2 GET /campaigns/{campaign_id}"
curl -s "$BASE_URL/campaigns/$CAMPAIGN_ID" | python3 -m json.tool
echo ""

echo "6.3 PATCH /campaigns/{campaign_id}"
curl -s -X PATCH "$BASE_URL/campaigns/$CAMPAIGN_ID" -H "Content-Type: application/json" -d '{"description": "Updated description"}' | python3 -m json.tool
echo ""

echo "6.4 POST /campaigns/{campaign_id}/transition - Move to active"
curl -s -X POST "$BASE_URL/campaigns/$CAMPAIGN_ID/transition" -H "Content-Type: application/json" -d '{"status": "active"}' | python3 -m json.tool
echo ""

echo "6.5 GET /campaigns/{campaign_id}/summary"
curl -s "$BASE_URL/campaigns/$CAMPAIGN_ID/summary" | python3 -m json.tool
echo ""

echo "=========================================="
echo "7. FEATURE 3: PEER CONFIRMATION SYSTEM"
echo "=========================================="
echo ""

echo "7.1 Create a sighting for confirmation test"
SIGHTING2_RESPONSE=$(curl -s -X POST $BASE_URL/sightings/ -H "Content-Type: application/json" -H "X-User-ID: $RANGER_ID" -d '{
  "pokemon_id": 1,
  "height": 0.7,
  "weight": 6.9,
  "shiny": false,
  "region": "Kanto",
  "location": "Pallet Town",
  "weather": "clear",
  "time_of_day": "morning",
  "notes": "Test for confirmation"
}')
SIGHTING2_ID=$(echo "$SIGHTING2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
echo "Created sighting: $SIGHTING2_ID"
echo ""

echo "7.2 POST /sightings/{sighting_id}/confirm - Confirm sighting"
curl -s -X POST "$BASE_URL/sightings/$SIGHTING2_ID/confirm" -H "X-User-ID: $RANGER_ID2" | python3 -m json.tool
echo ""

echo "7.3 GET /sightings/{sighting_id}/confirmation"
curl -s "$BASE_URL/sightings/$SIGHTING2_ID/confirmation" | python3 -m json.tool
echo ""

echo "7.4 Try to confirm own sighting (should fail)"
curl -s -X POST "$BASE_URL/sightings/$SIGHTING2_ID/confirm" -H "X-User-ID: $RANGER_ID" | python3 -m json.tool
echo ""

echo "=========================================="
echo "8. FEATURE 4: REGIONAL RESEARCH SUMMARY"
echo "=========================================="
echo ""

echo "8.1 GET /regions/{region_name}/summary"
curl -s "$BASE_URL/regions/Kanto/summary" | python3 -m json.tool
echo ""

echo "=========================================="
echo "9. FEATURE 5: POKEMON RARITY & ENCOUNTER RATE ANALYSIS"
echo "=========================================="
echo ""

echo "9.1 GET /regions/{region_name}/analysis"
curl -s "$BASE_URL/regions/Kanto/analysis" | python3 -m json.tool
echo ""

echo "=========================================="
echo "10. FEATURE 6: RANGER LEADERBOARD"
echo "=========================================="
echo ""

echo "10.1 GET /leaderboard (if implemented)"
curl -s "$BASE_URL/leaderboard" 2>&1 | python3 -m json.tool || echo "Endpoint not found or error"
echo ""

echo "=========================================="
echo "11. FEATURE 7: TRAINER POKEDEX (CATCH TRACKING)"
echo "=========================================="
echo ""

echo "11.1 POST /trainers/{trainer_id}/pokedex/{pokemon_id} - Mark as caught"
curl -s -X POST "$BASE_URL/trainers/$TRAINER_ID/pokedex/25" -H "X-User-ID: $TRAINER_ID" | python3 -m json.tool
echo ""

echo "11.2 GET /trainers/{trainer_id}/pokedex - View catch log"
curl -s "$BASE_URL/trainers/$TRAINER_ID/pokedex" | python3 -m json.tool
echo ""

echo "11.3 GET /trainers/{trainer_id}/pokedex/summary"
curl -s "$BASE_URL/trainers/$TRAINER_ID/pokedex/summary" | python3 -m json.tool
echo ""

echo "11.4 GET /pokedex/{pokemon_id} with X-User-ID header"
curl -s "$BASE_URL/pokedex/25" -H "X-User-ID: $TRAINER_ID" | python3 -m json.tool
echo ""

echo "11.5 DELETE /trainers/{trainer_id}/pokedex/{pokemon_id}"
curl -s -X DELETE "$BASE_URL/trainers/$TRAINER_ID/pokedex/25" -H "X-User-ID: $TRAINER_ID"
echo "Deleted catch record"
echo ""

echo "=========================================="
echo "TESTING COMPLETE"
echo "=========================================="
