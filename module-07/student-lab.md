# Module 07 — Monitoring and Performance Metrics (Student Lab)

**Time:** 35–45 minutes of active observation and load generation

---

## Your Mission

Turn the dashboards from pretty pictures into **actionable diagnostic tools**.

You will:

- Open the real OpenShift Observe + DCGM + Triton/NIM metrics surfaces
- Run carefully controlled load from your Dev Space
- Deliberately create (and then clear) a request queue backlog
- Watch in real time how **queue depth drives latency**, how GPU utilization can be misleading, and what the important panels really mean

By the end of this module you will be able to look at a production inference deployment and immediately know whether the bottleneck is the GPU, the batcher, the queue, or the client.

---

## Setup (Do This First — 3 minutes)

In your Dev Space terminal:

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate

export MODEL_ROUTE="https://<instructor-gives-you-this>"
export MODEL_NAME="<instructor-gives-you-this>"

echo "Route: $MODEL_ROUTE"
echo "Model: $MODEL_NAME"
```

Quick connectivity check:

```bash
curl -I "$MODEL_ROUTE/v2/health/ready" 2>/dev/null || curl -I "$MODEL_ROUTE/v1/models" 2>/dev/null || echo "Trying basic reachability..."
curl -s "$MODEL_ROUTE/v2/health/ready" | head -c 200 || true
```

---

## Step 1: Open All the Live Dashboards (Keep These Open the Whole Module)

You will be switching between your terminal (generating load) and the browser (watching graphs). Arrange your windows so you can see both.

### 1. OpenShift Console — Observe

1. Log into the OpenShift web console for the same cluster.
2. Go to **Observe → Dashboards**.
3. Look for (and pin or favorite) these dashboards:
   - **NVIDIA DCGM** (or "GPU", "DCGM Exporter", "NVIDIA GPU Metrics")
   - Any **Inference**, **Triton**, **KServe**, **Model Serving**, or custom workshop dashboard your instructor prepared

### 2. RHOAI / OpenShift AI Dashboard

1. Navigate to your Data Science Project.
2. Find your deployed model (InferenceService).
3. Open its detail view and look for a **Metrics** tab (NIM deployments often have rich panels here).

### 3. (Optional but powerful) Raw Metrics Explorer

Observe → **Metrics** (the Prometheus query browser). You can paste queries here later if a panel is missing.

**Pro tip:** Keep the DCGM dashboard in one browser tab and the model-specific or Triton metrics in another. Use the time-range selector (last 5m or last 15m) so you see the live action.

---

## Step 2: Establish a Quiet Baseline (Light Load)

We need to know what "normal" looks like before we break it.

Run a very gentle load (1–2 concurrent users):

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --concurrency 2 \
  --requests 20 \
  --prompt "Hello, this is a short test prompt."
```

**While this light load is running, look at the dashboard and record the steady-state values:**

- **DCGM / GPU panels**
  - Average GPU Utilization (%): ________
  - GPU Memory Used (MiB or %): ________
  - Power draw (W): ________
  - Temperature (°C): ________

- **Inference / Triton / Model panels**
  - Queue wait time or `nv_inference_queue_duration_us` (average or p95): ________
  - Compute / inference duration (average): ________
  - Request rate (RPS or requests per minute): ________
  - Any visible batch size distribution: ________
  - Cache hit rate (if the panel exists): ________

- **From the client output**
  - Average latency (ms): ________
  - p95 latency (ms): ________

Take a screenshot or copy the numbers into a scratch file. This is your **baseline**.

---

## Step 3: The Queue-Depth vs Latency Correlation Experiment (The Heart of the Module)

This is the exercise that makes everything click.

### Phase A — Moderate Sustained Load

Start a noticeably heavier load. Use one of these (pick what your instructor recommends):

**Option 1 — Python concurrent (precise control)**
```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --concurrency 12 \
  --requests 80 \
  --prompt "Explain the architecture of OpenShift in two paragraphs."
```

**Option 2 — hey (simple burst)**
```bash
hey -n 100 -c 15 \
  -m POST \
  -T "application/json" \
  -d '{"inputs":[{"name":"text_input","shape":[1],"datatype":"BYTES","data":["Explain containers in detail."]}]}' \
  "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer"
```

**Option 3 — k6 (nice ramp)**
```bash
k6 run -e MODEL_ROUTE="$MODEL_ROUTE" -e MODEL_NAME="$MODEL_NAME" common/load/k6-script.js
```

**While the load is running, stare at the live graphs and answer these questions out loud or in your notes:**

1. When the request rate increases, which line moves **first** — queue wait time or GPU utilization?
2. Does GPU utilization go **up** or surprisingly **down** as the queue builds? Why?
3. How many seconds after the queue depth spikes does the client-reported latency (or TTFT) start climbing?
4. Look at the batch-size panel (if present). Are requests being combined into larger batches, or are they mostly size 1?

Record the peak numbers you see during this phase.

### Phase B — Deliberately Create a Backlog (Long Prompts + High Concurrency)

Now we force the queue to grow on purpose. Longer prompts = more GPU time per request = easier to build a queue.

```bash
export LONG_PROMPT="Write a detailed 250-word technical explanation of how Kubernetes pod scheduling works, including the role of the scheduler, taints, tolerations, and node affinity."

python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --concurrency 20 \
  --requests 60 \
  --prompt "$LONG_PROMPT"
```

(If your client is NIM/OpenAI path, add `--openai` to the command above.)

**While this aggressive load runs, watch and record:**

