#!/usr/bin/env python3
"""
OpenAI-compatible client for NVIDIA NIM, vLLM, TGIS, or any OpenShift AI deployment
exposing the /v1/chat/completions endpoint.

Usage examples:
  python openai_infer.py --base-url https://nim-route/v1 --api-key $TOKEN \
                         --model meta/llama3-1-8b-instruct --prompt "Hello"

  # Streaming
  python openai_infer.py ... --stream
"""

import argparse
import os
import sys
import time
from typing import Optional

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def get_client(base_url: str, api_key: str = "dummy") -> OpenAI:
    """Create an OpenAI client pointed at the NIM / vLLM route."""
    return OpenAI(base_url=base_url.rstrip("/") + "/v1", api_key=api_key)


def chat(
    client: OpenAI,
    model: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
    stream: bool = False,
) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.perf_counter()

    if stream:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        collected = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                collected += piece
                console.print(piece, end="")
        console.print()
        elapsed = (time.perf_counter() - start) * 1000
        return {"content": collected, "latency_ms": elapsed, "streamed": True}
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        elapsed = (time.perf_counter() - start) * 1000
        content = resp.choices[0].message.content
        console.print(Markdown(content or "(empty)"))
        return {
            "content": content,
            "latency_ms": elapsed,
            "usage": getattr(resp, "usage", None),
            "streamed": False,
        }


def main():
    parser = argparse.ArgumentParser(description="OpenAI-compatible inference client for OpenShift AI (NIM/vLLM)")
    parser.add_argument("--base-url", required=True, help="Base inference URL, e.g. https://your-route/v1 or https://.../v1")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", "dummy"), help="API key or token (NIM often uses NGC key or service account token)")
    parser.add_argument("--model", required=True, help="Model identifier (e.g. meta/llama3-1-8b-instruct or the name you deployed)")
    parser.add_argument("--prompt", default="Explain the benefits of running inference on Red Hat OpenShift AI.", help="User prompt")
    parser.add_argument("--system", default="You are a helpful, concise assistant.", help="Optional system prompt")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--stream", action="store_true", help="Enable streaming output")
    parser.add_argument("--times", type=int, default=1, help="Run the prompt N times and report stats")
    args = parser.parse_args()

    client = get_client(args.base_url, args.api_key)
    latencies = []

    for i in range(args.times):
        if args.times > 1:
            console.print(f"\n[dim]=== Run {i+1}/{args.times} ===[/dim]")
        result = chat(
            client,
            model=args.model,
            prompt=args.prompt,
            system=args.system,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            stream=args.stream,
        )
        latencies.append(result["latency_ms"])

    if args.times > 1:
        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        console.print(f"\n[bold green]Aggregate[/bold green] — avg: {avg:.1f} ms | p95: {p95:.1f} ms | min/max: {min(latencies):.1f}/{max(latencies):.1f} ms")


if __name__ == "__main__":
    main()