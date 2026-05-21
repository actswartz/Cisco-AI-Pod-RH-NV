# Module 03 — Batching, Caching, and Queuing (Student Lab)

**Time:** 55–70 minutes (the most technical and valuable hands-on module of the workshop)

---

## Objectives

By the end of this module you will be able to:

- Explain why the default `max_batch_size: 1` causes catastrophic tail latency under realistic concurrency
- Configure and observe the benefits of **dynamic batching** (preferred batch sizes + queue delay) in Triton
- Demonstrate **response caching** and measure the dramatic latency reduction on cache hits
- Capture and compare quantitative performance metrics (average latency, p95, effective RPS) before and after tuning
- Understand that the majority of production LLM serving gains come from smart runtime configuration — not just bigger GPUs or more replicas

This module turns the "magic" of fast chatbots and RAG systems into something you can measure and control.

---

## Prerequisites

- You have successfully completed **Module 02** and still have your personal baseline numbers (avg + p95 from the low-concurrency run).
- Your Dev Space terminal is ready.
- The model deployed in Module 02 is still running and reachable (your instructor will confirm).
- You have the following environment variables ready (set them now if you cleared your terminal):

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate

export MODEL_ROUTE="https://<instructor-gives-you-this>"
export MODEL_NAME="<instructor-gives-you-this>"

echo "Route: $MODEL_ROUTE"
echo "Model:  $MODEL_NAME"
```

Quick connectivity check (should succeed with HTTP 200 or model metadata):

```bash
curl -I "$MODEL_ROUTE/v2/health/ready" || curl -I "$MODEL_ROUTE/v1/models"
```

> **Tip:** Keep these exports in your terminal for the entire lab. If you open a new terminal tab, re-run the three `export` lines above.

---

## Why This Experiment Matters

Real user traffic is never one request at a time. Production workloads routinely see 10–200 concurrent users. When every request is processed in complete isolation (`max_batch_size: 1`), the server is forced to **serialize** work. Each new request waits in a queue behind the previous ones, causing p95 (tail) latency to explode even when average latency looks acceptable.

Dynamic batching + response caching is how real systems (Triton, vLLM, TensorRT-LLM, NIM, etc.) achieve high throughput while keeping user-visible latency low.

Today you will experience the **before vs after** transformation live.

---

## Step 1: Observe the "Bad Default" — max_batch_size = 1

Your instructor will first show the current live configuration of the model (either via the OpenShift AI dashboard, `oc get inferenceservice`, or by displaying the `config.pbtxt` in the model repository).

**Look for this line:**

```pbtxt
max_batch_size: 1
```

There will be **no** `dynamic_batching { ... }` stanza and no `response_cache`.

This is the conservative default that many demos accidentally ship with.

### Run the Painful Baseline (10 concurrent users)

Run the **exact same load test** your instructor asks the whole class to execute. Use a short prompt so the model finishes quickly and the queuing effect is obvious:

```bash
python common/client/concurrent_load.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "Explain Kubernetes in one sentence." \
  --concurrency 10 \
  --requests 30
```

Watch the output carefully. The tool will print a rich table with:

- Average latency
- p50 / p95 latencies
- Effective requests per second (RPS) based on wall-clock time

**Record your numbers** in the data capture table below (row "Bad default (batch=1)").

> **What you will likely see:** Even with a fast model, p95 latency can be 5–15× worse than a single request. Many requests queue up and wait for the previous one to finish. This is the "death by a thousand cuts" that users feel as sluggish chat responses.

---

## Step 2: Enable Dynamic Batching — The "Aha!" Moment

Your instructor will now perform the live configuration change. There are two common approaches the instructor may use:

**Option A (most common for teaching):** Edit the `config.pbtxt` inside the model repository (S3 bucket, PVC, or ConfigMap) and trigger a reload/redeploy of the InferenceService.

**Option B:** Switch the InferenceService to a pre-prepared ServingRuntime that already has dynamic batching arguments.

### The Target Configuration

After the change, the relevant section of `config.pbtxt` will look approximately like this:

```pbtxt
max_batch_size: 8

