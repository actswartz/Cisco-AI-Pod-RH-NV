# Red Hat OpenShift AI — Scalable LLM Inference Demos

**Lightweight, instructor-led hands-on demos** using:

- **Red Hat OpenShift** — for scheduling, scaling, Routes, resilience, and observability
- **Red Hat OpenShift AI (RHOAI)** — for model serving with KServe / ModelMesh, custom runtimes (Triton), NVIDIA NIM, Hardware Profiles, and the AI dashboard
- **Red Hat OpenShift Dev Spaces** — as the one-click, reproducible student workspace (VS Code in the browser with `oc`, Python, load tools, and all demo scripts pre-cloned)

Each module is designed for a 45–90 minute instructor-led session. Students launch a shared Dev Space from this repo and run commands while the instructor demonstrates console actions, edits runtimes, kills pods, etc.

---

## Workshop Goals

By the end of the day students will be able to:

- Launch a consistent AI developer workspace in Dev Spaces
- Perform inference against models served by OpenShift AI (Triton or NIM)
- Understand and tune batching, caching, and queuing in Triton
- Observe load balancing and horizontal scaling in real time
- Configure GPU-aware Hardware Profiles and scheduling
- Demonstrate fault tolerance and recovery with KServe
- Use OpenShift Observe + Grafana for inference + GPU metrics
- Compare generic Triton vs. NVIDIA NIM performance (when NGC access is available)

---

## How Students Launch the Environment (One-Click)

1. Instructor gives the class the Dev Spaces URL for your cluster (or Developer Sandbox):
   ```
   https://devspaces-<cluster>.apps.<domain>/?url=https://github.com/YOUR-ORG/rhoai-llm-inference-demos
   ```

2. Dev Space starts automatically with:
   - Python 3.11 + virtualenv
   - `oc` CLI (logged in via the embedded OpenShift authentication)
   - `hey`, `k6`, `locust`, `ab` load generators
   - All demo scripts and YAMLs from this repo
   - `curl`, `jq`, `git`, etc.

3. On first start the workspace runs `postStart` commands to install Python packages and tools (cached thereafter).

4. Students immediately see the cloned repo and can `cd module-02 && python client/infer.py ...`

**No local installs. No "works on my machine".** Perfect for classrooms, partner workshops, or Red Hat + Cisco AI Factory sessions.

---

## Instructor Prerequisites (Cluster Side)

Before class the instructor must have:

- OpenShift AI installed with **Single-model serving (KServe)** enabled (recommended) or Multi-model
- At least one GPU node with NVIDIA GPU Operator + DCGM exporter running (for Modules 5–8). CPU-only fallback is possible for Modules 1–4 and 6.
- A **Data Science Project** (e.g., `rhoai-demos`) with a pre-deployed model:
  - Preferred for full experience: NVIDIA NIM deployment (Llama 3.1 8B or Phi-3 via NGC)
  - Lightweight / no-NGC: Custom Triton runtime serving a small model (TinyLlama, Phi-2, or even an ONNX toy model)
- The model's **external Route** exposed and tested
- Student view or edit access to the project (or give them their own projects + instructor shares the model via "Model catalog" or direct InferenceService)
- OpenShift **Observe** dashboards or a Grafana instance showing DCGM + KServe metrics
- (Optional) Cisco Nexus Dashboard / Nexus Insights showing fabric telemetry (whiteboard item)

**Offline / air-gapped / low-GPU alternative** is fully supported — see the "Lightweight Path" section in each module and the dedicated `common/yamls/offline/` examples.

---

## Repository Layout

```
rhoai-llm-inference-demos/
├── README.md
├── devfile.yaml                 # The magic one-click workspace
├── common/
│   ├── client/
│   │   ├── triton_infer.py      # REST v2 client for Triton
│   │   ├── openai_infer.py      # OpenAI-compatible client (NIM / vLLM)
│   │   └── concurrent_load.py   # Simple Python concurrent request loader with timing
│   ├── load/
│   │   ├── locustfile.py
│   │   └── k6-script.js
│   └── yamls/
│       ├── triton-kserve-servingruntime.yaml
│       ├── triton-dynamic-batching.yaml     # variants for Module 3
│       ├── hardware-profile-example.yaml
│       └── offline/                         # CPU-only tiny model examples
├── module-01-one-click-env/
├── module-02-first-inference/
├── module-03-batching-caching/
├── module-04-load-balancing/
├── module-05-gpu-scheduling/
├── module-06-fault-tolerance/
├── module-07-monitoring/
├── module-08-nim-comparison/
└── scripts/                     # helper utilities for instructor
```

