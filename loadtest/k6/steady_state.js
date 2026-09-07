/**
 * Steady-state benchmark: 50 VUs for 8 minutes against the FastAPI backend.
 * The headline number. Thresholds are what the fixed 2-task / 256cpu stack
 * should absorb without complaint.
 */
import { setupAuthAndSeedCases, trafficMix } from './lib.js';

export const options = {
  stages: [
    { duration: '2m', target: 50 },
    { duration: '5m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  return setupAuthAndSeedCases();
}

export default function (data) {
  trafficMix(data);
}
