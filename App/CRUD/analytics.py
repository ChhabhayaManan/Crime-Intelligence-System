"""
analytics.py
------------
Read-only analytics / reporting queries.

Functions
---------
  get_crime_hotspots – GET /analytics/hotspots
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from App.db.models import Address, CaseDetail
from App.schema.case import (
    CrimeHotspotItem,
    CrimeHotspotQuery,
    CrimeHotspotResponse,
)

# ---------------------------------------------------------------------------
# Crime hotspots
# ---------------------------------------------------------------------------

def get_crime_hotspots(
    db: Session,
    query: CrimeHotspotQuery,
) -> CrimeHotspotResponse:
    """Aggregate case counts by city with optional filters. Returns cities sorted by count desc."""
    q = (
        db.query(Address.city, func.count(CaseDetail.case_id).label("case_count"))
        .join(CaseDetail, CaseDetail.crime_location == Address.address_id)
    )

    if query.city:
        q = q.filter(Address.city.ilike(f"%{query.city}%"))
    if query.from_date:
        q = q.filter(CaseDetail.open_date >= query.from_date)
    if query.to_date:
        q = q.filter(CaseDetail.open_date <= query.to_date)

    rows = (
        q.group_by(Address.city)
        .order_by(func.count(CaseDetail.case_id).desc())
        .all()
    )

    items = [
        CrimeHotspotItem(city=row.city or "Unknown", case_count=row.case_count)
        for row in rows
        if row.city  # skip NULL cities
    ]

    return CrimeHotspotResponse(items=items)
