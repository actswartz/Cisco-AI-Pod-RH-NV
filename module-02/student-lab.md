# Module 02 — First Inference from the Workspace (Student Lab)

**Estimated Time:** 40–50 minutes of active hands-on work  
**Prerequisites:** Successful completion of Module 01 (Dev Space running, `MODEL_ROUTE` and `MODEL_NAME` exported, first validation request completed)  
**Goal:** Turn the abstract “inference pipeline” into a concrete, timestamped, observable reality by executing requests while watching every stage in the Red Hat OpenShift AI logs and metrics.

---

## Lab Objectives

By the end of this lab you will be able to:

- Reliably export and validate the two environment variables (`MODEL_ROUTE` and `MODEL_NAME`) required for every exercise in the workshop.
- Execute raw Triton v2 REST and OpenAI-compatible requests using `curl` and the reusable Python clients, and interpret the JSON responses.
- Perform side-by-side observation: run an inference from the Dev Space terminal while watching live preprocess → inference → postprocess logs in the OpenShift AI dashboard.
- Capture repeatable baseline latency numbers (avg, p50, p95) using the `concurrent_load.py` tool under light load.
- Distinguish between “time to first token” (streaming) and full-response latency, and explain why this matters for user experience.
- Document the exact numbers and observations that will be compared after we enable dynamic batching, caching, and scaling in Modules 03 and 04.
- Explain why the same client commands work whether the backend is a custom Triton runtime or an NVIDIA NIM deployment.

---

## Prerequisites & Environment Setup

You must have:

- A running Dev Space from Module 01 with the Python venv activated.
- The two environment variables from the previous module still set (or you will re-export them now).
- The Red Hat OpenShift AI dashboard open in a second browser tab, with the model’s **Logs** tab visible.
- The baseline capture table you started in Module 01.

**Re-activate and confirm your variables (do this every time you open a new terminal):**

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate

# Re-export if they were lost (instructor will remind you of the exact values)
export MODEL_ROUTE="https://<your-model-route-from-dashboard>"
export MODEL_NAME="<exact-model-name>"

echo "✅ Route: $MODEL_ROUTE"
echo "✅ Model: $MODEL_NAME"
```

---

## Step 1: Re-Verify Connectivity & Health

Before any inference, always confirm the model is reachable:

```bash
# Triton health (most common for custom runtimes)
curl -I "$MODEL_ROUTE/v2/health/ready"

# OpenAI-compatible health (NIM, vLLM, TGIS)
curl -I "$MODEL_ROUTE/v1/models" || echo "(OpenAI path may return 404 if not enabled – that is OK)"
```

**Expected result:** `HTTP/2 200 OK` (or a JSON list of models).  
If you see 403/401, ask your instructor for an authentication token and export it:

```bash
export INFERENCE_TOKEN="your-token-here"
# Most classroom models accept a dummy token or run with auth disabled
```

---

## Step 2: Raw curl – See Exactly What Travels Over the Wire

Run the following Triton v2 request. This is the lowest-level view you will ever use:

```bash
curl -s -X POST "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "text_input",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["Explain containers in exactly one sentence."]
    }]
  }' | jq .
```

**While the command runs, watch the model Logs tab in the dashboard.**

**Observe / Note this:**
- The exact timestamp the HTTP handler receives the request.
- Any tokenization or preprocessing messages.
- The moment the actual model forward pass (the “thinking”) begins.
- Post-processing / detokenization.
- The response being returned to the caller.

Copy the full JSON response (or at least the generated text) into your notes. Note any `output` tensors or timing fields the runtime provides.

Repeat the curl **once more** immediately:

```bash
# Second identical request – often faster due to any internal caching
curl -s -X POST "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "text_input",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["Explain containers in exactly one sentence."]
    }]
  }' | jq '. | {text: .outputs[0].data[0], timing: .}'
```

Record the wall-clock time difference between the two calls.

---

## Step 3: The Reusable Triton Client (Your Daily Driver)

The script `common/client/triton_infer.py` wraps the same REST call with timing, pretty printing, and repeat support.

```bash
python common/client/triton_infer.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "What is the difference between Red Hat OpenShift and Kubernetes?" \
  -v \
  --times 3