- Highest queue wait time / depth you observe: ________
- Highest client p95 latency: ________
- GPU utilization at the moment latency is worst: ________
- Any "pending requests" or "queue depth" counter: ________

**Key observation to discuss with your neighbor:**
> "The GPU looks only 40% busy, yet users are waiting 8 seconds. The work is stuck in the queue, not on the silicon."

### Phase C — Release the Pressure and Watch Recovery

Kill or reduce the load (Ctrl-C the current command, or run a very light one again):

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --concurrency 3 \
  --requests 15 \
  --prompt "Short recovery test."
```

**While the system drains the queue, watch the dashboards:**

- Does the queue depth drop **before** or **after** latency improves?
- Does GPU utilization often **spike** briefly as the backlog finally reaches the GPU?
- How long does it take for all the curves to return to the baseline you recorded in Step 2?

This "queue first, latency second, GPU catch-up last" pattern is one of the most important mental models in production LLM serving.

---

## Step 4: Read the Other Critical Panels

While you still have load running (or re-run a moderate test), explore these additional signals.

### If You Are Using NVIDIA NIM (OpenAI-compatible endpoint)

Look for these panels or run queries in the Metrics explorer:

- **Time to First Token (TTFT)** — the time until the first streaming token appears
- **Time Per Output Token (TPOT)** — generation speed after the first token
- Request queue length or "num_requests_waiting"
- Prompt token count vs. generation token count histograms

Run a streaming test while watching:

```bash
python common/client/openai_infer.py \
  --base-url "$MODEL_ROUTE/v1" \
  --model "$MODEL_NAME" \
  --prompt "Tell me a short story about Red Hat." \
  --stream
```

**While streaming requests are in flight, record:**
- TTFT values you see in the dashboard
- How TPOT changes as you increase concurrency

### Cache Hit Rate (If Response Cache Was Enabled in Module 03)

Run the **exact same prompt** many times in quick succession:

```bash
for i in {1..8}; do
  python common/client/triton_infer.py \
    --url "$MODEL_ROUTE" \
    --model "$MODEL_NAME" \
    --prompt "What is the capital of France?"
done
```

**While doing this, watch the cache hit rate panel.** It should jump toward 100% on repeats. Note how end-to-end latency collapses on cache hits even when the GPU is busy with other work.

### Batch Size Distribution

If the dashboard shows a histogram or average batch size:

- Run low concurrency (mostly batch size 1)
- Run high concurrency with dynamic batching enabled (you should see larger batches)

Larger batches = better GPU efficiency, but only if you also keep queue delay tuned.

---

## Step 5: Quick Experiments with Different Load Tools (10 min free play)

Try at least two of these and compare what the dashboards reveal:

1. **Locust interactive load** (great for live knob turning)
   ```bash
   locust -f common/load/locustfile.py --host="$MODEL_ROUTE" -u 15 -r 3 --run-time 90s
   ```
   Then open the Locust web UI (ask your instructor for the exposed route to port 8089) and dynamically change the number of users while watching the graphs.

2. **k6 with custom stages** — edit the stages in `common/load/k6-script.js` temporarily for a 10s ramp to 30 users, or just run the default.

3. **Simple `ab` or repeated `hey`** for very short sharp spikes.

After each run, answer:
- Which tool gave you the clearest "I can see the queue forming" signal on the dashboard?

---

## Your Data Collection Notes (Fill These In)

**Baseline (concurrency 2)**
- GPU Util: ____%   Queue wait: ____ ms   Client p95: ____ ms

**Moderate load (concurrency 10–15)**
- Peak GPU Util: ____%   Peak queue: ____ ms   Peak client p95: ____ ms   Time lag between queue spike and latency spike: ____ s

**High-backlog run (long prompts, high conc)**
- Worst queue depth seen: ________
- Worst client latency: ________
- GPU util during worst latency: ________
- Recovery time after load dropped: ________ s

**Cache experiment (if applicable)**
- First-request latency: ________ ms
- Cache-hit latency (repeat prompt): ________ ms
- Cache hit rate observed: ________ %

**NIM-specific (if applicable)**
- Typical TTFT under light load: ________ ms
- Typical TTFT under heavy load: ________ ms
- TPOT change with concurrency: ________________

---

## What Success Looks Like

- You can name the **four or five most important panels** on the DCGM + inference dashboard without looking.
- You can predict, from watching the queue metric alone, when client latency is about to get bad.
- You understand why "the GPU is only at 60%" is **not** always good news.
- You know exactly which knob (replicas, batch config, cache, Hardware Profile, prompt length, client concurrency) you would turn first when you see each anti-pattern on the dashboard.

---

## Lightweight / CPU-Only Path Notes

If you are running the offline Triton CPU example:
- DCGM panels will be empty or zero (no GPU).
- The **queue wait vs. compute duration** correlation is still extremely clear and often easier to see because absolute latencies are higher.
- Use the same load commands — the teaching signal for queuing theory remains excellent.

---

## What You Should Now Understand

- Real production debugging of LLM inference is done almost entirely by reading the relationship between **queue metrics**, **GPU metrics**, and **client-visible latency**.
- Adding more GPUs only helps after you have ruled out queuing and batching problems.
- The dashboards are not just for after-the-fact analysis — they are live control instrumentation you use while tuning.

**You are now equipped to walk up to any OpenShift AI inference deployment and diagnose performance issues like a pro.**

**Ready for Module 08 — Cisco-NVIDIA Integration and NIM vs Triton Comparison.** Keep your terminal and the dashboards handy.
