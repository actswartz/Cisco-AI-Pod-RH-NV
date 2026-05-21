// k6 load test script for OpenShift AI inference demos
// Run with: k6 run common/load/k6-script.js
//
// Set the target via environment variables:
//   export MODEL_ROUTE=https://your-route
//   export MODEL_NAME=tiny-llama
//   k6 run -e MODEL_ROUTE=... common/load/k6-script.js

import http from 'k6/http';
import { check, sleep } from 'k6';

const MODEL_ROUTE = __ENV.MODEL_ROUTE || 'https://replace-me';
const MODEL_NAME = __ENV.MODEL_NAME || 'tiny-llama';
const OPENAI_MODE = __ENV.OPENAI_MODE === 'true';

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // ramp-up
    { duration: '60s', target: 20 },  // steady load for demo
    { duration: '20s', target: 0 },   // ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'], // 5s is generous for first-time cold models
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  let url, payload, params;

  if (OPENAI_MODE) {
    url = `${MODEL_ROUTE}/v1/chat/completions`;
    payload = JSON.stringify({
      model: MODEL_NAME,
      messages: [{ role: 'user', content: 'Explain OpenShift in one sentence.' }],
      max_tokens: 32,
    });
    params = { headers: { 'Content-Type': 'application/json', Authorization: 'Bearer dummy' } };
  } else {
    // Triton v2
    url = `${MODEL_ROUTE}/v2/models/${MODEL_NAME}/infer`;
    payload = JSON.stringify({
      inputs: [{
        name: 'text_input',
        shape: [1],
        datatype: 'BYTES',
        data: ['Explain OpenShift in one sentence.'],
      }],
    });
    params = { headers: { 'Content-Type': 'application/json' } };
  }

  const res = http.post(url, payload, params);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has response body': (r) => r.body && r.body.length > 0,
  });

  sleep(0.2);
}