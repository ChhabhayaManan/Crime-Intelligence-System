"""
CRUD package for Crime-Tracking-and-Analysis-Database.

Modules
-------
common    – shared helpers and service-level functions
person    – Address and Person CRUD
case      – Case lifecycle (open / get / update / close / list / details)
evidence  – Evidence CRUD tied to cases
witness   – Witness and testimony operations
suspect   – Suspect operations
victim    – Victim operations
trial     – Trial, hearing, and punishment operations
analytics – Read-only aggregation queries
auth      – Authentication and RBAC stubs
"""

# ---- common (service helpers) ----
from .common import (
    assign_judge_to_trial,
    assign_officer_to_case,
    build_person_summary,
    link_suspect_evidence,
    next_id,
    next_trial_number,
    not_found,
    paginate,
    require,
    fetch_case,
    fetch_trial,
    unlink_officer_from_case,
)

# ---- person / address ----
from .person import (
    create_address,
    create_person,
    get_address,
    get_person,
    get_person_cases,
    list_addresses,
    list_persons,
    update_address,
    update_person,
)

# ---- case ----
from .case import (
    close_case,
    get_case,
    get_case_details,
    list_cases,
    open_case,
    update_case,
)

# ---- evidence ----
from .evidence import (
    add_case_evidence,
    get_evidence,
    list_case_evidence,
    update_evidence,
)

# ---- witness ----
from .witness import (
    add_case_witness,
    record_testimony,
    list_case_testimonies,
    list_case_witnesses,
)

# ---- suspect ----
from .suspect import (
    add_case_suspect,
    get_suspect,
    list_case_suspects,
    update_case_suspect,
)

# ---- victim ----
from .victim import (
    add_case_victim,
    list_case_victims,
    list_victims,
)

# ---- trial ----
from .trial import (
    add_case_trial,
    add_trial_hearing,
    apply_trial_punishment,
    get_trial_detail,
    list_case_trials,
    trial_read,
)

# ---- analytics ----
from .analytics import (
    get_case_evidence_witness_suspect,
    get_crime_hotspots,
)

# ---- auth ----
from .auth import (
    change_password,
    get_current_active_user,
    get_current_user,
    login_user,
    register_user,
)

__all__ = [
    # common / services
    "assign_judge_to_trial",
    "assign_officer_to_case",
    "build_person_summary",
    "link_suspect_evidence",
    "next_id",
    "next_trial_number",
    "not_found",
    "paginate",
    "require",
    "fetch_case",
    "fetch_trial",
    "unlink_officer_from_case",
    # person / address
    "create_address",
    "get_address",
    "update_address",
    "list_addresses",
    "create_person",
    "get_person",
    "update_person",
    "list_persons",
    "get_person_cases",
    # case
    "open_case",
    "get_case",
    "update_case",
    "close_case",
    "list_cases",
    "get_case_details",
    # evidence
    "add_case_evidence",
    "list_case_evidence",
    "get_evidence",
    "update_evidence",
    # witness
    "add_case_witness",
    "list_case_witnesses",
    "record_testimony",
    "list_case_testimonies",
    # suspect
    "add_case_suspect",
    "list_case_suspects",
    "update_case_suspect",
    "get_suspect",
    # victim
    "add_case_victim",
    "list_case_victims",
    "list_victims",
    # trial
    "add_case_trial",
    "list_case_trials",
    "add_trial_hearing",
    "get_trial_detail",
    "apply_trial_punishment",
    "trial_read",
    # analytics
    "get_case_evidence_witness_suspect",
    "get_crime_hotspots",
    # auth
    "login_user",
    "register_user",
    "change_password",
    "get_current_user",
    "get_current_active_user",
]
