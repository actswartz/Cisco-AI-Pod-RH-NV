#!/usr/bin/env python3
"""
Lightweight concurrent load generator for OpenShift AI inference demos.

Fires N concurrent requests (threads) against a Triton or OpenAI-compatible endpoint
and reports latency distribution. Perfect for quick "before/after" comparisons when
changing batch size, replica count, or switching between Triton and NIM.

Usage:
  python concurrent_load.py --url $ROUTE --model tiny-llama --prompt "test" --concurrency 10 --requests 50

For Triton use the /v2/models/... path or wrap with the triton_infer helper.
For NIM/vLLM use the OpenAI client path.
"""

import argparse
import concurrent.futures
import statistics
import time
from dataclasses import dataclass
from typing import Callable, List

import requests
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Result:
    latency_ms: float
    status: int
    error: str | None = None


def fire_triton_request(url: str, model: str, prompt: str) -> Result:
    """Minimal Triton v2 REST call (text input)."""
    start = time.perf_counter()
    try:
        payload = {
            "inputs": [{
                "name": "text_input",
                "shape": [1],
                "datatype": "BYTES",
                "data": [prompt],
            }]
        }
        r = requests.post(f"{url.rstrip('/')}/v2/models/{model}/infer", json=payload, timeout=120)
        latency = (time.perf_counter() - start) * 1000
        return Result(latency_ms=latency, status=r.status_code, error=None if r.ok else r.text[:200])
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return Result(latency_ms=latency, status=0, error=str(e))


def fire_openai_request(base_url: str, model: str, prompt: str, api_key: str = "dummy") -> Result:
    """Minimal OpenAI chat completion call (non-streaming)."""
    start = time.perf_counter()
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
                "temperature": 0.7,
            },
            timeout=120,
        )
        latency = (time.perf_counter() - start) * 1000
        return Result(latency_ms=latency, status=r.status_code, error=None if r.ok else r.text[:200])
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return Result(latency_ms=latency, status=0, error=str(e))


def run_load(
    target_fn: Callable[[], Result],
    concurrency: int,
    total_requests: int,
) -> List[Result]:
    results: List[Result] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(target_fn) for _ in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    return results


def print_stats(results: List[Result], title: str = "Results"):
    ok = [r for r in results if r.status == 200]
    errs = [r for r in results if r.status != 200]

    latencies = [r.latency_ms for r in ok]
    if not latencies:
        console.print("[red]All requests failed[/red]")
        return

    table = Table(title=title)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total requests", str(len(results)))
    table.add_row("Successful (200)", str(len(ok)))
    table.add_row("Errors", str(len(errs)))
    table.add_row("Latency avg (ms)", f"{statistics.mean(latencies):.1f}")
    table.add_row("Latency p50 (ms)", f"{statistics.median(latencies):.1f}")
    if len(latencies) >= 10:
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        table.add_row("Latency p95 (ms)", f"{p95:.1f}")
    table.add_row("Latency min / max", f"{min(latencies):.1f} / {max(latencies):.1f}")

    console.print(table)

    if errs:
        console.print(f"\n[red]First error sample:[/red] {errs[0].error}")


def main():
    parser = argparse.ArgumentParser(description="Concurrent load generator for RHOAI inference demos")
    parser.add_argument("--url", required=True, help="Model base URL (Triton route or NIM /v1 base)")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="Explain Kubernetes in one sentence.")
    parser.add_argument("--concurrency", "-c", type=int, default=5, help="Number of concurrent workers")
    parser.add_argument("--requests", "-n", type=int, default=20, help="Total number of requests to fire")
    parser.add_argument("--openai", action="store_true", help="Use OpenAI-compatible /v1/chat/completions path")
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    if args.openai:
        def target():
            return fire_openai_request(args.url, args.model, args.prompt, args.api_key)
        mode = "OpenAI-compatible"
    else:
        def target():
            return fire_triton_request(args.url, args.model, args.prompt)
        mode = "Triton v2"

    console.print(f"[bold]Firing {args.requests} requests at {args.concurrency} concurrency against {mode}[/bold]")
    console.print(f"URL: {args.url}  Model: {args.model}\n")

    start_wall = time.perf_counter()
    results = run_load(target, args.concurrency, args.requests)
    wall = time.perf_counter() - start_wall

    print_stats(results, title=f"Load test — {mode}")
    console.print(f"\nWall-clock time: {wall:.2f}s | Effective RPS: {len(results)/wall:.1f}")


if __name__ == "__main__":
    main()