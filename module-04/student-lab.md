# Module 04 — Load Balancing and Traffic Optimization (Student Lab)

**Time:** 30–45 minutes of active work

---

## Your Mission

Prove that a single external Route can automatically distribute inference traffic across multiple model server pods. You will:

- Inspect a running inference deployment at 1 replica
- Scale it to 3 replicas (via dashboard or `oc`)
- Fire sustained load from your Dev Space
- Watch live per-pod metrics in OpenShift Observe and see traffic split evenly
- Capture quantitative before/after numbers (replica count + RPS)

**Teaching point:** Clients never change. The OpenShift Route + Kubernetes Service + KServe predictor handles everything.

---

## Setup (Run This First)

Open a terminal in your Dev Space and run:

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate

export MODEL_ROUTE="https://<instructor-gives-you-this>"
export MODEL_NAME="<instructor-gives-you-this>"
export NS="<instructor-gives-you-this>"     # e.g. rhoai-demos or your project name

echo "Route : $MODEL_ROUTE"
echo "Model : $MODEL_NAME"
echo "Namespace: $NS"
```

### Quick Health Check

```bash
curl -I "$MODEL_ROUTE/v2/health/ready" || curl -I "$MODEL_ROUTE/v1/models" || true
```

You should get a `200` response (or a short JSON list for OpenAI-style endpoints).

---

## Task 1: Baseline — Current State (1 Replica)

### 1.1 Discover and Record Current Replica Count

Run these discovery commands:

```bash
# 1. Show the InferenceService
oc get inferenceservice $MODEL_NAME -n $NS -o wide

# 2. Find the exact predictor Deployment name
echo "=== Predictor Deployments ==="
oc get deployment -n $NS -l serving.kserve.io/inferenceservice=$MODEL_NAME

# 3. List current pods (should be 1)
echo "=== Current Pods ==="
oc get pods -n $NS -l serving.kserve.io/inferenceservice=$MODEL_NAME -o wide

# 4. Show endpoints (how many backends the Route sees)
echo "=== Endpoints (backends behind the Service) ==="
oc get endpoints -n $NS | grep -E "$MODEL_NAME|predictor" || oc get endpoints -n $NS
```

**Record the baseline (write it down or paste into a scratch file):**

- Replica count (from Deployment `READY` column): **1**
- Number of pods in `Running` + `Ready`: **__**
- Deployment name (you will need this for scaling): `______________________________`

### 1.2 Run a Quick Load Test (1 Replica) and Capture RPS

**Recommended first tool: Python concurrent loader** (clean table + exact RPS)

```bash
# Triton v2 path (most custom runtimes)
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Explain horizontal scaling for LLM serving in one sentence." \
  --concurrency 8 \
  --requests 80
```

**For OpenAI-compatible models** (NVIDIA NIM, vLLM, etc.) add `--openai`:

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Explain horizontal scaling for LLM serving in one sentence." \
  --concurrency 8 \
  --requests 80 \
  --openai
```

**Alternative: Classic `hey` burst (the command highlighted in the workshop)**

```bash
# Triton v2 version
PAYLOAD='{"inputs":[{"name":"text_input","shape":[1],"datatype":"BYTES","data":["Explain horizontal scaling for LLM serving in one sentence."]}]}'

hey -n 600 -c 12 \
  -m POST \
  -T "application/json" \
  -d "$PAYLOAD" \
  "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer"
```

```bash
# OpenAI-compatible version
PAYLOAD='{"model":"'$MODEL_NAME'","messages":[{"role":"user","content":"Explain horizontal scaling for LLM serving in one sentence."}],"max_tokens":48}'

hey -n 600 -c 12 \
  -m POST \
  -T "application/json" \
  -H "Authorization: Bearer dummy" \
  -d "$PAYLOAD" \
  "$MODEL_ROUTE/v1/chat/completions"
```

**Alternative sustained pattern: k6 (great for watching live graphs)**