```

**Run this while keeping the Logs tab visible on the left half of your screen** (or second monitor).

**What to narrate to yourself or a neighbor:**
- “Request left my terminal at …”
- “Pod received it at … (look for the first log line)”
- “Preprocessing finished at …”
- “Inference (model execution) started …”
- “First token / full generation finished at …”
- “Response returned to client at …”

The client will print a clean summary:

```
[bold]Stats[/bold] — avg: XX.X ms | p95: YY.Y ms | min/max: ...
```

**Expected result:** Three successful responses, decreasing or stable latency after the first call, and visible log activity in the dashboard.

---

## Step 4: OpenAI-Compatible Path (NIM / vLLM / TGIS Deployments)

If your model was deployed with an OpenAI-compatible runtime (very common for production Llama-3 / Phi-3 / Mistral via NVIDIA NIM), use the dedicated client:

```bash
python common/client/openai_infer.py \
  --base-url "$MODEL_ROUTE/v1" \
  --model "$MODEL_NAME" \
  --prompt "List three concrete benefits of running LLM inference on Red Hat OpenShift AI instead of a laptop." \
  --system "You are a concise, helpful Red Hat solutions architect." \
  --max-tokens 128 \
  --temperature 0.6 \
  --stream \
  --times 2
```

**Observe how streaming changes the experience:**
- The first tokens appear almost immediately (time-to-first-token).
- The rest of the answer fills in while you watch.
- Compare the total latency number printed at the end with the non-streaming feel.

Run the same prompt **without** `--stream` once so you can feel the difference:

```bash
python common/client/openai_infer.py \
  --base-url "$MODEL_ROUTE/v1" \
  --model "$MODEL_NAME" \
  --prompt "List three concrete benefits of running LLM inference on Red Hat OpenShift AI instead of a laptop." \
  --times 1
```

> **Key Insight:** The client code changed, but the Route, KServe, pod scaling, GPU scheduling, and observability layers stayed **exactly the same**. This is the power of the Red Hat OpenShift AI serving stack.

---

## Step 5: Side-by-Side Live Observation Exercise (Most Important 8–10 Minutes of the Module)

This is the moment the pipeline becomes real.

**Setup (recommended):**
1. Split your screen or use two monitors.
2. Left: OpenShift AI dashboard → your model → **Logs** tab (set to live / follow if possible).
3. Right: Your Dev Space terminal.

**Run the following command (use the Triton client or the exact curl you prefer):**

```bash
python common/client/triton_infer.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Describe the request path from a Dev Space to a GPU in Red Hat OpenShift AI using exactly 12 words." \
  -v
```

As soon as you press Enter, **narrate out loud** (or type into chat) the exact sequence you see:

- HTTP request timestamp in terminal
- First log line appearance in the pod
- Preprocess complete
- “Inference started” or equivalent
- Tokens being generated (or a single batch inference line)
- Response sent back
- Client receives and prints the answer + latency

Do this **twice** with different prompts. The second run usually shows clearer internal timing because caches are warm.

**Instructor will often pause here** for the whole class to share one observation each.

---

## Step 6: Capture Your Official Baseline Numbers

We need repeatable, comparable metrics before we start tuning.

Run the concurrent loader with a very modest load (this is your “before” picture):

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Hi there, this is a baseline test." \
  --concurrency 3 \
  --requests 15
```

If your deployment supports the OpenAI path and you want a second data point:

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Hi there, this is a baseline test." \
  --concurrency 3 \
  --requests 15 \
  --openai
