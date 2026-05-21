"""
Locust load test file for Red Hat OpenShift AI inference endpoints.

Usage from your Dev Space:
  locust -f common/load/locustfile.py --host=https://your-model-route

Then open the Locust UI (port 8089 is exposed by the devfile).

You can also run headless:
  locust -f common/load/locustfile.py --host=... -u 10 -r 2 --run-time 60s --html report.html
"""

from locust import HttpUser, task, between, events
import json
import os

MODEL_NAME = os.getenv("MODEL_NAME", "tiny-llama")
# For Triton v2
INFER_PATH = os.getenv("INFER_PATH", f"/v2/models/{MODEL_NAME}/infer")
# For NIM / vLLM OpenAI compat set INFER_PATH=/v1/chat/completions and use openai_mode

OPENAI_MODE = os.getenv("OPENAI_MODE", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "dummy")


class InferenceUser(HttpUser):
    wait_time = between(0.1, 0.5)  # aggressive for demo purposes

    @task(10)
    def inference(self):
        if OPENAI_MODE:
            payload = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": "Explain containers in one sentence."}],
                "max_tokens": 32,
                "temperature": 0.7,
            }
            headers = {"Authorization": f"Bearer {API_KEY}"}
            self.client.post("/v1/chat/completions", json=payload, headers=headers, name="/v1/chat/completions")
        else:
            # Triton v2 REST
            payload = {
                "inputs": [{
                    "name": "text_input",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ["Explain containers in one sentence."],
                }]
            }
            self.client.post(INFER_PATH, json=payload, name="/v2/models/.../infer")


# Optional: print nice summary at the end of a run
@events.quitting.add_listener
def _(environment, **kw):
    if not environment.stats.total.num_requests:
        return
    stats = environment.stats.total
    avg = stats.avg_response_time
    p95 = stats.get_response_time_percentile(0.95) or 0
    print(f"\n=== Locust Summary ===\nRPS: {stats.total_rps:.1f} | Avg latency: {avg:.1f} ms | p95: {p95:.1f} ms | Failures: {stats.num_failures}")