/**
 * Smoke check for the Streamlit tier. The frontend ALB is public, so this
 * runs from a laptop rather than an in-VPC task:
 *
 *   k6 run -e TARGET_URL=http://<frontend-alb-dns> loadtest/k6/smoke_frontend.js
 *
 * Streamlit keeps a per-session websocket, so this is not a user-interaction
 * load test. It only shows the tier serves concurrent page loads.
 */
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.TARGET_URL || 'http://localhost:8501';

export const options = {
  vus: 20,
  duration: '1m',
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get(BASE);
  check(res, { 'status 200': (r) => r.status === 200 });
}
