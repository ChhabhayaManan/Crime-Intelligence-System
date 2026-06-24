"""Pure formatting + payload-builder helpers. No streamlit, no network."""
from datetime import datetime


def iso(d):
    """date/datetime -> ISO string; passthrough str; None -> None."""
    if d is None:
        return None
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def map_status(s, default="open"):
    if s == "on_hold":
        return "hold"
    return s or default


def fmt_date(d):
    if not d:
        return "—"
    try:
        return datetime.fromisoformat(str(d).replace("Z", "")).strftime("%d %b %Y").upper()
    except Exception:
        return str(d)


def person_name(p):
    if not p:
        return "—"
    name = p.get("full_name") or " ".join(filter(None, [
        p.get("first_name"), p.get("middle_name"), p.get("last_name"),
    ]))
    return name or f"Person #{p.get('person_id', '?')}"


def fmt_addr(addr):
    if not addr:
        return "—"
    parts = [addr.get("street_address"), addr.get("city"), addr.get("state"),
             addr.get("pin_code"), addr.get("country")]
    return ", ".join(p for p in parts if p) or "—"


def case_ref(open_date, case_id):
    year = str(open_date or "")[:4] or "----"
    case_id_str = str(case_id).zfill(4) if case_id else ""
    return f"CIS/{year}/{case_id_str}"


def gender_label(g):
    if not g:
        return "—"
    return {"M": "Male", "F": "Female", "O": "Other"}.get(str(g).upper(), g)


_STATUS_ICON = {"open": "🟢", "hold": "🟡", "closed": "⚫"}
def status_icon(status):
    return _STATUS_ICON.get(status, "⚪")


_ARREST_ICON = {"wanted": "🔴", "arrested": "🟠", "released": "🟢"}
def arrest_icon(a):
    return _ARREST_ICON.get((a or "").lower(), "⚪")


def build_address_payload(street, city, state, pin_code, country):
    return {
        "street_address": street or None,
        "city": city, "state": state, "pin_code": pin_code, "country": country,
    }


def build_person_payload(first, middle, last, gender, birth_date, occupation,
                         contact, address_id=None, address=None):
    if (address_id is None) == (address is None):
        raise ValueError("Provide exactly one of address_id or address.")
    payload = {
        "first_name": first or None, "middle_name": middle or None, "last_name": last or None,
        "gender": gender or None, "birth_date": iso(birth_date),
        "occupation": occupation or None, "contact_number": contact or None,
    }
    if address_id is not None:
        payload["address_id"] = address_id
    else:
        payload["address"] = address
    return payload


def build_case_payload(summary, crime_type, location_id, reported_by, occurred_at,
                       initial_officer_id=None, open_date=None):
    payload = {
        "summary": summary, "crime_type": crime_type, "location_id": location_id,
        "reported_by": reported_by, "occurred_at": iso(occurred_at),
    }
    if initial_officer_id:
        payload["initial_officer_id"] = initial_officer_id
    if open_date:
        payload["open_date"] = iso(open_date)
    return payload


def build_punishment_payload(person_ids, fine=None, jail_start=None, jail_end=None, death_penalty=None):
    if not person_ids:
        raise ValueError("person_ids required.")
    if jail_start and jail_end and jail_start > jail_end:
        raise ValueError("jail_start cannot be later than jail_end.")
    return {
        "person_ids": list(person_ids), "fine": fine,
        "jail_start": iso(jail_start), "jail_end": iso(jail_end),
        "death_penalty": death_penalty or None,
    }
