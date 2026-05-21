# Module 05 — GPU Scheduling and Hardware Profiles (Student Lab)

**Time:** 40–50 minutes (instructor-led demonstration with extensive hands-on inspection from your Dev Space)

---

## Your Mission

Trace the complete chain that turns a friendly UI selection into real GPU hardware being used by your inference workload:

**Hardware Profile (UI) → pod spec with `nvidia.com/gpu` requests/limits + nodeSelector + tolerations → Kubernetes scheduler placement on a GPU node → NVIDIA DCGM metrics appear for that pod**

You will run every inspection command yourself. Even if you do not have cluster-admin rights, you can observe nodes, pods, and the effects of the profile. Your instructor will perform the privileged dashboard actions (creating the profile and deploying the model with it) while you watch the results appear in real time.

---

## Setup (Run This First)

Open a terminal in your Dev Space and prepare your environment:

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate

# Confirm you are authenticated to the cluster
oc whoami
oc cluster-info | head -3

# Note the project/namespace where models are deployed (ask instructor if unsure)
oc project
```

Export the usual variables from previous modules (instructor will remind you of the exact values):

```bash
export MODEL_ROUTE="https://<instructor-gives-you-this>"
export MODEL_NAME="<instructor-gives-you-this>"
export PROJECT="<instructor-gives-you-this>"   # e.g. rhoai-demos

echo "Project: $PROJECT"
echo "Model:   $MODEL_NAME"
```

---

## Task 1 — Explore the NVIDIA GPU Operator and DCGM (5–7 min)

The GPU Operator installs and manages everything needed for NVIDIA GPUs on OpenShift, including the DCGM exporter that produces the utilization, memory, temperature, and power metrics you will see later.

Run these commands to discover the components:

```bash
# See all GPU Operator workloads
oc get pods -n nvidia-gpu-operator

# Specifically locate the DCGM exporter (DaemonSet — one pod per GPU node)
oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter

# Get the exact DCGM pod name for later reference
DCGM_POD=$(oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "no-dcgm-pod-found")
echo "DCGM exporter pod: $DCGM_POD"
```

**What success looks like:** You see at least one `nvidia-dcgm-exporter-...` pod in `Running` state. This pod is what feeds the beautiful GPU graphs in the Observe dashboards.

---

## Task 2 — Inspect GPU Nodes and Capacity (8–10 min)

This is the "supply" side that the scheduler will match against.

```bash
# List every node that reports a GPU
oc get nodes -l nvidia.com/gpu.present=true -o wide

# Or discover all nvidia-related labels across the cluster
oc get nodes --show-labels | grep -i nvidia || echo "No nvidia labels visible (or try without grep)"
```

Pick the first GPU node and examine it in detail:

```bash
GPU_NODE=$(oc get nodes -l nvidia.com/gpu.present=true -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "no-gpu-node")
echo "Using GPU node: $GPU_NODE"

