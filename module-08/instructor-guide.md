# Module 08 — Cisco-NVIDIA Integration with Scalable Inference (Instructor Guide)

**Duration:** 50–60 min (capstone)

## If You Have NGC / Enterprise NIM Access

1. Enable the **NVIDIA NIM** tile in Applications → Explore (paste NGC key).
2. Deploy a real optimized model (Llama 3.1 8B or Nemotron) via the NIM workflow.
3. Run the exact same `concurrent_load.py` script from student workspaces against:
   - The generic Triton deployment from earlier in the day
   - The new NIM deployment
4. Side-by-side comparison in OpenShift metrics:
   - Significantly higher throughput (often 2–4×)
   - Much better latency tail
   - Lower GPU memory for the same concurrency (thanks to TensorRT-LLM kernels + optimized microservice)

## If You Do NOT Have NGC Access (Most Common Classroom Situation)

Run the comparison using two different Triton configurations:
- One with conservative batching / no cache
- One with aggressive dynamic batching + response cache + best-practice model config

Or deploy both a Triton runtime and the built-in vLLM / TGIS runtime (Red Hat ships these) and show students the different performance characteristics and ease-of-use tradeoffs.

## Closing Topology View

End the day with the full picture in the OpenShift AI dashboard:

- Dev Spaces workspaces (student coding / testing environment)
- Model server (NIM or Triton)
- Hardware Profiles + GPU nodes
- OpenShift monitoring + DCGM
- (Whiteboard) Cisco Nexus fabric underneath it all

**"You now understand the entire vertical, from a Python `openai` call in a browser-based IDE to the photons moving across a Nexus switch."**

This is the exact stack Red Hat + NVIDIA + Cisco are selling to enterprise customers for private AI factories.