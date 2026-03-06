#!/bin/bash

BASE_URL="http://localhost:8000/v1"

echo "========================================="
echo "TESTING FEATURE 6: RANGER LEADERBOARD"
echo "========================================="
echo ""

echo "1. Testing basic leaderboard endpoint..."
curl -s "$BASE_URL/leaderboard/?limit=3" | python3 -m json.tool
echo ""
echo ""

echo "2. Testing region filter (Kanto)..."
curl -s "$BASE_URL/leaderboard/?region=Kanto&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "3. Testing region filter case-insensitive (kanto)..."
curl -s "$BASE_URL/leaderboard/?region=kanto&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "4. Testing date range filter..."
curl -s "$BASE_URL/leaderboard/?date_from=2024-01-01&date_to=2024-12-31&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "5. Testing sort by confirmed_sightings..."
curl -s "$BASE_URL/leaderboard/?sort_by=confirmed_sightings&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "6. Testing sort by unique_species..."
curl -s "$BASE_URL/leaderboard/?sort_by=unique_species&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "7. Testing pagination (limit=2, offset=0)..."
curl -s "$BASE_URL/leaderboard/?limit=2&offset=0" | python3 -m json.tool
echo ""
echo ""

echo "8. Testing pagination (limit=2, offset=2)..."
curl -s "$BASE_URL/leaderboard/?limit=2&offset=2" | python3 -m json.tool
echo ""
echo ""

echo "9. Testing invalid region (should return 400)..."
curl -s "$BASE_URL/leaderboard/?region=InvalidRegion" | python3 -m json.tool
echo ""
echo ""

echo "10. Testing invalid date range (date_from > date_to, should return 400)..."
curl -s "$BASE_URL/leaderboard/?date_from=2025-12-31&date_to=2025-01-01" | python3 -m json.tool
echo ""
echo ""

echo "11. Testing limit validation (limit > 200, should return 422)..."
curl -s "$BASE_URL/leaderboard/?limit=300" | python3 -m json.tool
echo ""
echo ""

echo "12. Testing offset validation (offset > 10000, should return 422)..."
curl -s "$BASE_URL/leaderboard/?offset=15000" | python3 -m json.tool
echo ""
echo ""

echo "13. Testing combined filters (region + date range)..."
curl -s "$BASE_URL/leaderboard/?region=Kanto&date_from=2024-01-01&date_to=2024-12-31&limit=3" | python3 -m json.tool
echo ""
echo ""

echo "14. Testing empty results (non-existent date range)..."
curl -s "$BASE_URL/leaderboard/?date_from=2020-01-01&date_to=2020-01-31" | python3 -m json.tool
echo ""
echo ""

echo "15. Testing response structure (checking all required fields)..."
curl -s "$BASE_URL/leaderboard/?limit=1" | python3 -c "
import json, sys
data = json.load(sys.stdin)
entry = data['results'][0]
print('Entry fields:', list(entry.keys()))
print('Rarest pokemon fields:', list(entry['rarest_pokemon'].keys()) if entry.get('rarest_pokemon') else None)
print('')
print('✓ rank:', type(entry['rank']).__name__)
print('✓ ranger_id:', type(entry['ranger_id']).__name__)
print('✓ ranger_name:', type(entry['ranger_name']).__name__)
print('✓ total_sightings:', type(entry['total_sightings']).__name__)
print('✓ confirmed_sightings:', type(entry['confirmed_sightings']).__name__)
print('✓ unique_species:', type(entry['unique_species']).__name__)
print('✓ rarest_pokemon:', type(entry['rarest_pokemon']).__name__ if entry.get('rarest_pokemon') else None)
"
echo ""
echo ""

echo "========================================="
echo "TESTING COMPLETE"
echo "========================================="
