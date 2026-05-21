# Module 01 — One-Click Shared Environment (Student Lab)

**Estimated Time:** 30–40 minutes (including instructor discussion and whiteboard)  
**Difficulty:** Beginner – no prior OpenShift AI experience required  
**Goal:** Launch a perfectly reproducible developer workspace and gain a clear mental model of the complete inference request path before writing any production code.

---

## Lab Objectives

By the end of this lab you will be able to:

- Launch an identical, pre-configured Red Hat OpenShift Dev Spaces workspace from a single link with zero local software installation.
- Verify that all required tools (`oc`, `hey`, `k6`, Python clients, `rich`, etc.) are present and functional.
- Navigate the Red Hat OpenShift AI dashboard to locate a deployed model, inspect its status, replicas, hardware profile, and external Route.
- Execute a first validation inference request from your Dev Space terminal against the shared model using both raw `curl` and the reusable Python client.
- Draw or describe the end-to-end data flow: Dev Space → OpenShift Route → KServe InferenceService → Triton/NIM runtime → GPU (or CPU) → response.
- Record the exact model Route, name, and your observed baseline latency numbers for use in every subsequent module.
- Identify where the “knobs” (ServingRuntime configuration, Hardware Profiles, replica count, observability) live that we will tune throughout the day.

---

## Prerequisites & Environment Setup

You need **nothing installed on your laptop**. Everything runs inside a browser-based VS Code environment powered by Red Hat OpenShift Dev Spaces.

**What you must have from your instructor:**
- The single Dev Spaces launch link (example):  
  `https://devspaces-<cluster>.apps.<cluster-domain>/?url=https://github.com/<your-org>/rhoai-llm-inference-demos`
- The name of the Data Science Project containing the model (commonly `rhoai-demos`).
- The model Route URL and model name (you will copy these during the dashboard tour).
- Optional: OpenShift Console login command (if embedded authentication is not sufficient).

> **Instructor Note:** The workspace is defined by `devfile.yaml` at the root of this repository. The `postStart` event automatically creates a Python virtual environment, installs `requests`, `openai`, `rich`, `locust`, plus the `hey` and `k6` load generators. This is why every student has an identical environment on class day.

---

## Step 1: Launch Your Personal Dev Space

1. Click (or paste) the launch link provided by your instructor.
2. Authenticate with your OpenShift credentials when prompted (the workspace uses your identity for `oc` commands).
3. Wait for the workspace to initialize.  
   - First launch: 2–4 minutes while packages and tools are installed.  
   - Subsequent launches: usually under 60 seconds (cached layers).
4. When the VS Code interface appears, you should see the repository checked out at:

   ```bash
   /projects/rhoai-llm-inference-demos
   ```

**Verify the clone immediately:**

```bash
cd /projects/rhoai-llm-inference-demos
pwd
ls -1
```

**Expected result:** You see folders `common/`, `module-01/`, `module-02/`, `README.md`, `devfile.yaml`, etc.

---

## Step 2: Activate the Workshop Environment & Verify Tools

Open a terminal inside the Dev Space:

- **Menu:** Terminal → New Terminal, or press `` Ctrl+` `` (backtick).

Run the following commands exactly (copy-paste friendly):

```bash
# Activate the persistent Python virtual environment created by the devfile
source /home/user/.venv/bin/activate

# Quick status check (recommended after every reconnect)
echo "Python: $(python --version)"
echo "Working directory: $(pwd)"
which oc
which hey
which k6
which ab 2>/dev/null || echo "ab (Apache Bench) not found – optional"
```

Install/verify Python packages are usable:

```bash
python -c "
import requests
import openai
from rich.console import Console
print('✅ All core Python packages imported successfully')
console = Console()
console.print('[bold green]Rich console ready for pretty output[/bold green]')
"
```

**Expected result:** Clean output showing Python 3.11+, `oc`, `hey`, `k6`, and successful imports. No errors.

If any tool is missing (rare), run the setup command manually:

```bash
# Re-execute the exact setup defined in devfile.yaml
cd /projects/rhoai-llm-inference-demos
# The postStart already ran; you can also source ~/.bashrc again
source ~/.bashrc
```

---

## Step 3: Explore the Repository Structure

Get familiar with what you will use all day:

```bash
cd /projects/rhoai-llm-inference-demos

