"""
App/API/__init__.py
-------------------
Builds the v1 APIRouter that includes every domain sub-router.

All domain routers (persons, cases, evidence, witnesses, suspects,
victims, trials) enforce auth + RBAC at router level.

The system router (auth + analytics) is included without global
dependencies so that /auth/register and /auth/login stay public.
The analytics endpoints inside system_router protect themselves.
"""

from fastapi import APIRouter

from App.API.Routing import (
    addresses_router,
    cases_router,
    evidence_router,
    persons_router,
    suspects_router,
    system_router,
    trials_router,
    victims_router,
    witnesses_router,
)

api_router = APIRouter()

# People 
api_router.include_router(addresses_router)
api_router.include_router(persons_router)

# Case lifecycle 
api_router.include_router(cases_router)

# Case-scoped entities 
api_router.include_router(evidence_router)
api_router.include_router(witnesses_router)
api_router.include_router(suspects_router)
api_router.include_router(victims_router)
api_router.include_router(trials_router)

# Auth + Analytics -- no global dependency here.
# /auth/login and /auth/register stay public.
# Analytics & change-password protect themselves via their own Depends().
api_router.include_router(system_router)

__all__ = ["api_router"]
