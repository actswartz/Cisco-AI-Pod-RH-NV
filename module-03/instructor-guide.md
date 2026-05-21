# Module 03 — Batching, Caching, and Queuing (Instructor Guide)

**Duration:** 55–70 minutes (the most technical and valuable module of the day)  
**Goal:** Students leave understanding exactly why production LLM servers use dynamic batching and response caching, and how to configure them on OpenShift AI.

---

## Why This Module Matters

Most "AI demos" show one request at a time. Real workloads are 20–200 concurrent users. The difference between a model that can handle that load and one that collapses is almost entirely **batching + caching + queuing** configuration inside the runtime (Triton in this case).

---

## Pre-Class Preparation

- Model from Module 02 still running
- You have admin or edit rights on the ServingRuntime (or you pre-created two versions: `triton-batch-1` and `triton-batch-8`)
- The model repository contains a `config.pbtxt` you can edit live (easiest) or you edit the ServingRuntime args
- Students have their baseline numbers from Module 02

---

## The Demo Script (Live Editing)

### Phase 1 — "The Bad Default" (max_batch_size = 1)

1. Show the current model config (either in the dashboard or `oc get inferenceservice -o yaml`).

2. If using a custom Triton runtime, open the ServingRuntime and show:
   ```yaml
   # no dynamic_batching stanza yet
   ```

3. In the model repository (S3 or the PVC), show the current `config.pbtxt`:
   ```pbtxt
   max_batch_size: 1
   ```

4. From the student Dev Spaces, run a 10-concurrency load:

   ```bash
   python common/client/concurrent_load.py \
     --url $MODEL_ROUTE --model $MODEL_NAME \
     --concurrency 10 --requests 30
   ```

   Record the terrible p95 (often 5–15× single-request latency because every request is serialized).

### Phase 2 — Enable Dynamic Batching Live (The "Aha" Moment)

**Option A — Edit the model config.pbtxt (recommended for teaching)**

- Edit the `config.pbtxt` in the model repository (usually via the S3 bucket or a ConfigMap / PVC editor).
- Change to:
  ```pbtxt
  max_batch_size: 8
  dynamic_batching {
    preferred_batch_size: [ 4, 8 ]
    max_queue_delay_microseconds: 5000
  }
  ```
- Tell KServe / the runtime to reload the model (for Triton explicit mode this is often a management API call or a simple pod restart / re-deploy of the InferenceService).

**Option B — Use two different ServingRuntimes**

Pre-create:
- `triton-batch-1`
- `triton-batch-8` (with the dynamic batching args passed via `--backend-config` or environment)

Switch the InferenceService to the new runtime and redeploy.

5. While the model is redeploying, have students watch the pod events:

   ```bash
   oc get pods -w -n <project>
   ```

6. Once the new pods are `Running` and `Ready`, re-run the exact same load test from the Dev Spaces.

**Watch the numbers:**

- Average latency often *drops* even though more work is happening
- p95 drops dramatically (2–8× improvement is common)
- Effective RPS goes *up*

This is the moment students understand why "bigger batch = better" for throughput (but you must tune queue delay so tail latency doesn't suffer).

### Phase 3 — Response Caching (The "Magic" 10 ms Second Request)

1. Enable the response cache in the same `config.pbtxt`:

   ```pbtxt
   response_cache {
     enable: true
   }
   ```

2. Redeploy / reload.

3. Have a student run the **identical prompt** twice in a row from their terminal:

   ```bash
   python common/client/triton_infer.py --url $MODEL_ROUTE --model $MODEL_NAME \
     --prompt "What is the capital of France?" -v
   ```

4. On the second run, latency should collapse (often < 10–30 ms) because Triton returned the cached response without touching the model at all.

Show the log timestamps — the second request often never even reaches the inference engine.

**Discussion point:** "This is why RAG systems and chatbots feel so fast on the second turn of a conversation — the runtime is doing the heavy lifting for you."

---

## Student Exercise (15 min)

Give the class 10 minutes to experiment:

- Change concurrency from 5 → 20 → 50
- Try the same prompt 5 times in a row (watch cache hit)
- Try 5 different prompts (watch cache miss)
- Record the best p95 they can achieve

Then have 2–3 students report their best numbers and the exact config that produced them.

---

## Lightweight / CPU Path

On CPU-only:

- Use a deliberately tiny model (or even a Python backend that sleeps 200 ms to simulate "thinking")
- The relative improvement from `max_batch_size:1` → `8` is still dramatic (and easier to see because absolute numbers are larger)
- Response cache still gives the "instant second answer" effect

This is actually one of the best modules to run on limited hardware — the teaching signal is very strong.

---

## Artifacts Students Take Away

- The exact `config.pbtxt` snippet that worked
- Their own measured "before" and "after" numbers
- Understanding that **most production gains come from configuration, not bigger GPUs**

**End of the core technical heart of the workshop.** Everything after this builds on this mental model.