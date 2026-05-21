# Module 07 — Monitoring and Performance Metrics (Instructor Guide)

**Duration:** 40 min

## Live Dashboard Tour

Open three things side-by-side:

1. OpenShift Console → **Observe → Dashboards** (or custom Grafana) showing:
   - DCGM: GPU utilization, memory, temperature, power
   - Triton: queue wait time, compute latency, batch size distribution, cache hit rate

2. The RHOAI model metrics tab (if NIM) or the KServe/Triton Prometheus metrics.

3. Student Dev Spaces running a controlled load test.

## The Correlation Exercise

Have students deliberately create a queue backlog (high concurrency + large prompts).

Watch on the dashboard:
- Queue depth / wait time spikes
- 2–3 seconds later, inference latency follows
- GPU utilization may actually *drop* (starved for work because of queuing)

Then reduce concurrency or enable better batching and watch the curves invert.

This is the most powerful "I finally understand the metrics" moment of the day.