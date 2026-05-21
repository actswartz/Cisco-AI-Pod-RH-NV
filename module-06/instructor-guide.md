# Module 06 — Fault Tolerance and Disaster Recovery (Instructor Guide)

**Duration:** 40 min

## The "Kill the Pod" Live Demo (Most Memorable)

1. Start a continuous low-rate load from several student Dev Spaces:
   ```bash
   while true; do python common/client/triton_infer.py --url $MODEL_ROUTE --model $MODEL_NAME --prompt "ping"; sleep 1; done
   ```
2. In the OpenShift Console, find the running inference pod and delete it (`oc delete pod ...` or click the trash can in the dashboard).
3. Watch:
   - The load script shows only a brief spike or one or two errors (KServe / the Deployment controller immediately brings a new pod up)
   - The Route never went away — clients never had to change anything
   - New pod appears with the same model loaded

**This is the moment people really trust the platform.**

## Autoscaling (if you have metrics-based HPA or KEDA configured)

Trigger a sudden 5× load spike from the Dev Spaces. Show the replica count climb in the RHOAI dashboard.

## Data Connection / DR Portability

- Have a second S3 bucket (or MinIO) with the same model weights.
- Edit the InferenceService / data connection to point at the backup bucket.
- Redeploy — same container image, different weights pulled at start time.
- Prove that "disaster recovery" for the model itself is just "change the pointer and redeploy".

No container rebuilds. No golden images. Just infrastructure as code + object storage.