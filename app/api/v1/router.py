from fastapi import APIRouter

from . import campaigns, leaderboard, pokemon, rangers, regions, sightings, trainers, users

v1_router = APIRouter()

v1_router.include_router(trainers.router)
v1_router.include_router(rangers.router)
v1_router.include_router(pokemon.router)
v1_router.include_router(sightings.router)
v1_router.include_router(users.router)
v1_router.include_router(campaigns.router)
v1_router.include_router(regions.router)
v1_router.include_router(leaderboard.router)
