# Module 04 — Load Balancing and Traffic Optimization (Instructor Guide)

**Duration:** 40 min

## Core Demo

1. In the OpenShift AI dashboard (or `oc scale`), increase the model deployment from 1 → 3 replicas.
2. Confirm the single Route now has three ready pods behind it (`oc get endpoints` or the dashboard pod list).
3. From student Dev Spaces, run a sustained load:
   ```bash
   hey -n 1000 -c 20 $MODEL_ROUTE/v2/models/$MODEL_NAME/infer \
     -m POST -T 'application/json' -d '{"inputs":[...]}'   # or use the Python concurrent_load.py
   ```
4. Open **OpenShift Console → Observe → Metrics → by pod** and show traffic nicely distributed.
5. (Whiteboard) Mention that Cisco Nexus Dashboard would show the physical underlay heat map at the same time OpenShift is doing L7 balancing.

**Teaching point:** One Route + multiple model server pods = automatic horizontal scaling with zero client changes.

## Student Action
Students run the load generator and watch the pod CPU / request graphs split across replicas in real time.

## Lightweight Note
Works identically on CPU replicas. Great for proving the scaling story before you introduce GPUs.