/**
 * Shared setup and traffic mix for the backend load tests.
 *
 * setup() registers a throwaway user, discovers real address/person/officer
 * ids from the API, and seeds a handful of cases. It calls fail() rather than
 * carrying on, because a run that authenticates badly still finishes green
 * while measuring nothing but 401 latency.
 *
 * trafficMix() is 80% reads / 20% writes.
 */
import http from 'k6/http';
import { check, fail } from 'k6';

export const BASE = __ENV.TARGET_URL || 'http://localhost:8000/api/v1';

const JSON_HEADERS = { 'Content-Type': 'application/json' };
const SEED_CASES = 10;

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randOf(arr) {
  return arr[randInt(0, arr.length - 1)];
}

function ids(path, key, headers) {
  const res = http.get(`${BASE}${path}`, headers);
  if (res.status !== 200) {
    fail(`setup: GET ${path} returned ${res.status}, cannot discover ${key}`);
  }
  return (res.json('items') || []).map((item) => item[key]);
}

export function setupAuthAndSeedCases() {
  const runId = `${Date.now()}_${randInt(1000, 9999)}`;
  const username = `k6user_${runId}`;
  const password = 'K6-load-test-pw-1!';

  const registerRes = http.post(
    `${BASE}/auth/register`,
    JSON.stringify({
      username,
      email: `${username}@example.test`,
      password,
      confirm_password: password,
    }),
    { headers: JSON_HEADERS }
  );
  if (registerRes.status !== 201) {
    fail(`setup: register returned ${registerRes.status} - ${registerRes.body}`);
  }

  const loginRes = http.post(
    `${BASE}/auth/login`,
    JSON.stringify({ username, password }),
    { headers: JSON_HEADERS }
  );
  if (loginRes.status !== 200) {
    fail(`setup: login returned ${loginRes.status} - ${loginRes.body}`);
  }

  const token = loginRes.json('access_token');
  if (!token) {
    fail('setup: login succeeded but returned no access_token');
  }

  const authHeaders = {
    headers: { ...JSON_HEADERS, Authorization: `Bearer ${token}` },
  };

  const addressIds = ids('/addresses?page_size=50', 'address_id', authHeaders);
  const personIds = ids('/persons?page_size=50', 'person_id', authHeaders);
  const officerIds = ids('/persons?role=officer&page_size=50', 'person_id', authHeaders);

  if (!addressIds.length || !personIds.length) {
    fail(`setup: database looks unseeded (${addressIds.length} addresses, ${personIds.length} persons)`);
  }

  const caseIds = [];
  for (let i = 0; i < SEED_CASES; i++) {
    const res = http.post(
      `${BASE}/cases`,
      JSON.stringify({
        summary: `k6 seed case ${i} (${runId})`,
        crime_type: 'Theft',
        location_id: randOf(addressIds),
        reported_by: randOf(personIds),
        occurred_at: '2026-01-01',
      }),
      authHeaders
    );
    if (res.status === 201) caseIds.push(res.json('case_id'));
  }

  if (!caseIds.length) {
    fail('setup: could not create any seed cases, every write would target a missing id');
  }

  return { authHeaders, caseIds, addressIds, personIds, officerIds };
}

export function trafficMix(data) {
  const { authHeaders, caseIds, addressIds, personIds, officerIds } = data;
  const caseId = randOf(caseIds);

  if (Math.random() < 0.8) {
    const roll = Math.random();
    if (roll < 0.35) {
      const r = http.get(`${BASE}/cases?page=1&page_size=20`, authHeaders);
      check(r, { 'list cases 200': (res) => res.status === 200 });
    } else if (roll < 0.6) {
      const r = http.get(`${BASE}/cases/${caseId}`, authHeaders);
      check(r, { 'get case 200': (res) => res.status === 200 });
    } else if (roll < 0.8) {
      const r = http.get(`${BASE}/cases/${caseId}/details`, authHeaders);
      check(r, { 'case details 200': (res) => res.status === 200 });
    } else if (roll < 0.95) {
      const r = http.get(`${BASE}/persons?page=1&page_size=20`, authHeaders);
      check(r, { 'list persons 200': (res) => res.status === 200 });
    } else {
      const r = http.get(`${BASE}/analytics/hotspots`, authHeaders);
      check(r, { 'hotspots 200': (res) => res.status === 200 });
    }
    return;
  }

  const roll = Math.random();
  if (roll < 0.4) {
    const r = http.post(
      `${BASE}/cases`,
      JSON.stringify({
        summary: `k6 write case ${Date.now()}`,
        crime_type: 'Burglary',
        location_id: randOf(addressIds),
        reported_by: randOf(personIds),
        occurred_at: '2026-01-01',
      }),
      authHeaders
    );
    check(r, { 'open case 201': (res) => res.status === 201 });
  } else if (roll < 0.75 || !officerIds.length) {
    const r = http.patch(
      `${BASE}/cases/${caseId}`,
      JSON.stringify({ summary: `updated by k6 ${Date.now()}` }),
      authHeaders
    );
    check(r, { 'patch case 200': (res) => res.status === 200 });
  } else {
    const r = http.post(`${BASE}/cases/${caseId}/officers/${randOf(officerIds)}`, null, authHeaders);
    check(r, { 'assign officer 200': (res) => res.status === 200 });
  }
}