# The most important view — look for capacity, allocatable GPUs, taints, and selector labels
oc describe node $GPU_NODE | grep -i -E 'nvidia|gpu|allocatable|capacity|taint|selector' | head -40
```

**Key things to notice and remember:**

- Under **Capacity** and **Allocatable** you will see `nvidia.com/gpu: X`
- There is usually a taint: `nvidia.com/gpu:NoSchedule`
- Useful labels the Hardware Profile will target:
  - `nvidia.com/gpu.product: NVIDIA-A100-40GB` (or L40, RTX 6000, H100, etc.)
  - `nvidia.com/gpu.memory: 40Gi`
  - `nvidia.com/gpu.count: 1` or more for multi-GPU nodes

Write down or screenshot the exact product label and the allocatable GPU count on your node. You will compare this number after the model is deployed.

---

## Task 3 — (Instructor Demo) Create the Hardware Profile in the Dashboard

While you have been inspecting the nodes, your instructor opens the **Red Hat OpenShift AI dashboard** and performs the following:

1. Navigate to **Settings → Hardware profiles** (in the left sidebar; may be under "Settings" or require the Administrator perspective / RHOAI admin role).
2. Click **Create** (or **Add new Hardware Profile**).
3. Configure a profile that matches your cluster GPUs, for example:
   - **Display name:** `NVIDIA A100 40GB (LLM Inference)`
   - **Description:** Single A100 for Triton / NIM serving
   - **Resources requests & limits:** `nvidia.com/gpu: 1`, plus sensible CPU (4–8) and memory (16–32 Gi)
   - **Node selector:** `nvidia.com/gpu.product: NVIDIA-A100-40GB` (exact value from your `oc describe node`)
   - **Tolerations:** key `nvidia.com/gpu`, operator `Exists`, effect `NoSchedule`
4. Save / Create.

Your instructor may also create a **CPU-only** lightweight profile (no accelerator resource) so everyone can see the translation even on CPU-only clusters.

**Watch the UI** — this friendly form is what gets turned into the low-level pod scheduling directives.

---

## Task 4 — (Instructor Demo) Deploy or Redeploy a Model with the Hardware Profile

The instructor now uses the newly created profile:

- Goes to **Models** (or **Deployments** / **Data Science Projects**)
- Edits the existing inference deployment **or** creates a fresh one
- In the deployment wizard / form, locates the **Hardware profile** (or **Accelerator / Resources**) selector
- Chooses the profile just created
- Deploys or updates the model

RHOAI translates the Hardware Profile into the underlying `InferenceService` / KServe pod template.

While the rollout happens, you can watch live from your terminal:

```bash
# Watch pods in your project (press Ctrl-C when you see the new pod Running)
oc get pods -n $PROJECT -w
```

---

## Task 5 — Inspect the Running Pod — Prove the Chain (Most Important Hands-on Section)

Once the model pod is `Running` (green check in the dashboard), locate it precisely:

```bash
# List all pods and identify the inference/predictor pod
oc get pods -n $PROJECT

# Typical selector for KServe single-model serving
oc get pods -n $PROJECT -l "serving.kserve.io/inferenceservice=$MODEL_NAME" -o wide