dynamic_batching {
  preferred_batch_size: [ 4, 8 ]
  max_queue_delay_microseconds: 5000
}
```

**What these settings mean:**

| Setting                              | Purpose |
|--------------------------------------|---------|
| `max_batch_size: 8`                  | Triton is allowed to form batches up to 8 requests |
| `preferred_batch_size: [4, 8]`       | Triton tries hard to form batches of these sizes before executing |
| `max_queue_delay_microseconds: 5000` | Never wait more than 5 ms to form a batch (protects tail latency) |

While the model redeploys (pods will go `Terminating` → new pods `Pending`/`Running`), you can watch progress:

```bash
# If you have view access to the project namespace
oc get pods -w -n <your-project-name>

# Or simply watch the InferenceService status
oc get inferenceservice -w
```

Your instructor will announce when the new pods are `Running` and `Ready`.

### Re-run the Identical Load Test

Once the model is ready, run the **exact same command** again:

```bash
python common/client/concurrent_load.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "Explain Kubernetes in one sentence." \
  --concurrency 10 \
  --requests 30
```

**Record the new numbers** in the "After dynamic batching" row.

**Expected observations (typical results):**

- Average latency often **drops** even though we are doing more work per GPU execution
- p95 latency improves dramatically (commonly 2–8× reduction)
- Effective RPS **increases** significantly
- The system feels much more "elastic" under load

This is the core insight of the workshop: **configuration inside the runtime frequently delivers larger gains than adding more GPUs**.

---

## Step 3: Add Response Caching — Instant Second Answers

Response caching is the second "magic" lever. When the exact same prompt (or a semantically identical one, depending on implementation) arrives again, Triton can return the previously computed response in microseconds without ever touching the model weights.

### Instructor Enables the Cache

Your instructor will add the following stanza (usually in the same `config.pbtxt` edit or reload):

```pbtxt
response_cache {
  enable: true
}
```

After the model reloads, perform two powerful demonstrations.

### Demo A — Single Prompt, Repeated (Cache Hit Magic)

Run the **identical prompt twice in a row** using the single-request client with timing:

```bash
python common/client/triton_infer.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "What is the capital of France?" \
  -v
```

Copy the latency. Then immediately run the **exact same command again**.

On the second run you will typically see latency collapse to **< 30 ms** (often single-digit milliseconds). The second request never reached the GPU — it was served straight from Triton's in-memory response cache.

Run it a few more times with `--times 5` to see the pattern:

```bash
python common/client/triton_infer.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "What is the capital of France?" \
  --times 5