# High-level layout
ls -1

# The three client scripts you will run dozens of times
ls -l common/client/

# Load generation tools (introduced later)
ls common/load/

# Example ServingRuntimes and Hardware Profiles
ls -R common/yamls/
```

**Inspect the clients you will use:**

```bash
# See the help for the primary Triton v2 client
python common/client/triton_infer.py --help

# See the OpenAI-compatible client (used for NIM, vLLM, TGIS)
python common/client/openai_infer.py --help

# Concurrent load generator for before/after experiments
python common/client/concurrent_load.py --help
```

**Observe / Note this:**  
All three clients are written with the `rich` library for beautiful terminal output. They support both Triton’s native `/v2/models/.../infer` REST protocol and the OpenAI `/v1/chat/completions` path. This means the **same infrastructure** (Route, KServe, scaling, GPU scheduling) works for any runtime.

Read the short QUICKSTART and the top of README for philosophy:

```bash
head -50 README.md
cat QUICKSTART.md | head -30
```

---

## Step 4: Whiteboard the End-to-End Data Flow (Instructor-Led + Individual Exercise)

Your instructor will draw (or project) the following architecture. While they speak, **copy the diagram into your notes or a scratch file** and label each arrow with the technology responsible.

```
Your Dev Space Terminal (Python / curl / hey / k6)
          │
          │  HTTPS request (JSON payload or OpenAI format)
          ▼
OpenShift Route (L4/L7 load balancer, TLS termination, single public URL)
          │
          │  Routes traffic across available pods
          ▼
KServe InferenceService (or ModelMesh)
          │   (declarative, auto-scales, owns the "always-ready" contract)
          ▼
Triton Inference Server or NVIDIA NIM Pod(s)   ← 1..N replicas
          │
          │  Preprocess → Inference (model forward pass) → Postprocess
          ▼
GPU (NVIDIA A10/A100/H100 via GPU Operator) or CPU (lightweight path)
          │
          │  DCGM exporter → Prometheus → OpenShift Observe / Grafana
          ▼
(Optional) Cisco Nexus fabric telemetry (for advanced sessions)
```

**Discussion questions (answer in your notes):**
- Why does a single Route hide all the replicas from the caller?
- Which layer owns batching and response caching? (Answer: the runtime – Triton or NIM)
- Which layer provides fault tolerance when you delete a pod? (Answer: KServe + OpenShift)
- Where will you look to see GPU utilization live? (Answer: OpenShift Observe → DCGM metrics)

---

## Step 5: Tour the Red Hat OpenShift AI Dashboard (Self-Guided + Instructor Demo)

While the instructor demonstrates on the big screen, **follow along in your own browser tab** (you were granted project access).

1. Open the **Red Hat OpenShift AI dashboard** (usually `https://rhods-dashboard-<cluster>....` or linked from the OpenShift Console “Applications” menu).
2. In the top-left project switcher, select the Data Science Project your instructor named (e.g., `rhoai-demos`).
3. Navigate to **Models** (or **Deployments** / **Model Serving** depending on RHOAI version).
4. Locate the pre-deployed model (green checkmark, “Ready” status).
5. **Record the following immediately** (you will need these values for the rest of the day):

   | Item                  | Value / How to Capture                                      | Notes |
   |-----------------------|-------------------------------------------------------------|-------|
   | Model display name    | Click the row or name                                       | e.g. `tiny-llama`, `meta-llama3-1-8b-instruct` |
   | Exact Model Name (for clients) | Usually the same or shown under “Inference endpoint” | This is `$MODEL_NAME` |
   | External Route / Inference URL | Look for the “Route” link or “Copy inference endpoint” button | Starts with `https://...apps.<cluster>...` – this is `$MODEL_ROUTE` |
   | Replicas              | Note current count and the Hardware Profile column          | e.g. 1/2 or 2/2 |
   | Hardware Profile      | Name shown (e.g. `nvidia-a10`, `gpu-large`, or `cpu-light`) | Critical for Module 05 |
   | ServingRuntime        | Which runtime is selected (Custom Triton, NVIDIA NIM, etc.) | We will edit this in Module 03 |