Each `module-XX/` folder contains:
- `instructor-guide.md` — exact clicks, YAML edits, whiteboard talking points, timing
- `student-lab.md` — copy-paste commands students run in their Dev Space + what success looks like
- Any module-specific scripts or YAML patches

---

## Module Overview & Timing (Suggested 1-Day Agenda)

| Module | Title | Key Red Hat Tech | Duration | Hands-on Focus |
|--------|-------|------------------|----------|----------------|
| 01 | One-click shared environment | Dev Spaces + pre-deployed model | 30 min | Launch workspace, explore dashboard, whiteboard data flow |
| 02 | First inference from the workspace | Route → KServe → runtime | 45 min | `curl` + Python client, watch logs side-by-side |
| 03 | Batching, caching, queuing | Custom ServingRuntime + Triton config | 60 min | Edit `max_batch_size`, dynamic batching, response cache; compare latency |
| 04 | Load balancing & traffic | Scale replicas, OpenShift Route, metrics | 45 min | `hey -n 1000`, Observe → filter by pod |
| 05 | GPU scheduling & Hardware Profiles | NVIDIA Operator, DCGM, HardwareProfile CR | 45 min | Create profile in UI, deploy with GPU request, `oc describe node` |
| 06 | Fault tolerance & DR | Pod delete, autoscaling, data connection swap | 45 min | Kill pod during load, watch recovery; switch S3 bucket |
| 07 | Monitoring & performance | OpenShift Observe + DCGM + Triton metrics | 45 min | Live Grafana while running load; correlate queue vs latency |
| 08 | Cisco-NVIDIA integration | NIM vs generic Triton | 60 min | Same load script against both; show TensorRT-LLM gains + full topology |

**Total ~6 hours** including breaks. Modules 3, 5, and 8 are the deepest technical demos.

---

## Lightweight / Offline Path (No NGC, Limited GPUs)

Every module has a clearly marked **"Lightweight Alternative"** section:

- Use a **custom Triton CPU runtime** (no GPU required for basic demos)
- Serve a tiny ONNX or PyTorch model (or even a "hello world" Python backend in Triton)
- Or use the built-in **vLLM** or **TGIS** serving runtimes that Red Hat ships (much easier than custom Triton)
- For Module 8 comparison, run two different Triton configurations (one with batching, one without) or Triton vs. a simple Flask mock endpoint

This path is excellent for:
- Partner enablement without enterprise NGC keys
- Laptop / small cluster demos
- Air-gapped government or education environments

The `common/yamls/offline/` folder contains ready-to-apply examples.

---

## Quick Start for Instructors

1. Fork or copy this repo into an org the students can reach.
2. Update `devfile.yaml` if you want a different base image or extra tools.
3. (Strongly recommended) Pre-deploy one model in a shared project and note its Route + auth token.
4. Add the repo URL + any cluster-specific notes to your slide deck.
5. On class day: share the Dev Spaces launch link, have students start their workspaces while you do the Module 1 whiteboard.

---

## Related Red Hat & NVIDIA Resources

- [ai-on-openshift.io — Custom Triton runtime guide](https://ai-on-openshift.io/odh-rhoai/custom-runtime-triton/)
- [Red Hat Developer — How to set up NVIDIA NIM on OpenShift AI (May 2025)](https://developers.redhat.com/articles/2025/05/08/how-set-nvidia-nim-red-hat-openshift-ai)
- [Red Hat OpenShift AI Documentation — Serving models](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/latest/html/serving_models/)
- [NVIDIA GPU Operator on OpenShift](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/openshift.html)
- Red Hat Developer Sandbox (free tier with Dev Spaces + OpenShift AI): https://developers.redhat.com/developer-sandbox

---

## Contributing / Customizing for Your Class

- Add your own model repository under `common/models/` (git LFS or instructions)
- Extend `devfile.yaml` with additional VS Code extensions (e.g., "Continue" for local coding with the served model)
- Create a `solutions/` branch with completed scripts
- For Cisco-specific fabric demos, add a `cisco-nexus/` folder with topology diagrams or API call examples

---

**This workshop turns the abstract "LLM inference pipeline" into a concrete, observable, tunable system running on the exact stack your customers use: OpenShift + OpenShift AI + Dev Spaces.**

Let's build it.