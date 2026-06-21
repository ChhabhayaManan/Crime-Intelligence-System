"""
App/API/Routing/__init__.py
---------------------------
Aggregates all domain routers for easy import.
"""

from .addresses import router as addresses_router
from .persons import router as persons_router
from .cases import router as cases_router
from .evidence import router as evidence_router
from .witnesses import router as witnesses_router
from .suspects import router as suspects_router
from .victims import router as victims_router
from .trials import router as trials_router
from .system import router as system_router

__all__ = [
    "addresses_router",
    "persons_router",
    "cases_router",
    "evidence_router",
    "witnesses_router",
    "suspects_router",
    "victims_router",
    "trials_router",
    "system_router",
]
