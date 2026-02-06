#!/usr/bin/env python3
"""
Intelli-Router Triage Script

Calls a local Ollama model to classify incoming task complexity,
then outputs the recommended model for OpenClaw routing.

Triage model: qwen3:1.7b (~1.4 GB VRAM, <500ms per classification)
"""

import json
import sys
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
TRIAGE_MODEL = "qwen3:1.7b"

SYSTEM_PROMPT = """Pick exactly ONE category for this task. You must pick only one.

1. coding - writing, fixing, debugging, or reviewing code and scripts
2. complex - content over 500 words, system architecture, deep analysis
3. moderate - explanations, summaries, short writing, product descriptions
4. simple - greetings, quick facts, one-line answers

Reply with ONLY one JSON object. The tier MUST be one single word from: coding, complex, moderate, simple

Example replies:
{"tier": "simple", "reason": "greeting"}
{"tier": "coding", "reason": "asks to write a script"}
{"tier": "moderate", "reason": "asks for an explanation"}
{"tier": "complex", "reason": "requires 2000 word essay"}"""

TIER_MAP = {
    "simple": "ollama/dengcao/Qwen3-32B:Q5_K_M",
    "moderate": "anthropic/claude-sonnet-4-5",
    "coding": "openai-codex/gpt-5.2",
    "complex": "anthropic/claude-opus-4-5",
}

VALID_TIERS = set(TIER_MAP.keys())


def extract_json(text: str) -> dict:
    """Extract JSON from model output, handling markdown fences and multiline."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    return json.loads(text)


def normalize_tier(tier: str) -> str:
    """Force a single valid tier even if the model returns multiple."""
    tier = tier.strip().lower()

    if tier in VALID_TIERS:
        return tier

    # If model returned "coding|complex" style, pick the first valid one
    # Priority order: coding > complex > moderate > simple
    priority = ["coding", "complex", "moderate", "simple"]
    for candidate in priority:
        if candidate in tier:
            return candidate

    return "moderate"


def classify(prompt: str) -> dict:
    """Ask local Ollama to classify task complexity."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": TRIAGE_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "think": False,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 150},
            },
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "")

        parsed = extract_json(text)
        if "tier" in parsed:
            parsed["tier"] = normalize_tier(parsed["tier"])
        return parsed

    except requests.exceptions.RequestException as e:
        return {"tier": "moderate", "reason": f"Ollama unavailable ({e})"}
    except json.JSONDecodeError:
        return {"tier": "moderate", "reason": "Parse failed, defaulting"}


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = sys.stdin.read().strip()

    if not prompt:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    result = classify(prompt)
    tier = result.get("tier", "moderate")
    model = TIER_MAP.get(tier, TIER_MAP["moderate"])

    output = {"model": model, "tier": tier, "reason": result.get("reason", "")}
    print(json.dumps(output))


if __name__ == "__main__":
    main()