6. Click into the model row → **Logs** tab. Leave this tab open.
7. (If visible) Click **Metrics** or the “View in Observe” link.
8. Open a second browser tab to the **OpenShift Console → Observe → Metrics**.
9. Search for `DCGM` or `gpu` and pin a graph for the node running your model (instructor will point out the correct query).

> **Observe:** The model is already healthy and serving traffic. In later modules you will change replica counts, edit batching YAML, delete pods, and watch everything recover automatically.

**If you are on the Lightweight / CPU-only path:**  
Your instructor deployed the `triton-cpu-lightweight` ServingRuntime from `common/yamls/offline/`. The dashboard experience is identical; only the inference speed and GPU metrics will differ.

---

## Step 6: Capture Environment Variables & Perform Your First Validation Inference

In your Dev Space terminal, export the two critical variables (instructor will paste the exact values into chat or you copy from the dashboard):

```bash
export MODEL_ROUTE="https://<paste-the-route-here>"
export MODEL_NAME="<paste-the-exact-model-name-here>"

echo "Route : $MODEL_ROUTE"
echo "Model : $MODEL_NAME"
```

### 6.1 Health Check (always do this first)

```bash
# Triton v2 style health endpoint
curl -I "$MODEL_ROUTE/v2/health/ready" || true

# OpenAI-compatible style (NIM / vLLM)
curl -I "$MODEL_ROUTE/v1/models" || true
```

**Expected result:** HTTP/2 200 or a JSON model list. Any 4xx/5xx means the route or auth is not ready – tell your instructor.

### 6.2 Raw curl Request (see the wire format)

```bash
curl -s -X POST "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "text_input",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["Explain what Red Hat OpenShift AI is in one friendly sentence."]
    }]
  }' | jq .
```

Watch the **Logs** tab in the RHOAI dashboard while the request runs. You should see lines mentioning `preprocess`, `inference`, and `postprocess`.

### 6.3 Use the Production-Ready Python Client (the one you will use all day)

```bash
python common/client/triton_infer.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "List three benefits of running LLM inference on Red Hat OpenShift." \
  --verbose \
  --times 3
```

**Observe / Note this:**  
- The first request is often slower (cold tokenizer / model load).
- Subsequent requests are faster.
- The client prints a clean latency summary and the model’s actual text response.
- The rich JSON output in the terminal matches what you see in the pod logs.

### 6.4 (If your model is NIM or vLLM) Try the OpenAI Path

```bash
python common/client/openai_infer.py \
  --base-url "$MODEL_ROUTE/v1" \
  --model "$MODEL_NAME" \
  --prompt "Why is a single Route valuable for LLM serving?" \
  --stream \
  --times 2
```

Notice how streaming feels different (time-to-first-token) even though the underlying platform is the same.

---

## Step 7: Record Your Personal Baseline (Critical for Later Modules)

Run a tiny concurrent load so you have “before” numbers:

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Hi" \
  --concurrency 3 \
  --requests 12
