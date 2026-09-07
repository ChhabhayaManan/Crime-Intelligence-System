import os
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import requests

BASE = os.environ["API_BASE"].rstrip("/")
API = f"{BASE}/api/v1"
TS = str(int(time.time()))[-6:]
INCLUDE_ALL = [("include", name) for name in
               ("evidence", "witnesses", "suspects", "victims", "trials", "testimonies")]


class _S:
    username: str = f"tuser_{TS}"
    password: str = "T3stP@ss!"
    email: str = f"tuser_{TS}@example.com"
    user_id: int = 0
    token: str = ""
    refresh: str = ""
    headers: dict = {}
    address_id: int = 0
    person_id: int = 0
    officer_person_id: int = 0
    case_id: int = 0
    case_open_date: str = ""
    evidence_id: int = 0
    suspect_person_id: int = 0
    witness_person_id: int = 0
    victim_person_id: int = 0
    trial_id: int = 0


S = _S()


def url(path: str) -> str:
    return f"{API}/{path.lstrip('/')}"


class TestHealth:
    def test_liveness(self):
        r = requests.get(f"{BASE}/health", timeout=60)
        assert r.status_code == 200

    def test_readiness(self):
        r = requests.get(f"{BASE}/health/ready", timeout=60)
        assert r.status_code == 200, f"Readiness check failed: {r.text}"


