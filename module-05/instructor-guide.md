# Module 05 — GPU Scheduling and Hardware Profiles (Instructor Guide)

**Duration:** 40–50 min

## Key Actions

1. Show the NVIDIA GPU Operator and DCGM pods in the `nvidia-gpu-operator` namespace.
2. From a Dev Space: `oc describe node | grep -i nvidia` — students see the `nvidia.com/gpu` allocatable labels.
3. In OpenShift AI UI: **Settings → Hardware profiles → Create** — select "A100 40GB" or "L40" or "RTX 6000" profile.
4. Deploy (or re-deploy) the model using that Hardware Profile.
5. `oc get pod -o yaml` of the resulting inference pod — show the `nvidia.com/gpu: "1"` request/limit that RHOAI injected.

**Whiteboard:** Hardware Profile (UI abstraction) → KServe pod spec → scheduler places on a node that has the GPU → DCGM starts reporting.

## Cisco + NVIDIA angle
The same Hardware Profile that gives you the GPU also lets you request NVLink or specific MIG profiles in more advanced setups. The underlay (Cisco Nexus) is what makes the GPUs talk to each other at full bandwidth when you eventually do multi-GPU or multi-node inference.

## Lightweight Path
Create a "CPU-only" Hardware Profile (requests/limits only, no accelerator) so students still see the full UI → pod spec translation even without GPUs.