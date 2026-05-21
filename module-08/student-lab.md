# Module 08 — Cisco-NVIDIA Integration with Scalable Inference (Student Lab — Capstone)

**Time:** 50–60 minutes (the final hands-on lab of the day)

---

## Your Capstone Mission

You have spent the day building mental models one layer at a time:

- Launching identical environments (Module 01)
- Making your first real inference calls (Module 02)
- Tuning batching and caching inside Triton (Module 03)
- Scaling replicas and watching load balancing (Module 04)
- Understanding GPU scheduling via Hardware Profiles (Module 05)
- Proving resilience when pods die (Module 06)
- Reading the metrics that explain *why* performance changes (Module 07)

**Today’s lab is the capstone.** You will now run the *exact same load script* against two different production inference deployments, capture hard numbers side-by-side, and then step back to see the complete vertical stack — from the Python code in your browser-based IDE all the way down to the Cisco Nexus fabric under the GPUs.

This is the moment everything clicks.

---

## Prerequisites & Setup

Make sure you are inside your Dev Space and the environment is ready.

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate
```

Your instructor will provide you with **two complete sets of connection information** before you begin. There are two equally valid paths for this lab:

### Path A — Real NVIDIA NIM Comparison (Best Experience)
- **Deployment A:** The generic / custom Triton deployment used throughout Modules 2–7 (`TRITON_ROUTE` + `TRITON_MODEL`)
- **Deployment B:** A production-grade NVIDIA NIM deployment (Llama 3.1 8B, Nemotron, etc.) reached via the OpenAI-compatible `/v1` endpoint (`NIM_ROUTE` + `NIM_MODEL`)

### Path B — Two Differently Tuned Triton Configurations (Always Available)
- **Deployment A (Baseline):** Conservative Triton (small `max_batch_size`, no response cache, default settings)
- **Deployment B (Optimized):** Aggressively tuned Triton (dynamic batching enabled, response cache on, best-practice `config.pbtxt`, or a vLLM/TGIS runtime)

Both paths produce excellent learning outcomes. The performance delta you measure will be dramatic either way.

Set your variables now (example shown for Path B — substitute the exact values your instructor gives you):

```bash
# === PATH B EXAMPLE (Two Triton variants) ===
export BASELINE_ROUTE="https://triton-baseline-<your-route>"
export BASELINE_MODEL="llama-3-8b-instruct"

export OPTIMIZED_ROUTE="https://triton-optimized-<your-route>"
export OPTIMIZED_MODEL="llama-3-8b-instruct"

# === PATH A EXAMPLE (NIM) — uncomment and use instead if provided ===
# export BASELINE_ROUTE="https://triton-generic-..."
# export BASELINE_MODEL="tiny-llama"
# export OPTIMIZED_ROUTE="https://nim-llama-..."
# export OPTIMIZED_MODEL="meta/llama3-1-8b-instruct"
```

Quick sanity check that both endpoints are reachable:

```bash
echo "Testing baseline..."
curl -I "$BASELINE_ROUTE/v2/health/ready" 2>/dev/null || curl -I "$BASELINE_ROUTE/v1/models" 2>/dev/null | head -1

echo "Testing optimized..."
curl -I "$OPTIMIZED_ROUTE/v2/health/ready" 2>/dev/null || curl -I "$OPTIMIZED_ROUTE/v1/models" 2>/dev/null | head -1
```

If either fails, ask your instructor for the corrected values.

---

## Task 1: Single Request Smoke Test on Both Deployments (5 min)

Run one quick inference against each so you have a “feel” for single-user latency before the load test.

**Baseline / Generic (usually Triton v2 path):**

```bash
python common/client/triton_infer.py \
  --url "$BASELINE_ROUTE" \
  --model "$BASELINE_MODEL" \
  --prompt "In one sentence, what is the role of a ServingRuntime in OpenShift AI?" \
  -v
```

**Optimized (may be Triton or OpenAI-compatible):**

If the optimized endpoint is OpenAI-style (NIM, vLLM, TGIS), use:

```bash
python common/client/openai_infer.py \
  --base-url "$OPTIMIZED_ROUTE/v1" \
  --model "$OPTIMIZED_MODEL" \
  --prompt "In one sentence, what is the role of a ServingRuntime in OpenShift AI?"
```

If it is also a raw Triton endpoint, use the `triton_infer.py` command instead.

**Record** the single-request latency you see for each. You will compare this to the p95 numbers under load.

---

## Task 2: Run the Same Load Script Against Both Deployments (20–25 min)

We will use `concurrent_load.py` — the same tool you used in earlier modules. It gives clean, rich tables with average, p50, p95, throughput, and error counts.

Choose a consistent, moderately stressful load. Your instructor will suggest good values for the hardware in the room (typical starting point):

```bash
CONCURRENCY=8
TOTAL_REQUESTS=50
PROMPT="Explain the difference between batching and caching for LLM inference in two clear sentences."
```

### Run Against Baseline (Deployment A)

```bash
python common/client/concurrent_load.py \
  --url "$BASELINE_ROUTE" \
  --model "$BASELINE_MODEL" \
  --prompt "$PROMPT" \
  --concurrency $CONCURRENCY \
  --requests $TOTAL_REQUESTS \
  $( [ "$BASELINE_IS_OPENAI" = "true" ] && echo "--openai" )