```

**What to Capture / Write Down** (create a note or table in your scratch file):

| Metric                    | Your Observed Value | Source Command                  | Why It Matters Later                  |
|---------------------------|---------------------|---------------------------------|---------------------------------------|
| MODEL_ROUTE               | https://...         | Dashboard or echo               | Every single command needs this       |
| MODEL_NAME                | tiny-llama          | Dashboard                       | Must match the runtime exactly        |
| First curl latency        | ___ ms              | Manual timing or client         | Baseline before any tuning            |
| triton_infer.py avg (3x)  | ___ ms              | `--times 3` output              | Compare after enabling dynamic batching |
| concurrent_load p95       | ___ ms              | concurrent_load.py output       | Target for Module 03 & 04 experiments |
| Current replica count     | 1 or 2              | RHOAI dashboard                 | We will scale this live in Module 04  |
| Hardware Profile name     | nvidia-...          | Dashboard column                | Key for Module 05 GPU scheduling      |

Keep this table handy for the entire workshop. We will repeatedly beat these numbers.

---

## Reflection & Key Takeaways

Answer these in your notes (2–3 minutes):

1. In **one sentence**, describe the complete path a prompt takes from the moment you press Enter in your Dev Space until the model’s answer appears.
2. What single feature of Dev Spaces + `devfile.yaml` eliminates the classic “but it works on my machine” problem on workshop day?
3. Name two concrete “knobs” we can turn later today that are **not** in your Python client code.
4. Why does Red Hat emphasize the **Route + KServe** layer for production LLM serving instead of exposing pod IPs directly?

Share one answer with the person next to you or in chat when the instructor asks.

---

## Troubleshooting Common Issues

| Problem                              | Likely Cause & Fix |
|--------------------------------------|--------------------|
| Dev Space build stays at “Starting” for >5 min | Browser tab throttled or cluster under load. Refresh the workspace page or ask instructor to check pod status. |
| `oc whoami` says “not logged in” or “unauthorized” | Use the OpenShift Console “Copy login command” button and paste it, or rely on the embedded Dev Spaces authentication. |
| `curl` against the Route returns 403 / 401 | The InferenceService may require a token. Ask instructor for the service account token or `oc whoami -t`. Many classroom models run with `disableAuth: true` or a public route. |
| `python ... triton_infer.py` fails with connection error | Wrong `$MODEL_ROUTE` (missing https:// or trailing slash). Re-export the exact value from the dashboard. |
| Model logs tab is empty or “No pods” | Wrong project selected in the dashboard switcher. Confirm you are in the same project as the model. |
| `hey` or `k6` command not found | Run `source /home/user/.venv/bin/activate && source ~/.bashrc` again. The postStart is idempotent. |
| No DCGM / GPU graphs in Observe | Cluster may be using the CPU-only lightweight path today. GPU metrics appear in Modules 05–08 when hardware is present. |
| ImportError for `rich` or `openai` | The venv was not activated. Always start with `source /home/user/.venv/bin/activate`. |

Still stuck? Raise your hand — the instructor has seen every one of these before.

---

## Checkpoint / Success Criteria

You have successfully completed Module 01 when **all** of the following are true:

- [ ] Your Dev Space is running, the venv is activated, and `python --version`, `oc`, `hey`, and `k6` all report successfully.
- [ ] You can run `python common/client/triton_infer.py --help` without errors.
- [ ] You have exported `MODEL_ROUTE` and `MODEL_NAME` and a health-check `curl -I` returns 200.
- [ ] You executed at least one successful inference request (curl or Python client) and saw the response text plus a latency number.
- [ ] You can point to the model in the OpenShift AI dashboard, name its current replica count and Hardware Profile, and have the Route URL copied.
- [ ] You have a personal “baseline” table with at least the Route, model name, and one latency number written down.
- [ ] You can describe (or have sketched) the five-layer request path from Dev Space to GPU.

**If every box is checked — congratulations!** You now have a living, breathing, identical environment that every other student and the instructor share. This is the foundation for the rest of the day.

---

**Ready for Module 02 — First Real Inference (deep pipeline observation, side-by-side logs, and baseline capture).**

Keep this terminal and these two environment variables exported. We will use them immediately.

> **Remember the philosophy:** One link → identical workspace → observable stack → tunable production inference on Red Hat OpenShift AI.

---

*End of Module 01 Student Lab*  
*Red Hat OpenShift AI – Scalable LLM Inference Demos Workshop*
