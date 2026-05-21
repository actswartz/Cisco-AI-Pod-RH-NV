# Module 06 — Fault Tolerance and Disaster Recovery (Student Lab)

**Time:** 35–45 minutes (primarily observation while running steady load)

---

## Your Mission

Prove to yourself that production LLM serving on OpenShift AI is resilient:

- A pod can be killed **under live traffic** and clients see almost zero interruption.
- The system can scale replicas up and down transparently.
- "Disaster recovery" for the model itself is achieved by simply re-pointing at a backup copy of the weights in object storage — no image rebuilds, no golden containers, no client changes.

You will generate the traffic, measure the recovery, and watch the platform heal itself.

---

## Setup (2 minutes)

Open a terminal in your Dev Space and prepare your environment.

```bash
cd /projects/rhoai-llm-inference-demos
source /home/user/.venv/bin/activate
```

Export the values provided by your instructor:

```bash
export MODEL_ROUTE="https://<instructor-gives-you-this>"
export MODEL_NAME="<instructor-gives-you-this>"
export NAMESPACE="<instructor-gives-you-this>"   # Data Science Project name
```

Quick connectivity check:

```bash
echo "Route : $MODEL_ROUTE"
echo "Model : $MODEL_NAME"
echo "NS    : $NAMESPACE"

curl -I "$MODEL_ROUTE/v2/health/ready" 2>/dev/null | head -3 || \
curl -I "$MODEL_ROUTE/v1/models" -H "Authorization: Bearer dummy" 2>/dev/null | head -3
```

Send one test request:

```bash
python common/client/triton_infer.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "Module 06 resilience test — are you there?"
```

You should receive a clean response. Leave this terminal open.

**Tip:** Open a **second terminal tab** (`Terminal → New Terminal`) now. You will use it for watch commands while the load loop runs in the first tab.

---

## Task 1 — Run the Continuous Low-Rate Load Loop

This loop simulates realistic steady traffic (approximately 1 request per second). Multiple students running it simultaneously creates the "live production load" the instructor will disrupt.

In your **first terminal**, run the following clean loop (recommended):

```bash
echo "=== CONTINUOUS LOAD STARTED — Leave this running for the whole module ==="
echo "Press Ctrl-C only when the instructor says the module is complete."
echo ""

while true; do
  TS=$(date '+%H:%M:%S')
  if python common/client/triton_infer.py \
       --url "$MODEL_ROUTE" \
       --model "$MODEL_NAME" \
       --prompt "ping" \
       > /tmp/ping.log 2>&1 ; then
    echo "[$TS] ✓ OK"
  else
    echo "[$TS] ✗ ERROR  (see tail of /tmp/ping.log)"
    tail -3 /tmp/ping.log
  fi
  sleep 1
done
```

**Alternative (simpler, matches instructor demo exactly):**

```bash
while true; do
  python common/client/triton_infer.py \
    --url $MODEL_ROUTE --model $MODEL_NAME --prompt "ping"
  sleep 1
done
```

The first version is strongly preferred because the terminal stays readable (one clean line per second) and makes recovery time measurement trivial.

Leave the loop **running** for the remainder of the module.

**To see detailed latency on any individual request** (without spamming the continuous loop), run this in your second terminal:

```bash
python common/client/triton_infer.py \
  --url $MODEL_ROUTE --model $MODEL_NAME --prompt "ping" -v
```

---

**Tip for instructors/students:** The simple `while true` version from the instructor guide also works if you prefer raw output:

```bash
while true; do python common/client/triton_infer.py --url $MODEL_ROUTE --model $MODEL_NAME --prompt "ping"; sleep 1; done
```

---



## Task 2 — The "Kill the Pod" Live Recovery Demo (Core Experience)

This is the single most memorable demonstration in the workshop.

### What the Instructor Will Do

1. Confirm that several students have the continuous load loop running.
2. In the OpenShift AI dashboard (or via `oc`), locate the currently running predictor pod for your model.
3. Delete the pod (trash icon or `oc delete pod <pod-name>`).

### What You Should See — Terminal (Load Loop)

- For 1–3 seconds you will see one or more `✗ ERROR` lines (connection refused, timeout, 5xx, or Python exception).
- Almost immediately, successful `✓ OK` lines resume.
- The exact same `MODEL_ROUTE` continues to work — **your client never changed**.

Typical observed result: **0–2 errors** before traffic is healthy again.

### Recovery Time Measurement Exercise (Record Your Numbers)

While the pod is being deleted, carefully note:

1. Timestamp of the **last successful** (`✓ OK`) line **before** the error window.
2. Timestamp of the **first successful** (`✓ OK`) line **after** recovery.
3. How many error lines appeared.

**Your measurements:**

```
Last successful request:     HH:MM:SS
First successful after kill: HH:MM:SS
Client-visible outage:       _____ seconds
Errors observed:             _____
```

Share your numbers with the class. In a well-tuned demo you will usually see **under 10–15 seconds** of impact, often just a single ping failure.

### What You Should See — Dashboard & Cluster

- **RHOAI / OpenShift Console**:
  - Old pod transitions to `Terminating`.
  - A new pod with a different name appears immediately.
  - Pod lifecycle: `Pending` → `ContainerCreating` → `Running` → model initialization → `Ready`.
- **OpenShift Events** (in your second terminal):

  ```bash
  oc get events -n $NAMESPACE --sort-by=.lastTimestamp | tail -15
  ```

  Look for `Created pod`, `Started container`, and readiness messages related to your model.

- The **Route** and external URL never disappear or change.

**Why the impact is so small:**

- The Deployment controller reacts instantly.
- OpenShift Service and Route endpoints are updated automatically.
- KServe’s readiness probe gates traffic until the new replica is truly healthy.
- Clients are completely decoupled from individual pod identities.

