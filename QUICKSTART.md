# Quick Start — RHOAI LLM Inference Demos Workshop

## For Instructors (5 minutes to prepare the class)

1. Fork this repo or copy it to a Git location your students can reach.
2. (Recommended) Pre-deploy one model in OpenShift AI (NIM or custom Triton) and expose its Route.
3. Update the `devfile.yaml` only if you need a different base image.
4. Give students this single link:
   ```
   https://<your-devspaces-host>/?url=https://github.com/your-org/rhoai-llm-inference-demos
   ```
5. Open the Module 01 instructor guide and follow the 30-minute flow.

## For Students (first 3 minutes)

Just click the link your instructor gives you. Everything else is already in the workspace.

After the workspace finishes starting:

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate
python common/client/triton_infer.py --help
```

Then follow the instructor through the modules.

## Minimal Cluster Requirements (for a great experience)

- OpenShift 4.14+ with OpenShift AI 2.10+ (or 3.x)
- KServe (single-model serving) enabled
- Optional but recommended: NVIDIA GPU Operator + at least one GPU node
- S3 or MinIO for model storage
- Student access to a Data Science Project (or cluster-admin for the demo namespace)

## No GPU / No NGC? Still 100% Usable

Use the files in `common/yamls/offline/`. The first six modules work beautifully with a CPU-only Triton + tiny model (or even a mock "sleepy" Python backend). Module 7 and 8 still teach the monitoring and comparison concepts using two different Triton configurations.

## Getting Help During Class

All commands the students ever need are in the `common/client/` and `common/load/` folders and the per-module student labs. The instructor guides have the exact clicks and YAML edits.

---

**You now have everything you need to run a world-class, reproducible, Red Hat OpenShift AI LLM inference workshop.**