```

> **Important:** If the baseline endpoint is OpenAI-compatible, set `BASELINE_IS_OPENAI=true` in your shell before running (or just add `--openai` manually). For classic Triton endpoints, omit the flag.

**Capture everything** — the full table, the wall-clock time, and the effective RPS line. Screenshot or copy into your notes.

While this load is running, watch (or ask the instructor to narrate) the live metrics:
- GPU utilization ramp-up
- Queue depth / batch size distribution (if Triton metrics visible)
- Any memory pressure

### Run Against Optimized (Deployment B)

Now run **the identical command** against the second deployment:

```bash
python common/client/concurrent_load.py \
  --url "$OPTIMIZED_ROUTE" \
  --model "$OPTIMIZED_MODEL" \
  --prompt "$PROMPT" \
  --concurrency $CONCURRENCY \
  --requests $TOTAL_REQUESTS \
  $( [ "$OPTIMIZED_IS_OPENAI" = "true" ] && echo "--openai" )
```

**Capture the second set of numbers with equal care.**

**Pro Tip for stronger data:** Repeat the pair of runs at two different concurrency levels (e.g., 4 and 16) if time permits. The gap often widens at higher load.

---

## Task 3: Complete the Side-by-Side Comparison Table (8–10 min)

Fill in the table below with your actual measured values. This is the artifact you will take away from the capstone.

| Metric                              | Deployment A<br>Baseline / Generic Triton          | Deployment B<br>Optimized (NIM or Tuned Triton)   | Improvement Factor / Delta |
|-------------------------------------|----------------------------------------------------|---------------------------------------------------|----------------------------|
| Concurrency used                    |                                                    |                                                   | —                          |
| Total requests attempted            |                                                    |                                                   | —                          |
| Successful (200) responses          |                                                    |                                                   | —                          |
| Effective throughput (RPS)          |                                                    |                                                   |                            |
| Average latency (ms)                |                                                    |                                                   |                            |
| p50 latency (ms)                    |                                                    |                                                   |                            |
| p95 latency (ms)                    |                                                    |                                                   |                            |
| p99 / max latency (ms)              |                                                    |                                                   |                            |
| Wall-clock time for the run (s)     |                                                    |                                                   |                            |
| GPU memory footprint (dashboard)    |                                                    |                                                   |                            |
| Peak / sustained GPU util %         |                                                    |                                                   |                            |
| Cache hit rate (if visible)         |                                                    |                                                   |                            |
| Qualitative observations            |                                                    |                                                   |                            |

**Answer these analysis questions using your data:**

1. By what factor did throughput improve on the optimized path?
2. How much did the p95 (the latency experienced by the slowest 5% of users) drop? This is usually the most business-relevant number.
3. Did the optimized deployment achieve its gains while using *less* or *more* GPU memory?
4. Were the gains larger at higher concurrency? Why do you think that is?

---

## Task 4: Explore the Full Topology in the OpenShift AI Dashboard (8–10 min)

This is the “zoom out” moment. Open the **Red Hat OpenShift AI dashboard** and navigate to the Data Science Project that contains today’s models.

With your instructor, deliberately walk through **every visible layer** of the stack:

- **Your own Dev Space** — the running `devworkspace` that has been your home all day. Notice it is just another pod with a route, persistent volume, and injected environment.
- **The two model deployments** you just benchmarked — look at their InferenceService objects, replica counts, and pod status.
- **ServingRuntimes** — the custom Triton one vs. the NIM or built-in vLLM/TGIS runtime. See how the dashboard lets you choose the engine at deployment time.
- **Hardware Profiles** — the UI abstraction that turned into `nvidia.com/gpu` requests on the actual pods (Module 05).
- **Pod placement** — which nodes the inference pods landed on and why.
- **Routes & networking** — the single external HTTPS endpoint that hides all the complexity behind it.
- **Live metrics tabs** — DCGM GPU telemetry + runtime-specific counters (queue time, batch sizes, cache efficiency). Watch how the graphs you studied in Module 07 directly explain the numbers in your table.
- **Project-level view** — everything an enterprise MLOps team sees in one place.

**Instructor highlight (whiteboard or screen share):**  
“From the Python `concurrent_load.py` you just ran inside a browser-based VS Code session, through the OpenShift Route, KServe, the chosen runtime (Triton or NIM), the GPU Operator, the DCGM exporter, the node scheduler, and finally the high-speed Cisco Nexus fabric connecting the GPUs — this is the complete vertical that Red Hat, NVIDIA, and Cisco sell together as a turnkey private AI factory.”

Take one last good look. You now have the full picture.

---

## Task 5: The Strong Capstone Reflection (10–12 min)

This section is deliberately substantial because it is the last exercise of the day.

In your notes (or a shared document), write thoughtful answers to the prompts below. Be specific — reference the actual numbers you just measured and the objects you just saw in the dashboard.

### Reflection Prompts

**1. End-to-End Request Path**  
Trace one prompt from the moment `concurrent_load.py` creates the HTTP request inside your Dev Space until the tokens come back. Name at least **seven** distinct technologies, Kubernetes resources, or hardware components the request touches. (Example start: “Python requests → OpenShift Route → … → Cisco silicon”)

**2. Configuration vs. Raw Hardware**  
In many runs the largest gains came from enabling dynamic batching + response cache or switching to an optimized engine rather than simply giving the model a bigger GPU. What does this teach you about where production performance engineering time should actually be spent?

**3. The Value of the Platform**  
Imagine you had to reproduce today’s entire exercise (Dev Spaces + two different inference engines + GPU scheduling + live metrics + fault tolerance) using only raw Kubernetes, manual Dockerfiles, and a plain VM cluster. Which three things would have been dramatically harder or impossible without Red Hat OpenShift AI?

**4. The Invisible Fabric**  
The Cisco Nexus layer was mentioned repeatedly even though you never configured a switch. In a real deployment with 8, 32, or 128 GPUs across multiple nodes, what specific failure mode or performance cliff would appear if the interconnect was ordinary datacenter Ethernet instead of a properly engineered lossless, high-radix AI fabric?

**5. Personal “Aha” Moment**  
What single moment or number from today’s workshop changed the way you think about LLM inference systems? Why will that insight matter in your future work?

### Your “I Now Understand the Entire Stack” Paragraph

Write one concise, personal paragraph (3–6 sentences) that you can keep, share with your team, or even post. Use this template as a starting point and make it your own:

> “In the capstone lab I ran identical concurrent load (`concurrency=$CONCURRENCY`, $TOTAL_REQUESTS requests) against a baseline Triton deployment and an optimized [NIM / tuned Triton] deployment. The optimized path delivered roughly ___× higher throughput and reduced p95 latency from ___ ms to ___ ms while often using less GPU memory. I watched the exact same client code travel through my Dev Space, an OpenShift Route, KServe, a chosen ServingRuntime, Hardware Profiles, the NVIDIA GPU Operator + DCGM, and ultimately the high-speed fabric underneath. I now have a complete, practical mental model of the full Red Hat + NVIDIA + Cisco inference stack — from a Python prompt in a browser IDE to photons moving across a Nexus switch — and I understand exactly where the biggest performance levers live.”

---

## Lab Deliverables Checklist

- [ ] Both endpoints smoke-tested with single requests
- [ ] Two complete `concurrent_load.py` runs captured (same parameters)
- [ ] Filled side-by-side comparison table with real measured data
- [ ] GPU / metrics observations noted during the loads
- [ ] Full topology walk-through completed in the OpenShift AI dashboard
- [ ] Written answers to the five reflection prompts
- [ ] Personal “I now understand the entire stack” paragraph

---

## What You Should Now Understand — The Capstone Synthesis

You can now confidently say:

- How to perform a fair, apples-to-apples benchmark between two inference stacks using the same load generator and prompts
- Why optimized runtimes (dynamic batching, response caching, TensorRT-LLM kernels in NIM, etc.) routinely deliver 2–4× gains that no amount of extra GPU silicon can match by itself
- The precise mapping from every UI element in the OpenShift AI dashboard to the underlying Kubernetes and hardware objects
- The complete vertical integration: **Developer workspace (Dev Spaces) → Platform orchestration (OpenShift + KServe) → Inference runtime (Triton or NIM) → Accelerator scheduling (GPU Operator + Hardware Profiles) → Observability (DCGM + runtime metrics) → High-speed networking fabric (Cisco Nexus)**
- That this exact architecture — reproducible, observable, tunable, and resilient — is what real enterprises are putting into production today for private AI factories

---

**Congratulations. You have completed the full workshop.**

You arrived this morning not knowing how to launch a consistent AI environment. You are leaving with the ability to:

- Launch identical workspaces for any team
- Deploy and tune real LLM inference servers
- Measure and explain performance differences with data
- See and articulate the entire Red Hat + NVIDIA + Cisco stack

The numbers in your comparison table and the paragraph you just wrote are powerful evidence of that journey.

**This is the stack being sold and deployed for enterprise private AI right now.**

Keep your notes, your table, and your reflection. They will serve you well in future conversations, architecture reviews, and proof-of-concept work.

---

**End of Module 08 — Capstone Complete**

**End of Workshop**

(Leave your Dev Space running for any final instructor-led discussion, group share-out, or wrap-up Q&A.)

Thank you for spending the day with us. You now understand the entire stack.