```bash
k6 run -e MODEL_ROUTE="$MODEL_ROUTE" \
       -e MODEL_NAME="$MODEL_NAME" \
       -e OPENAI_MODE="false" \
       common/load/k6-script.js
```

(Change `OPENAI_MODE="true"` if your model uses the `/v1/chat/completions` path.)

**Capture these numbers from the tool output (1 replica):**

- Effective / Requests per second (RPS): **________**
- Average latency (ms): **________**
- p95 latency (ms) if shown: **________**
- Any errors?: **________**

> **Tip:** Open a second terminal tab (`Terminal → New Terminal` or split view) and keep `oc get pods -n $NS -l serving.kserve.io/inferenceservice=$MODEL_NAME -w` running while you test. Watch for changes later.

---

## Task 2: Scale to 3 Replicas

Your instructor will usually demonstrate scaling live in the OpenShift AI dashboard or OpenShift Console. You will then verify with `oc`.

### Option A — Scale via OpenShift AI Dashboard (Recommended for Demo)

1. Open the **Red Hat OpenShift AI** dashboard.
2. Go to your project (`$NS`).
3. Find the model / InferenceService row for `$MODEL_NAME`.
4. Edit the deployment (look for “Edit” or the replica count control) and set **Model server replicas** to `3`.
5. Save / redeploy. Watch the status change from 1/1 → 3/3.

### Option B — Scale via CLI (`oc scale`)

```bash
# Use the deployment name you recorded in Task 1
DEPLOYMENT="<paste-the-deployment-name-here>"

# Scale it
oc scale deployment/$DEPLOYMENT --replicas=3 -n $NS

# Watch the new pods come up in real time (Ctrl-C when done)
oc get pods -n $NS -l serving.kserve.io/inferenceservice=$MODEL_NAME -w
```

After the watch shows 3 pods `Running` and `1/1 Ready`, re-run the inspection commands from Task 1.1.

**Record after scaling:**

- Replica count now: **3**
- Pods in `Running` + `Ready`: **__ / 3**
- All pods show the same model revision / image? (yes/no)

Confirm the Route still works:

```bash
curl -I "$MODEL_ROUTE/v2/health/ready" || curl -I "$MODEL_ROUTE/v1/models"
```

The health check should still succeed — the Route never changed.

---

## Task 3: Sustained Load + Live Metrics Observation (3 Replicas)

This is the heart of the module.

### 3.1 Start a Sustained Load

In one terminal, start a longer-running load generator so you have time to watch the UI:

**Best choice for live observation: k6 (has nice ramp + 60s steady phase)**

```bash
k6 run -e MODEL_ROUTE="$MODEL_ROUTE" \
       -e MODEL_NAME="$MODEL_NAME" \
       -e OPENAI_MODE="false" \
       common/load/k6-script.js
```

(For OpenAI models: `-e OPENAI_MODE="true"`)

**Or a longer hey burst (Triton v2 example — define payload first):**

```bash
# Define payload (Triton)
PAYLOAD='{"inputs":[{"name":"text_input","shape":[1],"datatype":"BYTES","data":["Explain horizontal scaling for LLM serving in one sentence."]}]}'

hey -n 2000 -c 25 \
  -m POST \
  -T "application/json" \
  -d "$PAYLOAD" \
  "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer"
```

(For OpenAI-compatible endpoints, use the OpenAI-style payload + `-H "Authorization: Bearer dummy"` exactly as shown in Task 1.2.)

While the load is running, **do not stop it yet**.

### 3.2 Observe Traffic Distribution in OpenShift Observe

1. Open (or switch to) a browser tab with the **OpenShift Console**.
2. Make sure you are in project **`$NS`**.
3. Go to **Observe → Metrics** (left sidebar).
4. In the query / metric browser:
   - Search for `CPU` or `container_cpu_usage_seconds_total` or `http_requests` / KServe metrics.
   - Or use the **pod** dropdown / label selector.
