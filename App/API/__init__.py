from fastapi import APIRouter, Depends

from App.CRUD.auth import get_current_user
from App.API.Routing import (
    addresses,
    cases,
    evidence,
    persons,
    suspects,
    system,
    trials,
    victims,
    witnesses,
)

_PROTECTED = (
    addresses,
    persons,
    cases,
    evidence,
    witnesses,
    suspects,
    victims,
    trials,
    system,
)

api_router = APIRouter()
api_router.include_router(system.auth_router)

for _module in _PROTECTED:
    api_router.include_router(
        _module.router, dependencies=[Depends(get_current_user)]
    )