class TestAuth:
    def test_register(self):
        r = requests.post(url("auth/register"), json={
            "username": S.username,
            "email": S.email,
            "password": S.password,
            "confirm_password": S.password,
            "mobile_number": "9876543210",
        }, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["username"] == S.username
        assert "role" not in body and "is_active" not in body, r.text
        assert set(body) == {"user_id", "username", "email", "mobile_number"}, r.text
        S.user_id = body["user_id"]

    def test_register_duplicate_rejected(self):
        r = requests.post(url("auth/register"), json={
            "username": S.username,
            "email": S.email,
            "password": S.password,
            "confirm_password": S.password,
        }, timeout=60)
        assert r.status_code == 400, r.text

    def test_register_password_mismatch_rejected(self):
        r = requests.post(url("auth/register"), json={
            "username": f"nomatch_{TS}",
            "email": f"nomatch_{TS}@example.com",
            "password": S.password,
            "confirm_password": "differentPassword!",
        }, timeout=60)
        assert r.status_code == 422, r.text

    def test_login(self):
        r = requests.post(url("auth/login"), json={
            "username": S.username,
            "password": S.password,
        }, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert "expires_at" in body
        S.token = body["access_token"]
        S.refresh = body["refresh_token"]
        S.headers = {"Authorization": f"Bearer {S.token}"}

    def test_login_wrong_password_rejected(self):
        r = requests.post(url("auth/login"), json={
            "username": S.username,
            "password": "completely_wrong_999",
        }, timeout=60)
        assert r.status_code == 401, r.text

    def test_login_unknown_user_rejected(self):
        r = requests.post(url("auth/login"), json={
            "username": f"ghost_{TS}",
            "password": S.password,
        }, timeout=60)
        assert r.status_code == 401, r.text

    def test_refresh_with_valid_token_returns_working_access_token(self):
        r = requests.post(url("auth/refresh"), json={
            "refresh_token": S.refresh,
        }, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" not in body
        assert body["token_type"] == "bearer"
        assert "expires_at" in body

        new_headers = {"Authorization": f"Bearer {body['access_token']}"}
        tmp_pw = "FromRefresh1!"
        r2 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": S.password,
            "new_password": tmp_pw,
        }, headers=new_headers, timeout=60)
        assert r2.status_code == 200, r2.text
        r3 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": tmp_pw,
            "new_password": S.password,
        }, headers=S.headers, timeout=60)
        assert r3.status_code == 200, r3.text

    def test_refresh_with_access_token_in_body_rejected(self):
        r = requests.post(url("auth/refresh"), json={
            "refresh_token": S.token,
        }, timeout=60)
        assert r.status_code == 401, r.text
        assert r.headers.get("WWW-Authenticate") == "Bearer"
        assert r.json()["detail"] == "Could not validate credentials."

    def test_refresh_with_tampered_or_garbage_token_in_body_rejected(self):
        assert S.refresh, "test_login must run first"
        head, body_seg, sig = S.refresh.split(".")
        tampered = f"{head}.{body_seg[:-2] + ('AA' if body_seg[-2:] != 'AA' else 'BB')}.{sig}"
        for bad_token in ("not.a.jwt", "garbage", tampered):
            r = requests.post(url("auth/refresh"), json={
                "refresh_token": bad_token,
            }, timeout=60)
            assert r.status_code == 401, (bad_token, r.text)
            assert r.headers.get("WWW-Authenticate") == "Bearer"
            assert r.json()["detail"] == "Could not validate credentials."

    def test_protected_endpoint_without_token_rejected(self):
        r = requests.get(url("cases"), timeout=60)
        assert r.status_code == 401, r.text

    def test_change_password_with_refresh_token_as_bearer_rejected(self):
        assert S.refresh, "test_login must run first"
        r = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": S.password,
            "new_password": S.password,
        }, headers={"Authorization": f"Bearer {S.refresh}"}, timeout=60)
        assert r.status_code == 401, r.text
        assert r.headers.get("WWW-Authenticate") == "Bearer"
        assert r.json()["detail"] == "Could not validate credentials."

    def test_change_password_with_tampered_or_garbage_token_rejected(self):
        assert S.token, "test_login must run first"
        head, body_seg, sig = S.token.split(".")
        tampered = f"{head}.{body_seg[:-2] + ('AA' if body_seg[-2:] != 'AA' else 'BB')}.{sig}"
        for bad_token in (tampered, "not.a.jwt", "garbage-bearer-token"):
            r = requests.post(url("auth/change-password"), json={
                "username": S.username,
                "current_password": S.password,
                "new_password": S.password,
            }, headers={"Authorization": f"Bearer {bad_token}"}, timeout=60)
            assert r.status_code == 401, (bad_token, r.text)

    def test_change_password_and_revert(self):
        new_pw = "N3wP@ssword!"
        r = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": S.password,
            "new_password": new_pw,
        }, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        r2 = requests.post(url("auth/login"), json={
            "username": S.username,
            "password": new_pw,
        }, timeout=60)
        assert r2.status_code == 200, r2.text
        r3 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": new_pw,
            "new_password": S.password,
        }, headers=S.headers, timeout=60)
        assert r3.status_code == 200, r3.text

    def test_expired_access_token_then_refresh_recovers(self):
        secret = os.getenv("JWT_SECRET")
        if not secret:
            pytest.skip(
                "SILENTLY SKIPPED — expiry behaviour is NOT being verified. "
                "JWT_SECRET is not set in this test process's environment, so a "
                "token signed with the same secret the live server uses cannot be "
                "minted without changing production code (e.g. exposing "
                "ACCESS_TOKEN_EXPIRE_MINUTES as an env override). To enable this "
                "test, put JWT_SECRET=<the server's secret> in .env or the "
                "environment (see the Setup block at the top of this file)."
            )

        now = datetime.now(tz=timezone.utc)
        short_lived_access = jwt.encode(
            {
                "sub": str(S.user_id),
                "username": S.username,
                "typ": "access",
                "iat": now,
                "exp": now + timedelta(seconds=1),
            },
            secret,
            algorithm="HS256",
        )
        valid_short_lived = jwt.encode(
            {
                "sub": str(S.user_id),
                "username": S.username,
                "typ": "access",
                "iat": now,
                "exp": now + timedelta(seconds=60),
            },
            secret,
            algorithm="HS256",
        )
        r0 = requests.post(url("auth/change-password"), json={
            "username": "someone_else",
            "current_password": "x",
            "new_password": "Irrelevant1!",
        }, headers={"Authorization": f"Bearer {valid_short_lived}"}, timeout=60)
        assert r0.status_code == 403, r0.text

        time.sleep(2)

        expired_headers = {"Authorization": f"Bearer {short_lived_access}"}
        r1 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": S.password,
            "new_password": S.password,
        }, headers=expired_headers, timeout=60)
        assert r1.status_code == 401, r1.text

        r2 = requests.post(url("auth/refresh"), json={
            "refresh_token": S.refresh,
        }, timeout=60)
        assert r2.status_code == 200, r2.text
        new_access = r2.json()["access_token"]

        new_pw = "Recovered9!"
        r3 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": S.password,
            "new_password": new_pw,
        }, headers={"Authorization": f"Bearer {new_access}"}, timeout=60)
        assert r3.status_code == 200, r3.text

        r4 = requests.post(url("auth/change-password"), json={
            "username": S.username,
            "current_password": new_pw,
            "new_password": S.password,
        }, headers=S.headers, timeout=60)
        assert r4.status_code == 200, r4.text