5. **Filter or select only the pods belonging to your model** (their names contain `$MODEL_NAME` or the predictor name).
6. Pin 2–3 graphs:
   - Request rate or throughput per pod
   - CPU usage per pod
   - (If available) inference latency or queue depth

**What you should see:**

- Three distinct lines (one per pod) instead of one.
- The lines are roughly the **same height** — traffic is being load-balanced.
- No single pod is carrying 100% of the load.
- As load continues, the graphs stay balanced.

Take a screenshot or note the visual pattern.

> **Pro tip:** If the graphs are empty, try the “Custom query” box and type a simple selector like:
> `container_cpu_usage_seconds_total{container="kserve-container", pod=~".*your-model.*"}`

### 3.3 Capture After Numbers

Once you have observed the split, run the **exact same quick load command** you used in Task 1.2 (same concurrency + request count) and record the new numbers.

**Record the 3-replica results:**

- RPS (Requests/sec): **________**   (compare to the 1-replica value)
- Average latency: **________**
- p95 latency: **________**
- Did RPS increase, stay similar, or become more stable? ____________________

Stop the sustained load generator (Ctrl-C).

---

## Observation Checklist

Fill this out as you go. These numbers and observations are what you will discuss with your team and instructor.

**1 Replica (Before Scaling)**

| Item                    | Value                  | Notes / Observations                          |
|-------------------------|------------------------|-----------------------------------------------|
| Ready replicas          | 1                      |                                               |
| Pods visible (`oc get`) |                        |                                               |
| RPS from hey / k6 / Python |                    |                                               |
| Avg latency             |                        |                                               |
| p95 latency             |                        |                                               |
| Metrics view (pod graph)| All traffic on 1 line  |                                               |

**3 Replicas (After Scaling)**

| Item                    | Value                  | Notes / Observations                                      |
|-------------------------|------------------------|-----------------------------------------------------------|
| Ready replicas          | 3                      |                                                           |
| Pods visible            |                        | All three should be Running/Ready                         |
| RPS from load tool      |                        | Higher capacity or more stable?                           |
| Avg latency             |                        | Usually similar or slightly better                        |
| p95 latency             |                        |                                                           |
| Metrics view            | 3 lines, balanced      | Traffic visibly split across pods? Yes / No / Partial     |
| Any errors during scale |                        |                                                           |

---

## Reflection Questions

Answer these (discuss with a neighbor or the class):

1. Why didn’t you have to change the `MODEL_ROUTE` or any client code when the replica count changed?
2. Which OpenShift / Kubernetes objects are responsible for spreading the requests? (Route, Service, Endpoints, kube-proxy…)
3. What would happen to a single client if one of the three pods became slow or crashed?
4. How does this pattern help when traffic spikes at 2 a.m. or during a product launch?
5. (Advanced) Where would you look next if you wanted **automatic** scaling instead of manual `oc scale`? (Hint: look at HPA or KServe autoscaler in later modules.)

---

## What Success Looks Like

- You can confidently run `oc get pods -l serving.kserve.io/inferenceservice=...` and interpret the output
- You have run load, watched the metrics dashboard update live, and seen the traffic split across three pods
- You have written down real before/after RPS and replica numbers from **your own** Dev Space session
- You can explain to someone: “One Route + multiple pods = automatic load balancing with zero client changes”

**Checkpoint complete.**  
You now understand horizontal scaling and OpenShift traffic distribution for inference workloads.

---

## Lightweight / CPU-Only Path

Everything in this lab works identically when the model is running on CPU-only replicas (using the `triton-cpu-lightweight` ServingRuntime or a simple vLLM CPU deployment). The scaling behavior, Route balancing, and per-pod metrics are exactly the same. Use this module early if GPUs are scarce — the teaching signal is extremely clear.

---

**You are ready for Module 05 — GPU Scheduling & Hardware Profiles.**

Bring your recorded numbers and the mental model of “Route in front, N identical pods behind it” with you.