---

## Task 3 — Autoscaling Observation (Manual or HPA/KEDA)

### If Your Cluster Has Autoscaling Configured

Your instructor may trigger a sudden load spike (ask several students to run `concurrent_load.py` with high `--concurrency`) or directly scale the model.

**Watch the replica count change live** in your second terminal:

```bash
# Watch pods for your specific InferenceService
oc get pods -n $NAMESPACE -w \
  -l serving.kserve.io/inferenceservice=$MODEL_NAME
```

Or a broader view:

```bash
oc get pods -n $NAMESPACE -w | grep -E 'predictor|model|kserve'
```

**Alternative — watch the Deployment directly** (the underlying controller):

```bash
oc get deploy -n $NAMESPACE -w | grep -i $MODEL_NAME
```

### Manual Scaling Demo (Always Available)

Even without HPA, the instructor can demonstrate horizontal scaling:

1. Instructor increases the desired replica count for the model (dashboard or `oc scale` / edit InferenceService).
2. New pods appear.
3. Your running load loop automatically benefits from the additional capacity (no client changes).

**What success looks like:**

- Replica count visibly increases (e.g. 1 → 2 or 1 → 3).
- All new pods reach `Running` + `Ready`.
- You can confirm traffic is being load-balanced across them (later modules or Observe dashboards).

When the instructor scales back down, you will see pods terminate cleanly while your load loop continues with no client-side awareness.

---

## Task 4 — Disaster Recovery via Data Connection Swap

This demonstrates the most powerful form of resilience for LLM workloads: **storage portability**.

### Instructor Preparation (Pre-Class)

The instructor has an identical copy of the model weights in a second S3 bucket (or secondary data connection / MinIO instance).

### The Demo

1. Instructor shows the **current** data connection / storage location of the live model (`oc get inferenceservice $MODEL_NAME -o yaml` or dashboard UI).
2. Instructor updates the model to use the **backup data connection**.
3. Instructor redeploys the InferenceService.

### What You Should Observe

- Existing pod(s) are terminated (your load loop will show a brief error window, similar to Task 2 but usually longer).
- Brand-new pod(s) start.
- **Critical observation — inspect the new pod’s logs** (instructor will share the pod name or you can find it):

  ```bash
  # In second terminal — follow logs of the newly created pod
  oc logs -f <new-predictor-pod-name> -n $NAMESPACE -c kserve-container | grep -E 'model|download|s3|storage|loading|triton'
  ```

  You should see clear evidence that weights are being pulled from the **backup** location (different bucket name, different path, or "restoring from DR bucket").

- Once the new pod reaches Ready, your continuous load loop resumes success against the **unchanged** `MODEL_ROUTE`.

- The model answers identically to before.

**DR Recovery Time Measurement (compare with Task 2)**

```
DR swap initiated:           HH:MM:SS
New pod Ready:               HH:MM:SS
DR recovery duration:        _____ seconds (usually longer than pod-kill)
```

**Why DR recovery is typically slower than a simple pod kill:**

- Pod kill re-uses the cached container image on the node.
- DR swap usually involves fresh model weight download from object storage (network-bound) + GPU memory loading.

### The Profound Takeaway

Changing the source of the model weights is just a configuration edit + redeploy.

- No Dockerfiles touched.
- No container images rebuilt or re-pushed.
- No client configuration updated.
- The exact same ServingRuntime and container image now serves a model restored from "disaster" storage.

This is true infrastructure-as-code + object-storage-based model management.

---

## Handy Observation Commands (Keep in Second Terminal)

```bash
# 1. Live pod watch (best during all demos)
oc get pods -n $NAMESPACE -w

# 2. Focused on your model
oc get pods -n $NAMESPACE \
  -l serving.kserve.io/inferenceservice=$MODEL_NAME

# 3. InferenceService definition (look for storage / dataConnection)
oc get inferenceservice $MODEL_NAME -n $NAMESPACE -o yaml

# 4. Recent events
oc get events -n $NAMESPACE --sort-by=.lastTimestamp | tail -20

# 5. Quick replica count
oc get inferenceservice $MODEL_NAME -n $NAMESPACE

# 6. Route (prove it never changes)
oc get route -n $NAMESPACE | grep -i model || oc get route -n $NAMESPACE
```

---

## What Success Looks Like

- You ran a continuous, clean load loop that survived a pod deletion with only a handful of errors.
- You personally measured sub-15-second recovery time under real traffic.
- You watched replica count change (manually or automatically) with zero impact on the client URL.
- You witnessed a full data-connection "DR" swap and saw the new pod load weights from the backup bucket.
- You now have first-hand evidence that **the platform heals itself** and that model artifacts are portable, not baked into immutable images.

---

## What You Should Now Understand

- Kubernetes self-healing + KServe’s controller model deliver production-grade fault tolerance for inference workloads.
- A stable external Route + Service is the secret to zero-downtime client experience.
- Horizontal scaling (manual or automatic) is a natural extension of the same architecture.
- Separating compute (runtime container) from data (weights in S3) enables trivial, fast, auditable disaster recovery and multi-region portability.
- You have now experienced the complete resilience story: pod failure → recovery, scaling, and storage-level DR.

---

**Outstanding. You have completed the resilience module.**

You now understand why teams trust Red Hat OpenShift AI to run real customer-facing LLM services.

**Next: Module 07 — Monitoring & Performance.**

We will keep the same model and load techniques while we explore OpenShift Observe, Grafana dashboards, DCGM GPU metrics, and how to correlate queue depth, batching, and latency in real time.

Keep your Dev Space and load loops ready.
