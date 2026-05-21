# Module 01 — One-Click Shared Environment (Instructor Guide)

**Duration:** 25–35 minutes  
**Goal:** Get every student into an identical, ready-to-use workspace and make the end-to-end data flow visible before anyone writes code.

---

## Pre-Class Checklist (Instructor)

- [ ] This repo forked or copied to a location students can reach from Dev Spaces
- [ ] At least one model already deployed in OpenShift AI (NIM preferred, Triton lightweight OK)
- [ ] The model has an **external Route** and you have tested a `curl` against it
- [ ] Students have been added to the Data Science Project (or given their own + you share the model)
- [ ] Whiteboard or slide with the data flow diagram (see below)
- [ ] Dev Spaces launch link ready to paste in chat / slide

---

## Step-by-Step Flow

### 1. Welcome & Context (5 min)

> "Today we are not just talking about LLMs. We are going to make every layer observable — from the student's terminal in Dev Spaces, through OpenShift Routes and KServe, down to the actual GPU (or CPU) running Triton or NIM, and back."

### 2. Launch the Dev Space (8 min)

1. Give students the launch URL:
   ```
   https://<devspaces-host>/?url=https://github.com/<your-org>/rhoai-llm-inference-demos
   ```
2. Have them click it while you watch the first few workspaces come up.
3. Walk them through the automatic `postStart` setup (Python venv, `hey`, `k6`, `locust`, clients).
4. Ask everyone to run:
   ```bash
   ./show-status   # or the command shown in the welcome banner
   cd module-01
   ls -la
   ```

**Teaching point:** "This is the power of Dev Spaces + devfile.yaml. One link, reproducible environment, no 'pip install' hell on class day."

### 3. Whiteboard the Data Flow (10 min)

Draw (or show pre-drawn) the following:

```
Student Dev Space (terminal / Python)
        │
        │  curl / Python openai / requests
        ▼
OpenShift Route (https://your-model-route)
        │
        │  (OpenShift load balances across replicas)
        ▼
KServe InferenceService (or ModelMesh)
        │
        ▼
Triton / NIM Pod  (1–N replicas)
        │
        ▼
GPU (or CPU for lightweight path)  ← DCGM metrics
        │
   Cisco Nexus fabric (optional whiteboard layer)
```

Emphasize:
- The **single Route** hides all the complexity
- OpenShift owns L4/L7 balancing
- KServe owns the "always available" contract (even when you delete pods)
- The runtime (Triton/NIM) owns batching, caching, execution
- OpenShift AI dashboard is the control plane students will use all day

### 4. Show the "End State" in the OpenShift AI Dashboard (8 min)

While students are still exploring their workspace:

1. Open the **OpenShift AI dashboard** → **Models** or **Deployments**
2. Show the already-running model (green check, replicas, hardware profile, route URL)
3. Click into the model → **Logs** tab (live)
4. Click **Metrics** if available
5. Briefly open the **OpenShift Console → Observe → Metrics** and show DCGM GPU utilization for the node

**Key phrase:** "By the end of the day you will understand every number on these screens and know exactly which knob to turn when latency or cost is too high."

### 5. Quick Validation from a Student Workspace (5 min)

Pick one student (or do it yourself) and run a single request while everyone watches the model logs update in real time.

```bash
# In Dev Space
export MODEL_ROUTE=https://tiny-llama-rhoai-demos.apps.cluster.example.com
export MODEL_NAME=tiny-llama

python ../common/client/triton_infer.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "Say hello in exactly five words." \
  -v
```

Watch the logs in the RHOAI dashboard light up with `preprocess → inference → postprocess`.

### 6. Wrap & Teaser (2 min)

> "In Module 2 we will do this again, but deliberately, and we will look at every timestamp. Then in Module 3 we will break batching and fix it live."

---

## Lightweight / No-GPU Variant

If you have no GPUs today:

- Use the `triton-cpu-lightweight` ServingRuntime from `common/yamls/offline/`
- Deploy a 20–100 MB ONNX model (or a Python backend that just echoes + sleeps 200 ms)
- The data flow whiteboard and Dev Space experience are identical
- Students still see real logs, real routes, real scaling (just slower inference)

This is actually *better* for the first hour — students focus on the platform, not "waiting for the GPU".

---

## Common Gotchas & Solutions

| Gotcha | Fix |
|--------|-----|
| Dev Space shows "oc not logged in" | Tell students to use the OpenShift Console "Copy login command" and paste it, or rely on the embedded auth that Dev Spaces usually provides |
| Model route returns 403 / auth error | Make sure the InferenceService has `disableAuth: false` or students have the service account token |
| No pods visible in dashboard | Wrong project selected in the top-left project switcher |
| `hey` or `k6` command not found | Run the setup command again or `source ~/.bashrc` |

---

**End of Module 01. Students now have a living, breathing environment and a mental model of the full stack.**