class TestAddresses:
    def test_create(self):
        r = requests.post(url("addresses"), json={
            "street_address": f"123 Test Street {TS}",
            "city": "TestCity",
            "state": "TestState",
            "pin_code": "000001",
            "country": "Testland",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "address_id" in body
        assert body["city"] == "TestCity"
        S.address_id = body["address_id"]

    def test_list(self):
        r = requests.get(url("addresses"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert "meta" in body
        assert isinstance(body["items"], list)

    def test_list_filter_city(self):
        r = requests.get(url("addresses"), params={"city": "TestCity"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        ids = [a["address_id"] for a in r.json()["items"]]
        assert S.address_id in ids

    def test_list_filter_country(self):
        r = requests.get(url("addresses"), params={"country": "Testland"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["items"], list)

    def test_get(self):
        r = requests.get(url(f"addresses/{S.address_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["address_id"] == S.address_id
        assert body["city"] == "TestCity"

    def test_update(self):
        r = requests.patch(url(f"addresses/{S.address_id}"), json={
            "city": "UpdatedCity",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["city"] == "UpdatedCity"

    def test_get_nonexistent_returns_404(self):
        r = requests.get(url("addresses/9999999"), headers=S.headers, timeout=60)
        assert r.status_code == 404, r.text

    def test_pagination(self):
        r = requests.get(url("addresses"), params={"page": 1, "page_size": 5}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) <= 5
        assert body["meta"]["page_size"] == 5


class TestPersons:
    def test_create_with_inline_address(self):
        r = requests.post(url("persons"), json={
            "first_name": "Test",
            "last_name": f"User{TS}",
            "gender": "M",
            "birth_date": "1990-01-15",
            "occupation": "Tester",
            "contact_number": "1234567890",
            "address": {
                "street_address": f"456 Person Ave {TS}",
                "city": "Personville",
                "state": "PS",
                "pin_code": "000002",
                "country": "Testland",
            },
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "person_id" in body
        assert "summary" in body
        S.person_id = body["person_id"]

    def test_create_with_existing_address_id(self):
        r = requests.post(url("persons"), json={
            "first_name": "Another",
            "last_name": f"Person{TS}",
            "gender": "F",
            "birth_date": "1985-06-20",
            "occupation": "Analyst",
            "contact_number": "9876543211",
            "address_id": S.address_id,
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        assert "person_id" in r.json()

    def test_create_requires_address_or_address_id(self):
        r = requests.post(url("persons"), json={
            "first_name": "Bad",
            "last_name": "Person",
            "gender": "M",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 422, r.text

    def test_create_future_birth_date_rejected(self):
        r = requests.post(url("persons"), json={
            "first_name": "Future",
            "last_name": "Person",
            "gender": "M",
            "birth_date": "2099-01-01",
            "address_id": S.address_id,
        }, headers=S.headers, timeout=60)
        assert r.status_code == 422, r.text

    def test_list(self):
        r = requests.get(url("persons"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert "meta" in body

    def test_list_filter_by_role_officer(self):
        r = requests.get(url("persons"), params={"role": "officer"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        if items:
            S.officer_person_id = items[0]["person_id"]

    def test_list_search_by_name(self):
        r = requests.get(url("persons"), params={"query": f"User{TS}"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        ids = [p["person_id"] for p in r.json()["items"]]
        assert S.person_id in ids

    def test_get(self):
        r = requests.get(url(f"persons/{S.person_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["person_id"] == S.person_id
        assert body["first_name"] == "Test"
        assert "role_details" in body

    def test_update(self):
        r = requests.patch(url(f"persons/{S.person_id}"), json={
            "occupation": "Senior Tester",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["occupation"] == "Senior Tester"

    def test_get_person_cases(self):
        r = requests.get(url(f"persons/{S.person_id}/cases"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_get_nonexistent_returns_404(self):
        r = requests.get(url("persons/9999999"), headers=S.headers, timeout=60)
        assert r.status_code == 404, r.text

    def test_pagination(self):
        r = requests.get(url("persons"), params={"page": 1, "page_size": 3}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) <= 3


class TestCases:
    def test_open_case(self):
        payload = {
            "summary": f"Test robbery case {TS}",
            "crime_type": "Robbery",
            "location_id": S.address_id,
            "reported_by": S.person_id,
            "occurred_at": "2025-01-10",
        }
        if S.officer_person_id:
            payload["initial_officer_id"] = S.officer_person_id
        r = requests.post(url("cases"), json=payload, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "case_id" in body
        assert "open_date" in body
        assert body["status"] == "open"
        S.case_id = body["case_id"]
        S.case_open_date = body["open_date"]

    def test_list(self):
        r = requests.get(url("cases"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert "meta" in body

    def test_list_filter_crime_type(self):
        r = requests.get(url("cases"), params={"crime_type": "Robbery"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        ids = [c["case_id"] for c in r.json()["items"]]
        assert S.case_id in ids

    def test_list_filter_status_open(self):
        r = requests.get(url("cases"), params={"status": "open"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        for c in r.json()["items"]:
            assert c["status"] == "open"

    def test_list_filter_date_range(self):
        r = requests.get(url("cases"), params={"from": "2025-01-01", "to": "2025-12-31"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text

    def test_list_sort(self):
        r = requests.get(url("cases"), params={"sort": "-open_date"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text

    def test_list_invalid_date_range_rejected(self):
        r = requests.get(url("cases"), params={"from": "2025-12-31", "to": "2025-01-01"}, headers=S.headers, timeout=60)
        assert r.status_code == 400, r.text

    def test_get(self):
        r = requests.get(url(f"cases/{S.case_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["case_id"] == S.case_id
        assert body["status"] == "open"

    def test_update(self):
        r = requests.patch(url(f"cases/{S.case_id}"), json={
            "summary": f"Updated robbery case {TS}",
            "crime_type": "Armed Robbery",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["crime_type"] == "Armed Robbery"

    def test_assign_officer(self):
        if not S.officer_person_id:
            pytest.skip("No officer found in seed data (role=officer)")
        r = requests.post(
            url(f"cases/{S.case_id}/officers/{S.officer_person_id}"),
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        assert "detail" in r.json()

    def test_unlink_officer(self):
        if not S.officer_person_id:
            pytest.skip("No officer found in seed data (role=officer)")
        r = requests.delete(
            url(f"cases/{S.case_id}/officers/{S.officer_person_id}"),
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text

    def test_get_details_empty(self):
        r = requests.get(
            url(f"cases/{S.case_id}/details"),
            params=INCLUDE_ALL,
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "case" in body
        assert body["case"]["case_id"] == S.case_id
        assert "evidence" in body
        assert "suspects" in body
        assert "witnesses" in body
        assert "victims" in body
        assert "trials" in body

    def test_get_nonexistent_returns_404(self):
        r = requests.get(url("cases/9999999"), headers=S.headers, timeout=60)
        assert r.status_code == 404, r.text


class TestEvidence:
    def test_add_evidence(self):
        r = requests.post(url(f"cases/{S.case_id}/evidence"), json={
            "description": f"Fingerprints on weapon {TS}",
            "collected_at": "2025-01-11",
            "location_id": S.address_id,
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "evidence_id" in body
        assert "evidence" in body
        assert body["evidence"]["case_id"] == S.case_id
        S.evidence_id = body["evidence_id"]

    def test_add_evidence_minimal(self):
        r = requests.post(url(f"cases/{S.case_id}/evidence"), json={
            "description": f"CCTV footage {TS}",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text

    def test_list_case_evidence(self):
        r = requests.get(url(f"cases/{S.case_id}/evidence"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert body["case_id"] == S.case_id
        ids = [e["evidence_id"] for e in body["items"]]
        assert S.evidence_id in ids

    def test_get(self):
        r = requests.get(url(f"evidence/{S.evidence_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["evidence_id"] == S.evidence_id
        assert body["case_id"] == S.case_id

    def test_update(self):
        r = requests.patch(
            url(f"evidence/{S.evidence_id}"),
            json={"description": f"Updated fingerprints on weapon {TS}"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        assert "Updated fingerprints" in r.json()["description"]

    def test_update_location(self):
        r = requests.patch(
            url(f"evidence/{S.evidence_id}"),
            json={"location_id": S.address_id},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.json()["location_id"] == S.address_id

    def test_get_nonexistent_returns_404(self):
        r = requests.get(url("evidence/9999999"), headers=S.headers, timeout=60)
        assert r.status_code == 404, r.text


class TestSuspects:
    def test_add_suspect_inline_with_evidence(self):
        r = requests.post(url(f"cases/{S.case_id}/suspects"), json={
            "person": {
                "first_name": "Sus",
                "last_name": f"Pect{TS}",
                "gender": "M",
                "birth_date": "1988-03-15",
                "contact_number": "5550001111",
                "address_id": S.address_id,
            },
            "evidence_ids": [S.evidence_id],
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "suspect_id" in body
        assert "suspect" in body
        assert S.evidence_id in body["suspect"]["linked_evidence_ids"]
        S.suspect_person_id = body["suspect_id"]

    def test_add_suspect_existing_person(self):
        r = requests.post(url(f"cases/{S.case_id}/suspects"), json={
            "person_id": S.person_id,
            "evidence_ids": [],
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text

    def test_list_case_suspects(self):
        r = requests.get(url(f"cases/{S.case_id}/suspects"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert body["case_id"] == S.case_id
        ids = [s["suspect_id"] for s in body["items"]]
        assert S.suspect_person_id in ids

    def test_update_arrest_status(self):
        r = requests.patch(
            url(f"cases/{S.case_id}/suspects/{S.suspect_person_id}"),
            json={"arrest_status": "arrested"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["suspect"]["arrest_status"] == "arrested"

    def test_update_physical_description(self):
        r = requests.patch(
            url(f"cases/{S.case_id}/suspects/{S.suspect_person_id}"),
            json={
                "physical_description": "Tall, dark hair, scar on left cheek",
                "family_contact": "5550008888",
            },
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "Tall" in body["suspect"]["physical_description"]

    def test_update_to_released(self):
        r = requests.patch(
            url(f"cases/{S.case_id}/suspects/{S.suspect_person_id}"),
            json={"arrest_status": "released"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.json()["suspect"]["arrest_status"] == "released"

    def test_get(self):
        r = requests.get(url(f"suspects/{S.suspect_person_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["suspect_id"] == S.suspect_person_id

    def test_invalid_arrest_status_rejected(self):
        r = requests.patch(
            url(f"cases/{S.case_id}/suspects/{S.suspect_person_id}"),
            json={"arrest_status": "invalid_status"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 422, r.text


class TestWitnesses:
    def test_add_witness_inline(self):
        r = requests.post(url(f"cases/{S.case_id}/witnesses"), json={
            "person": {
                "first_name": "Wit",
                "last_name": f"Ness{TS}",
                "gender": "F",
                "birth_date": "1992-07-22",
                "contact_number": "5550002222",
                "address_id": S.address_id,
            },
            "contact_info": "5550002222",
            "statement": f"I saw the suspect near the scene on {TS}",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "witness_id" in body
        assert "witness" in body
        S.witness_person_id = body["witness_id"]

    def test_add_witness_existing_person(self):
        r = requests.post(url(f"cases/{S.case_id}/witnesses"), json={
            "person_id": S.person_id,
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text

    def test_list_case_witnesses(self):
        r = requests.get(url(f"cases/{S.case_id}/witnesses"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert body["case_id"] == S.case_id
        ids = [w["witness_id"] for w in body["items"]]
        assert S.witness_person_id in ids

    def test_record_testimony(self):
        r = requests.post(
            url(f"cases/{S.case_id}/witnesses/{S.witness_person_id}/testimony"),
            json={
                "testimony_text": f"Suspect wore red jacket, seen at {TS}",
                "pointed_suspects": [S.suspect_person_id],
            },
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert "testimony_text" in body
        assert body["witness_id"] == S.witness_person_id
        assert body["case_id"] == S.case_id
        assert S.suspect_person_id in body["pointed_suspects"]

    def test_record_testimony_empty_suspects(self):
        r = requests.post(
            url(f"cases/{S.case_id}/witnesses/{S.witness_person_id}/testimony"),
            json={
                "testimony_text": f"Additional observation {TS}",
                "pointed_suspects": [],
            },
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 201, r.text

    def test_list_case_testimonies(self):
        r = requests.get(url(f"cases/{S.case_id}/testimonies"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        witness_ids = [t["witness_id"] for t in body]
        assert S.witness_person_id in witness_ids


class TestVictims:
    def test_add_victim_inline(self):
        r = requests.post(url(f"cases/{S.case_id}/victims"), json={
            "person": {
                "first_name": "Vic",
                "last_name": f"Tim{TS}",
                "gender": "F",
                "birth_date": "1995-11-05",
                "contact_number": "5550003333",
                "address_id": S.address_id,
            },
            "harm_details": "Minor physical injuries",
            "family_contact": "5550009999",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "victim_id" in body
        assert "victim" in body
        assert body["victim"]["harm_details"] == "Minor physical injuries"
        S.victim_person_id = body["victim_id"]

    def test_add_victim_existing_person(self):
        r = requests.post(url(f"cases/{S.case_id}/victims"), json={
            "person_id": S.person_id,
            "harm_details": "Psychological trauma",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text

    def test_list_case_victims(self):
        r = requests.get(url(f"cases/{S.case_id}/victims"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert body["case_id"] == S.case_id
        ids = [v["victim_id"] for v in body["items"]]
        assert S.victim_person_id in ids

    def test_list_victims_global(self):
        r = requests.get(url("victims"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert "meta" in body

    def test_list_victims_global_search(self):
        r = requests.get(url("victims"), params={"query": f"Tim{TS}"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        ids = [v["victim_id"] for v in r.json()["items"]]
        assert S.victim_person_id in ids

    def test_list_victims_pagination(self):
        r = requests.get(url("victims"), params={"page": 1, "page_size": 5}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) <= 5


class TestTrials:
    def test_add_trial(self):
        r = requests.post(url(f"cases/{S.case_id}/trials"), json={
            "hearing_date": "2025-03-01",
            "judge_id": S.person_id,
            "court_level": "District Court",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "trial_id" in body
        assert "trial" in body
        assert body["trial"]["court_level"] == "District Court"
        S.trial_id = body["trial_id"]

    def test_add_trial_minimal(self):
        r = requests.post(url(f"cases/{S.case_id}/trials"), json={}, headers=S.headers, timeout=60)
        assert r.status_code == 201, r.text

    def test_list_case_trials(self):
        r = requests.get(url(f"cases/{S.case_id}/trials"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert body["case_id"] == S.case_id
        ids = [t["trial_id"] for t in body["items"]]
        assert S.trial_id in ids

    def test_get_trial_detail(self):
        r = requests.get(url(f"cases/{S.case_id}/trials/{S.trial_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "trial" in body
        assert "punishments" in body
        assert isinstance(body["punishments"], list)

    def test_assign_judge(self):
        r = requests.post(
            url(f"cases/{S.case_id}/trials/{S.trial_id}/judge/{S.person_id}"),
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        assert "detail" in r.json()

    def test_add_hearing(self):
        r = requests.post(
            url(f"cases/{S.case_id}/trials/{S.trial_id}/hearing"),
            json={
                "hearing_date": "2025-03-15",
                "outcome": "adjourned",
            },
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert "trial_id" in body
        assert "trial" in body

    def test_apply_punishment(self):
        r = requests.post(
            url(f"cases/{S.case_id}/trials/{S.trial_id}/punishment"),
            json={
                "person_ids": [S.suspect_person_id],
                "fine": 5000,
                "jail_start": "2025-04-01",
                "jail_end": "2026-04-01",
                "death_penalty": "N",
            },
            headers=S.headers, timeout=60,
        )
        assert r.status_code in (201, 400), r.text  # 400 when the person has no criminal profile
        if r.status_code == 201:
            body = r.json()
            assert "trial_id" in body
            assert "punishments" in body


class TestCaseDetailsFull:
    def test_all_includes_populated(self):
        r = requests.get(
            url(f"cases/{S.case_id}/details"),
            params=INCLUDE_ALL,
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["case"]["case_id"] == S.case_id
        assert len(body["evidence"]) >= 1, "Expected at least 1 evidence item"
        assert len(body["suspects"]) >= 1, "Expected at least 1 suspect"
        assert len(body["witnesses"]) >= 1, "Expected at least 1 witness"
        assert len(body["victims"]) >= 1, "Expected at least 1 victim"
        assert len(body["trials"]) >= 1, "Expected at least 1 trial"
        assert len(body["testimonies"]) >= 1, "Expected at least 1 testimony"

    def test_single_include_evidence_only(self):
        r = requests.get(
            url(f"cases/{S.case_id}/details"),
            params={"include": "evidence"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "evidence" in body
        assert len(body["evidence"]) >= 1

    def test_no_include_returns_case_only(self):
        r = requests.get(
            url(f"cases/{S.case_id}/details"),
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "case" in body
        assert body["case"]["case_id"] == S.case_id


class TestAnalytics:
    def test_hotspots(self):
        r = requests.get(url("analytics/hotspots"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)
        assert len(body["items"]) >= 1

    def test_hotspots_filter_city(self):
        r = requests.get(
            url("analytics/hotspots"),
            params={"city": "TestCity"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body

    def test_hotspots_filter_date_range(self):
        r = requests.get(
            url("analytics/hotspots"),
            params={"from": "2024-01-01", "to": "2025-12-31"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 200, r.text

    def test_hotspots_invalid_date_range_rejected(self):
        r = requests.get(
            url("analytics/hotspots"),
            params={"from": "2025-12-31", "to": "2025-01-01"},
            headers=S.headers, timeout=60,
        )
        assert r.status_code == 400, r.text

    def test_hotspots_sorted_desc(self):
        r = requests.get(url("analytics/hotspots"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        counts = [item["case_count"] for item in r.json()["items"]]
        assert counts == sorted(counts, reverse=True), "Hotspots should be sorted by case_count desc"


class TestCaseClose:
    def test_close_case(self):
        r = requests.patch(url(f"cases/{S.case_id}/close"), json={
            "closed_at": "2025-06-01",
        }, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "closed"
        assert body["case_id"] == S.case_id
        assert body["end_date"] == "2025-06-01"

    def test_closed_case_shows_in_list(self):
        r = requests.get(url("cases"), params={"status": "closed"}, headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        ids = [c["case_id"] for c in r.json()["items"]]
        assert S.case_id in ids

    def test_get_closed_case(self):
        r = requests.get(url(f"cases/{S.case_id}"), headers=S.headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "closed"


# ---------------------------------------------------------------------------
# The classes below build their own fixtures, so they can be run on their own
# with -k and still mean something.
# ---------------------------------------------------------------------------

class _Ctx:
    """Its own user, address, person and case."""

    def __init__(self, tag):
        name = f"{tag}_{TS}"
        pw = "C0ntext!pass"
        r = requests.post(url("auth/register"), json={
            "username": name, "email": f"{name}@example.com",
            "password": pw, "confirm_password": pw,
        }, timeout=60)
        assert r.status_code == 201, r.text
        self.username, self.password = name, pw

        r = requests.post(url("auth/login"), json={"username": name, "password": pw}, timeout=60)
        assert r.status_code == 200, f"login failed immediately after register: {r.text}"
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        self.address_id = self._post("addresses", {
            "street_address": "1 Ctx Road", "city": f"Ctx{TS}", "state": "S",
            "pin_code": "000002", "country": "Testland"})["address_id"]
        self.person_id = self._post("persons", {
            "first_name": "Ctx", "last_name": "Person", "gender": "M",
            "address_id": self.address_id})["person_id"]
        self.case_id = self.new_case()["case_id"]

    def _post(self, path, payload):
        r = requests.post(url(path), json=payload, headers=self.headers, timeout=60)
        assert r.status_code == 201, r.text
        return r.json()

    def new_case(self, crime_type="CtxCrime"):
        return self._post("cases", {
            "summary": f"Context case {TS}", "crime_type": crime_type,
            "location_id": self.address_id, "reported_by": self.person_id,
            "occurred_at": "2025-01-01"})


@pytest.fixture(scope="class")
def ctx(request):
    c = _Ctx(request.cls.__name__.lower())
    request.cls.ctx = c
    return c


@pytest.mark.usefixtures("ctx")
class TestWriteThenRead:
    """A write must be committed before its response reaches the client."""

    def test_created_case_is_readable_immediately(self):
        for _ in range(10):
            case_id = self.ctx.new_case("RaceCheck")["case_id"]
            got = requests.get(url(f"cases/{case_id}"), headers=self.ctx.headers, timeout=60)
            assert got.status_code == 200, f"case {case_id} unreadable right after creation: {got.text}"

    def test_registered_user_can_log_in_immediately(self):
        for i in range(5):
            name = f"race_{TS}_{i}"
            r = requests.post(url("auth/register"), json={
                "username": name, "email": f"{name}@example.com",
                "password": self.ctx.password, "confirm_password": self.ctx.password,
            }, timeout=60)
            assert r.status_code == 201, r.text
            login = requests.post(url("auth/login"), json={
                "username": name, "password": self.ctx.password}, timeout=60)
            assert login.status_code == 200, f"login failed right after register: {login.text}"

    def test_failed_request_leaves_no_partial_write(self):
        ghost = f"ghost_{TS}"
        r = requests.post(url(f"cases/{self.ctx.case_id}/suspects"), json={
            "person": {"first_name": ghost, "last_name": "Ghost", "gender": "M",
                       "address_id": self.ctx.address_id},
            "evidence_ids": [9999999],
        }, headers=self.ctx.headers, timeout=60)
        assert r.status_code == 400, r.text
        found = requests.get(url("persons"), params={"query": ghost},
                             headers=self.ctx.headers, timeout=60)
        assert found.json()["meta"]["total"] == 0, "a person survived a failed request"


@pytest.mark.usefixtures("ctx")
class TestErrorMapping:
    """The error type decides the status code, not the route."""

    def test_missing_entity_is_404(self):
        for path in ("addresses/9999999", "persons/9999999", "cases/9999999",
                     "evidence/9999999", "suspects/9999999"):
            r = requests.get(url(path), headers=self.ctx.headers, timeout=60)
            assert r.status_code == 404, f"{path} -> {r.status_code} {r.text}"

    def test_missing_case_on_nested_write_is_404(self):
        r = requests.post(url("cases/9999999/suspects"), json={
            "person_id": self.ctx.person_id, "evidence_ids": [],
        }, headers=self.ctx.headers, timeout=60)
        assert r.status_code == 404, r.text

    def test_editing_a_closed_case_is_400(self):
        case_id = self.ctx.new_case()["case_id"]
        r = requests.patch(url(f"cases/{case_id}/close"), json={},
                           headers=self.ctx.headers, timeout=60)
        assert r.status_code == 200, r.text
        r = requests.patch(url(f"cases/{case_id}"), json={"summary": "nope"},
                           headers=self.ctx.headers, timeout=60)
        assert r.status_code == 400, r.text
        assert "closed" in r.json()["detail"].lower()

    def test_bad_credentials_are_401_with_challenge(self):
        r = requests.post(url("auth/login"), json={
            "username": self.ctx.username, "password": "definitely_wrong_1",
        }, timeout=60)
        assert r.status_code == 401, r.text
        assert r.headers.get("WWW-Authenticate") == "Bearer"

    def test_schema_violation_is_422(self):
        r = requests.post(url("addresses"), json={"city": "OnlyCity"},
                          headers=self.ctx.headers, timeout=60)
        assert r.status_code == 422, r.text


class TestAuthRequired:
    """Everything except health and the auth entry points needs a token."""

    PROTECTED = [
        ("GET", "addresses"), ("GET", "persons"), ("GET", "cases"),
        ("GET", "victims"), ("GET", "analytics/hotspots"),
        ("POST", "addresses"), ("POST", "persons"), ("POST", "cases"),
    ]

    def test_protected_endpoints_reject_anonymous(self):
        for method, path in self.PROTECTED:
            r = requests.request(method, url(path), json={}, timeout=60)
            assert r.status_code == 401, f"{method} {path} -> {r.status_code} {r.text}"

    def test_auth_entry_points_stay_open(self):
        r = requests.post(url("auth/login"), json={"username": "nobody", "password": "x"}, timeout=60)
        assert r.status_code == 401, r.text
        r = requests.post(url("auth/refresh"), json={"refresh_token": "garbage"}, timeout=60)
        assert r.status_code == 401, r.text

    def test_health_stays_open(self):
        assert requests.get(f"{BASE}/health", timeout=60).status_code == 200
        assert requests.get(f"{BASE}/health/ready", timeout=60).status_code == 200
