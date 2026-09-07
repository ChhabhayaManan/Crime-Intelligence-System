/**
 * Breaking-point test: ramps to 300 VUs until the fixed-capacity stack
 * degrades. abortOnFail stops the run the moment the SLO breaks instead of
 * burning the full 12 minutes. Read it alongside CloudWatch and RDS metrics
 * for the same window to see which tier gave out first.
 */
import { setupAuthAndSeedCases, trafficMix } from './lib.js';

export const options = {
  stages: [
    { duration: '1m', target: 25 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 75 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 125 },
    { duration: '1m', target: 150 },
    { duration: '1m', target: 175 },
    { duration: '1m', target: 200 },
    { duration: '1m', target: 225 },
    { duration: '1m', target: 250 },
    { duration: '1m', target: 275 },
    { duration: '1m', target: 300 },
  ],
  thresholds: {
    http_req_duration: [{ threshold: 'p(95)<1000', abortOnFail: true }],
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true }],
  },
};

export function setup() {
  return setupAuthAndSeedCases();
}

export default function (data) {
  trafficMix(data);
}
