#!/usr/bin/env python3
"""
Triton Inference Server v2 REST client for Red Hat OpenShift AI demos.

Usage:
  python triton_infer.py --url https://your-model-route --model tiny-llama --prompt "Hello"
  python triton_infer.py --url $MODEL_ROUTE --model $MODEL_NAME --prompt "..." --verbose

Supports both raw text (for models with tokenizer backend) and structured tensor inputs.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests
from rich.console import Console
from rich.json import JSON

console = Console()


def post_inference(
    base_url: str,
    model_name: str,
    inputs: list[Dict[str, Any]],
    model_version: str = "",
    timeout: int = 60,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Call Triton's /v2/models/{model}/infer endpoint."""
    version = f"/{model_version}" if model_version else ""
    url = f"{base_url.rstrip('/')}/v2/models/{model_name}{version}/infer"

    payload = {
        "inputs": inputs,
        # "outputs": []  # add if you want specific output tensors only
    }

    if verbose:
        console.print(f"[cyan]POST[/cyan] {url}")
        console.print(JSON.from_data(payload))

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def make_text_input(prompt: str, name: str = "text_input", shape: list[int] | None = None) -> Dict[str, Any]:
    """Common pattern for text-generation models served via Triton's Python or tokenizer backend."""
    if shape is None:
        shape = [1]
    return {
        "name": name,
        "shape": shape,
        "datatype": "BYTES",
        "data": [prompt],
    }


def make_tensor_input(data: list, name: str, datatype: str = "FP32", shape: list[int] | None = None) -> Dict[str, Any]:
    if shape is None:
        shape = [1, len(data)]
    return {
        "name": name,
        "shape": shape,
        "datatype": datatype,
        "data": data,
    }


def run_single(
    base_url: str,
    model_name: str,
    prompt: str,
    verbose: bool = False,
) -> Dict[str, Any]:
    """High-level helper used by most demo scripts."""
    start = time.perf_counter()
    result = post_inference(
        base_url=base_url,
        model_name=model_name,
        inputs=[make_text_input(prompt)],
        verbose=verbose,
    )
    elapsed = (time.perf_counter() - start) * 1000

    if verbose:
        console.print(f"[green]Latency: {elapsed:.1f} ms[/green]")
        console.print(JSON.from_data(result))

    return {"result": result, "latency_ms": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Triton v2 inference client for OpenShift AI demos")
    parser.add_argument("--url", required=True, help="Base URL of the model route (https://...)")
    parser.add_argument("--model", required=True, help="Model name as known to Triton (e.g. tiny-llama)")
    parser.add_argument("--prompt", default="Explain Red Hat OpenShift AI in one sentence.", help="Prompt text")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--times", type=int, default=1, help="Repeat the request N times and print stats")
    args = parser.parse_args()

    latencies = []
    for i in range(args.times):
        if args.times > 1:
            console.print(f"[dim]Request {i+1}/{args.times}[/dim]")
        data = run_single(args.url, args.model, args.prompt, verbose=args.verbose)
        latencies.append(data["latency_ms"])

    if args.times > 1:
        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        console.print(f"\n[bold]Stats[/bold] — avg: {avg:.1f} ms | p95: {p95:.1f} ms | min/max: {min(latencies):.1f}/{max(latencies):.1f}")

    # Pretty print last result
    console.print("\n[bold]Last response:[/bold]")
    console.print(JSON.from_data(data["result"]))


if __name__ == "__main__":
    main()