```

**What to Capture / Write Down** (expand the table you started in Module 01):

| Metric                        | Triton Path Value | OpenAI Path Value (if applicable) | Command / Notes                          | Target for Future Modules |
|-------------------------------|-------------------|-----------------------------------|------------------------------------------|---------------------------|
| Avg latency (light load)      | ___ ms            | ___ ms                            | concurrent_load.py                       | Beat with dynamic batching |
| p50 latency                   | ___ ms            | ___ ms                            | Printed in stats table                   | —                         |
| p95 latency                   | ___ ms            | ___ ms                            | —                                        | Key SLO for Module 04     |
| # of successful requests      | 15 / 15           | 15 / 15                           | Look for “Successful (200)”              | —                         |
| Errors observed               | 0                 | 0                                 | First error sample line                  | Should stay zero          |
| Wall-clock time for the run   | ___ s             | ___ s                             | Printed at bottom of output              | Effective RPS calculation |
| Time-to-first-token (feel)    | N/A               | Noticeably faster with --stream   | Streaming run observation                | UX metric for Module 08   |

**Store these numbers safely.** Every future module will ask “Did we beat the Module 02 baseline?”

---

## Step 7: Quick Experiment – Cold vs Warm Requests

Run the Triton client with a brand-new prompt you have never used:

```bash
python common/client/triton_infer.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "What is the capital of Australia and why is it not the largest city?" \
  -v
```

Immediately run it **again** with the exact same prompt:

```bash
python common/client/triton_infer.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "What is the capital of Australia and why is it not the largest city?" \
  -v
```

**Record the latency difference.** This difference is often the first thing that improves dramatically once we enable the Triton response cache in Module 03.

---

## Reflection & Key Takeaways

Take 3 minutes to answer in your notes:

1. Which stage of the pipeline (preprocess, inference, postprocess) usually dominates the latency you observed? How could you confirm this with the logs?
2. Why does a single OpenShift Route + KServe layer give us both a simple developer experience **and** production resilience at the same time?
3. When you used `--stream`, what changed in the user-perceived experience versus total latency? Why does this matter for chatbot-style applications?
4. Look at your p95 number from the concurrent load. If this model were serving real users, what would a p95 of that value imply for the 95th percentile user?

Be ready to share your most surprising observation when the instructor asks the room.

---

## Troubleshooting Common Issues

| Problem                                      | Diagnosis & Resolution |
|----------------------------------------------|------------------------|
| Second request is **slower** than the first  | Possible cold model reload or tokenization cache miss. Run `--times 5` and watch whether it stabilizes. |
| Logs tab shows nothing even though curl succeeds | You may be looking at the wrong pod or the model uses a different container name. Ask instructor to point out the correct pod in the OpenShift Console (Workloads → Pods). |
| `concurrent_load.py` reports many errors     | Concurrency too high for current replica count (1 replica under heavy concurrent load can queue or timeout). Reduce `--concurrency` to 2 for now. |
| Streaming output appears garbled             | Terminal width or rich library interaction. Run without `--stream` first, then try again. |
| `MODEL_NAME` mismatch error in Triton client | The name inside the runtime (often the folder name under `/mnt/models`) must match exactly what you pass with `--model`. Check the dashboard or `oc get inferenceservice` output. |
| Very high latency on CPU-only lightweight path | Expected. A 200–800 ms “thinking” time is normal for the teaching model. Focus on the pipeline visibility, not absolute speed. |

---

## Checkpoint / Success Criteria

You are ready for Module 03 when you can truthfully check every box:

- [ ] `MODEL_ROUTE` and `MODEL_NAME` are exported and health checks pass in both Triton and (if applicable) OpenAI paths.
- [ ] You successfully executed raw `curl`, `triton_infer.py`, and `openai_infer.py` (with and without streaming) and received coherent model output each time.
- [ ] You performed at least one side-by-side observation session, watching live logs while a request executed, and can describe the major stages with timestamps.
- [ ] You have a completed baseline table (avg / p50 / p95, successful requests, wall time) from `concurrent_load.py` under light load.
- [ ] You observed and recorded a measurable difference between first (cold) and second (warm) identical requests.
- [ ] You can explain, in your own words, why changing the client library does **not** require any change to the OpenShift Route, KServe, or runtime configuration.

**Excellent work.** You now have concrete, personal numbers and a visceral understanding of the pipeline. In the next module we will deliberately mis-configure batching, watch latency explode, then fix it live with dynamic batching and response caching — and beat every number on your Module 02 baseline table.

---

**Proceed to Module 03 — Batching, Caching, and Queuing.**

Keep your terminal, the two environment variables, and your baseline table open. We are about to make the model dramatically faster.

---

*End of Module 02 Student Lab*  
*Red Hat OpenShift AI – Scalable LLM Inference Demos Workshop*
