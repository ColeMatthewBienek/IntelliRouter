#!/usr/bin/env python3
"""
Intelli-Router Classification Test Suite

Runs 12 sample prompts across all 4 tiers and validates routing decisions.
Requires Ollama running locally with the triage model pulled.
"""

import subprocess
import json
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFY_SCRIPT = os.path.join(SCRIPT_DIR, "classify.py")

TEST_PROMPTS = [
    # Simple (3)
    ("Hello!", "simple"),
    ("What's 2+2?", "simple"),
    ("What time is it?", "simple"),
    # Moderate (3)
    ("Summarize the key differences between REST and GraphQL", "moderate"),
    ("Write a product description for a vintage t-shirt", "moderate"),
    ("Explain how DNS works", "moderate"),
    # Coding (4)
    ("Write a Python script that scrapes product prices from a URL", "coding"),
    ("Fix this bug in my React component that causes infinite re-renders", "coding"),
    ("Create a Docker compose file for a Node.js app with Redis and Postgres", "coding"),
    ("Debug this race condition in my async Python code and suggest a fix with tests", "coding"),
    # Complex (2)
    ("Design a microservices architecture for an e-commerce platform with event sourcing", "complex"),
    ("Write a 2000-word blog post analyzing AI trends in print-on-demand", "complex"),
]


def run_test(prompt, expected):
    start = time.time()
    result = subprocess.run(
        ["python3", CLASSIFY_SCRIPT, prompt],
        capture_output=True,
        text=True,
        timeout=15,
    )
    elapsed = time.time() - start
    try:
        data = json.loads(result.stdout.strip())
        tier = data.get("tier", "???")
        model = data.get("model", "???")
        match = "\u2705" if tier == expected else "\u274c"
        print(f"{match} [{elapsed:.1f}s] {tier:>8} \u2192 {model}")
        print(f"           {prompt[:65]}")
        if tier != expected:
            print(f"           Expected: {expected}, Got: {tier} ({data.get('reason', '')})")
        return tier == expected
    except Exception as e:
        print(f"\u274c ERROR: {e} | {prompt[:60]}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Intelli-Router Classification Test (4-tier)")
    print("=" * 70)
    correct = sum(run_test(p, e) for p, e in TEST_PROMPTS)
    print("=" * 70)
    print(f"Results: {correct}/{len(TEST_PROMPTS)} correct")
    if correct == len(TEST_PROMPTS):
        print("All tests passed! Router is ready.")
    else:
        print("Some misclassifications. Review SYSTEM_PROMPT in classify.py.")
