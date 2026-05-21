# Module 02 — First Inference from the Workspace (Instructor Guide)

**Duration:** 40–50 minutes  
**Goal:** Make the inference pipeline *concrete* by executing a request while everyone watches the exact path through preprocess → inference → postprocess.

---

## Pre-Class Setup

- Model from Module 01 still running and healthy
- Students have their Dev Spaces open and have completed the Module 01 verification
- You have the exact model name and route URL written on the whiteboard or slide

---

## Detailed Walkthrough

### 1. Set Environment Variables Together (5 min)

Have every student run in their Dev Space:

```bash
export MODEL_ROUTE="https://<paste-the-route-from-dashboard>"
export MODEL_NAME="<exact-model-name-from-dashboard>"

echo $MODEL_ROUTE
echo $MODEL_NAME
```

### 2. Simple curl First (8 min)

Show the raw HTTP request so nobody thinks there is magic.

```bash
# Triton v2 style (most common for custom runtimes)
curl -s -X POST "$MODEL_ROUTE/v2/models/$MODEL_NAME/infer" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "text_input",
      "shape": [1],
      "datatype": "BYTES",
      "data": ["Explain Red Hat OpenShift in exactly one sentence."]
    }]
  }' | jq .
```

**Watch the RHOAI model logs live** while the request executes. Point out:
- The HTTP handler receiving the request
- Any tokenization / preprocessing
- Actual model forward pass (this is where the "thinking" time appears)
- Post-processing / detokenization
- Response being sent back

### 3. Python Client — The Tool They Will Use All Day (10 min)

```bash
python common/client/triton_infer.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "What is the difference between OpenShift and Kubernetes?" \
  -v
```

Run it twice:
- First time (cold start / first tokenization) — usually slower
- Second time — faster because of any internal caching the runtime does

### 4. OpenAI-Compatible Path (if using NIM or vLLM) (8 min)

If your deployed model is a NIM or vLLM-based deployment:

```bash
python common/client/openai_infer.py \
  --base-url "$MODEL_ROUTE/v1" \
  --model "$MODEL_NAME" \
  --prompt "Why does batching improve LLM throughput?" \
  --stream
```

Emphasize that the **client code changes** but the infrastructure (Route, KServe, scaling, GPU scheduling) stays exactly the same.

### 5. Side-by-Side Observation Exercise (10 min)

Split the class view:

- Left half of screen (or second monitor): **OpenShift AI → Model → Logs**
- Right half: student terminal running the Python client with `--verbose`

Run the request again. Have students narrate what they see:
- "Request hits the route at 10:14:03.112"
- "Pod receives it at 10:14:03.118"
- "Preprocessing done at 10:14:03.145"
- "Inference started..."
- "First token generated at..."
- "Full response returned at 10:14:04.872"

This is the moment the abstract "inference pipeline" becomes real for them.

### 6. Collect Baseline Numbers (5 min)

Have everyone run the concurrent loader with very low load:

```bash
python common/client/concurrent_load.py \
  --url $MODEL_ROUTE \
  --model $MODEL_NAME \
  --prompt "Hello" \
  --concurrency 2 \
  --requests 10
```

Write the average and p95 numbers on the whiteboard. We will beat these numbers in Module 3 by tuning batching.

---

## Lightweight Path Notes

If you are on CPU-only Triton:

- Expect 300–2000 ms per request depending on model size
- The pipeline observation is *more* valuable, not less — students can actually read the timestamps
- Use a deliberately slow "echo + sleep(0.4)" Python backend model so every stage is visible

---

## Transition to Module 03

> "Now that we can see the pipeline, we are going to break it on purpose (by setting max_batch_size=1) and then make it dramatically faster by enabling dynamic batching and caching. That is the heart of production LLM serving."

**End of Module 02.**