```

### Demo B — Cache Miss vs Hit Under Load (Optional but Powerful)

1. Run five **identical** prompts in quick succession and record the first vs. subsequent latencies.
2. Then run five **different** prompts and observe that every request pays the full price (cache misses).

This directly explains why well-designed RAG chatbots and conversational agents feel snappy on follow-up turns.

**Record any cache-related observations** in the Notes column of your table.

---

## Step 4: Your Own Experiments (15 minutes)

Now it is your turn. Using the same two commands, explore the following (always keep the prompt and request count consistent when comparing):

- Increase concurrency: try `--concurrency 20` and even `30` (if the cluster allows).
- Lower the queue delay (instructor may allow one more edit) and observe the p95 vs. throughput trade-off.
- Mix cache-friendly and cache-unfriendly traffic.
- Try the OpenAI-compatible client if your model exposes `/v1/chat/completions`:

  ```bash
  python common/client/concurrent_load.py \
    --url $MODEL_ROUTE/v1 \
    --model $MODEL_NAME \
    --prompt "Hi" \
    --concurrency 8 \
    --requests 20 \
    --openai
  ```

Document your best configuration and the metrics it produced.

---

## Data Capture Table — Your Quantitative Results

**Fill this table during the lab.** Use the exact same prompt and request count across rows for fair comparison whenever possible.

| Phase                        | Concurrency | Requests | Avg Latency (ms) | p95 Latency (ms) | Effective RPS | Notes / Observations |
|------------------------------|-------------|----------|------------------|------------------|---------------|----------------------|
| Module 02 baseline           | 3           | 15       |                  |                  |               | From previous lab |
| Bad default (`max_batch_size: 1`) | 10     | 30       |                  |                  |               | Serialized queuing pain |
| After dynamic batching       | 10          | 30       |                  |                  |               | Preferred batches + queue delay |
| Dynamic batching + cache     | 10          | 30       |                  |                  |               | Cache hits on repeated prompts |
| Your best run (record config) | ___       | ___      |                  |                  |               | What settings produced this? |
| Experiment: conc=20          | 20          | 30       |                  |                  |               | Higher load test |
| Cache hit demo (single prompt repeated) | 1 | 5 | (first)          | (subsequent)     | —             | Use `triton_infer.py --times 5` |

**Also note the exact `config.pbtxt` snippet** your instructor ended up with (ask them to share it or screenshot it):

```pbtxt
# Paste the final working configuration here for your notes
```

---

## Reflection Questions

Answer these in your notes or discuss with a neighbor:

1. Why does p95 (tail) latency matter far more for user experience than average latency in a chatbot or RAG application?

2. What is the fundamental trade-off controlled by `max_queue_delay_microseconds`? What happens if you set it extremely low? Extremely high?

3. In a real RAG system, would you expect a higher or lower cache hit rate on the second turn of a conversation? Why?

4. Your instructor changed only configuration — no code, no extra GPUs. What does this tell you about where the biggest wins usually hide in production LLM deployments?

5. If you had to choose between (a) doubling the number of replicas or (b) enabling well-tuned dynamic batching + cache, which would you try first and why?

---

## Troubleshooting

| Problem                              | Likely Cause & Fix |
|--------------------------------------|--------------------|
| Load test shows very high errors or timeouts | Model pod is still deploying or crashed. Wait for `Ready` status and check `oc describe pod` or dashboard logs. |
| Second identical prompt is not dramatically faster | Cache was not enabled, or the model was reloaded after you ran the first request, or the prompt differs by even one character/whitespace. Re-run after confirming cache stanza is present. |
| `oc` commands fail with permission errors | You may not have direct project access. Ask your instructor to share pod status or perform the `oc get pods -w` in their terminal and narrate. |
| Exports are lost after new terminal | Re-run the `cd`, `source`, and two `export` lines at the top of the Setup section. |
| Numbers look almost identical before/after | Concurrency may be too low to expose the bottleneck, or the model is extremely fast even serialized. Ask instructor to increase `--concurrency` to 15–20 or use a slightly heavier prompt. |
| `concurrent_load.py` reports 0 successful requests | Check that `$MODEL_ROUTE` and `$MODEL_NAME` are correct and that the model still serves a basic single request with `triton_infer.py`. |

If the model is CPU-only (lightweight path), absolute numbers will be higher but the **relative improvement** from batching is usually even more dramatic and easier to see.

---

## Success Checkpoint

You have successfully completed Module 03 when you can:

- [ ] Show your filled data capture table with at least one clear "before" and "after" comparison (ideally p95 improvement of 2× or more).
- [ ] Explain in your own words what `dynamic_batching` and `response_cache` do inside Triton.
- [ ] Demonstrate (or describe) the instant cache-hit effect with an identical prompt run twice.
- [ ] State the exact `config.pbtxt` settings that produced your best numbers.
- [ ] Articulate why configuration tuning often beats "throw more hardware at it."

**Congratulations!** You now understand the single most important performance lever in production LLM inference serving.

---

## What's Next

In **Module 04 — Load Balancing & Traffic Management** we will take the now-healthy batched model and deliberately stress it with many more replicas and real traffic shaping using OpenShift Routes and load generators (`hey`, `k6`, `locust`).

Keep your best numbers handy — we will continue to beat them throughout the day.

---

**End of Module 03 Student Lab**

*Reference artifacts: `common/client/concurrent_load.py`, `common/client/triton_infer.py`, `common/yamls/triton-dynamic-batching.yaml`*