# Capture the exact pod name
POD_NAME=$(oc get pods -n $PROJECT -l "serving.kserve.io/inferenceservice=$MODEL_NAME" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
echo "Inference pod: $POD_NAME"
```

Now extract the **exact evidence** that the Hardware Profile was applied:

```bash
# Full YAML is long — we pull only the scheduling and resource sections
oc get pod $POD_NAME -n $PROJECT -o yaml > /tmp/inference-pod.yaml

echo "=== GPU resource requests/limits (injected by Hardware Profile) ==="
grep -A 20 -E 'resources:' /tmp/inference-pod.yaml | head -25

echo ""
echo "=== Node selector and tolerations (injected by Hardware Profile) ==="
grep -A 30 -E 'nodeSelector:|tolerations:' /tmp/inference-pod.yaml | head -35
```

**You should clearly see:**

- `nvidia.com/gpu: "1"` under both `requests:` and `limits:`
- The `nodeSelector` that matches the label on your GPU node
- The toleration that allows the pod to be scheduled on a tainted GPU node

Also verify placement:

```bash
# Which physical node did the scheduler choose?
oc get pod $POD_NAME -n $PROJECT -o wide
oc describe pod $POD_NAME -n $PROJECT | grep -E 'Node:|Status:|Started:'

# Compare GPU count before vs after (the allocatable number should be lower)
oc describe node $GPU_NODE | grep -A 5 'Allocatable:'
```

Finally, prove the pod really came from the profile by looking at the full pod spec or annotations if present.

```bash
# Quick one-liner many instructors love
oc get pod $POD_NAME -n $PROJECT -o yaml | grep -E 'nvidia.com/gpu|nodeSelector|tolerations' -A 3 -B 1
```

---

## Task 6 — Correlate Scheduling with Real DCGM GPU Utilization (5–8 min)

The model is now actually using a physical GPU because of the profile.

1. Ask your instructor to open **OpenShift Console → Observe → Dashboards** (or the workshop Grafana instance) and show the **DCGM** row of graphs.

2. Typical panels you will see:
   - GPU Utilization (%)
   - GPU Memory Usage (FB memory)
   - Power draw, temperature, etc.
   - Often broken down by node or by pod label

3. From your Dev Space, generate realistic inference load so the GPU actually does work:

```bash
python common/client/concurrent_load.py \
  --url "$MODEL_ROUTE" \
  --model "$MODEL_NAME" \
  --prompt "Write a detailed explanation of how Kubernetes schedules pods onto GPU nodes using node selectors and tolerations." \
  --concurrency 3 \
  --requests 30
```

While the load runs, watch the DCGM graphs:

- GPU utilization on **your** node spikes
- Memory usage increases
- The pod name or namespace filter (if available) shows activity only for the workload that selected the Hardware Profile

**The "aha" moment:** You just proved the entire chain end-to-end.

   - UI created the profile  
   - Profile produced the `nvidia.com/gpu` request in the pod  
   - Scheduler placed the pod on a real GPU node  
   - DCGM immediately started reporting live metrics for that GPU

---

## Lightweight / CPU-Only Alternative (If No GPUs Available)

If your environment has no physical GPUs or the instructor wants to demonstrate the concept safely:

- Instructor creates a **CPU-only Hardware Profile** (requests/limits for cpu/memory only; no accelerator stanza, no nvidia tolerations).
- A model is deployed (or redeployed) using that profile.
- You repeat Task 5 on the new pod.

**Expected observations:**
- The pod YAML contains **no** `nvidia.com/gpu` line
- No GPU nodeSelector or nvidia toleration
- The pod can land on any suitable worker node (or a CPU-labeled node)
- No DCGM activity for this workload

This proves Hardware Profiles are a general, powerful abstraction — GPUs are simply the most interesting case for LLM inference.

---

## What You Should Now Understand

- **Hardware Profiles** are the single source of truth in the OpenShift AI dashboard for accelerator-aware deployments. They abstract away raw Kubernetes scheduling details.
- When you pick a profile during model deployment, RHOAI automatically injects the corresponding `resources.requests.nvidia.com/gpu`, `nodeSelector`, and `tolerations` into the KServe pod template.
- The standard Kubernetes scheduler (plus any extended resources from the NVIDIA GPU Operator) is responsible for finding a node that both has the GPU capacity **and** satisfies the taints/selectors.
- Once the pod is bound to a GPU, the DCGM exporter (part of the GPU Operator DaemonSet) publishes high-fidelity metrics that flow into OpenShift monitoring, Grafana, and the RHOAI metrics tabs.
- You can always debug scheduling problems from a normal user terminal using:
  - `oc describe node`
  - `oc get pod -o yaml`
  - `oc get hardwareprofile -n redhat-ods-applications`
- The same mechanism supports advanced scenarios: MIG profiles, multi-GPU, NVLink, specific VRAM sizes, and project-scoped visibility.

---

## Quick Reference Commands

```bash
# GPU infrastructure
oc get pods -n nvidia-gpu-operator -l app=nvidia-dcgm-exporter
oc get nodes -l nvidia.com/gpu.present=true
oc describe node <gpu-node-name> | grep -i -E 'nvidia|allocatable'

# Hardware Profiles (CRs)
oc get hardwareprofile -n redhat-ods-applications
oc describe hardwareprofile <profile-name> -n redhat-ods-applications

# Running inference pod (after profile is used)
oc get pods -n $PROJECT -l "serving.kserve.io/inferenceservice=$MODEL_NAME"
oc get pod $POD_NAME -n $PROJECT -o yaml | grep -E 'nvidia.com/gpu|resources:|nodeSelector:|tolerations:' -A 8 -B 2

# Watch everything during deployment
oc get pods -n $PROJECT -w
```

---

**You have now completed the core technical foundation of GPU-aware model serving.**

**Ready for Module 06 — Fault Tolerance & Disaster Recovery.** Keep your terminal session and the OpenShift AI dashboard handy.