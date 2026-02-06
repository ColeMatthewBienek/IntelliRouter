# IntelliRouter

An intelligent model router for [OpenClaw](https://github.com/openclaw/openclaw) that triages incoming messages by complexity using a tiny local LLM, then routes each request to the optimal AI model.

**Save 40-60% on API costs** by handling simple tasks locally and only escalating to expensive models when the task actually needs them.

## How It Works

```
User message
    │
    ▼
┌─────────────┐     ┌──────────────────────────────────┐
│  qwen3:1.7b │────▶│  Tier classification (<500ms)    │
│  (local)    │     │  simple | moderate | coding |     │
└─────────────┘     │  complex                         │
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
         ┌─────────┐   ┌───────────┐    ┌─────────────┐
         │  Local   │   │  Sonnet   │    │ Codex/Opus  │
         │  32B     │   │  (API)    │    │   (API)     │
         │  FREE    │   │  $$$      │    │   $$$$      │
         └─────────┘   └───────────┘    └─────────────┘
```

A small local model (qwen3:1.7b, ~1.4 GB VRAM) classifies each message into one of four tiers. The classifier runs in under 500ms and costs nothing. The actual work then goes to the right model for the job.

## Tier Routing

| Tier | Routed To | Use Case | Cost |
|------|-----------|----------|------|
| **simple** | Local 32B (Ollama) | Greetings, quick facts, one-liners | Free |
| **moderate** | Claude Sonnet 4.5 | Explanations, summaries, short writing | ~$3/M tokens |
| **coding** | Codex / GPT-5.2 | Write, fix, debug, review code | Subscription |
| **complex** | Claude Opus 4.5 | Long-form content, architecture, deep analysis | ~$15/M tokens |

## Requirements

- **Ollama** installed and running at `localhost:11434`
- **Python 3.8+** with `requests` library
- **GPU**: Any GPU that can run the triage model (~1.4 GB VRAM for qwen3:1.7b)
- **Work model** (optional): A capable local model for the simple tier. Default config uses `dengcao/Qwen3-32B:Q5_K_M` (~23 GB VRAM)

## Quick Start

### 1. Install Ollama and pull models

```bash
# Install Ollama (Linux/WSL)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the triage model (required, ~1.4 GB)
ollama pull qwen3:1.7b

# Pull a local work model for the simple tier (optional, ~23 GB)
ollama pull dengcao/Qwen3-32B:Q5_K_M
```

### 2. Install Python dependency

```bash
pip install requests
```

### 3. Copy the skill into OpenClaw

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/IntelliRouter.git

# Copy into your OpenClaw workspace skills directory
cp -r IntelliRouter ~/.openclaw/workspace/skills/intelli-router
```

### 4. Run the test suite

```bash
python3 ~/.openclaw/workspace/skills/intelli-router/scripts/test_classify.py
```

You should see 12/12 correct.

### 5. Update OpenClaw config

Add the local Ollama model to your `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "models": {
        "ollama/dengcao/Qwen3-32B:Q5_K_M": {
          "alias": "local"
        }
      }
    }
  },
  "skills": {
    "entries": {
      "intelli-router": {
        "enabled": true
      }
    }
  }
}
```

### 6. Tell your agent to use the skill

Send this to your OpenClaw agent:

```
Read the file at ~/.openclaw/workspace/skills/intelli-router/SKILL.md and use it as a skill
```

## Customization

### Swap models

Edit `TIER_MAP` in `scripts/classify.py` to point tiers at different models:

```python
TIER_MAP = {
    "simple": "ollama/your-local-model",
    "moderate": "anthropic/claude-sonnet-4-5",
    "coding": "openai-codex/gpt-5.2",
    "complex": "anthropic/claude-opus-4-5",
}
```

### Change the triage model

Any small Ollama model that can output JSON works. Edit `TRIAGE_MODEL`:

```python
TRIAGE_MODEL = "qwen3:1.7b"  # Default, good accuracy/speed balance
# TRIAGE_MODEL = "qwen3:0.6b"  # Faster but less accurate (7/12)
# TRIAGE_MODEL = "qwen3:4b"    # More accurate but slower
```

### Adjust tier definitions

Edit `SYSTEM_PROMPT` in `scripts/classify.py`. The prompt is intentionally minimal because small models perform better with concise instructions.

## Project Structure

```
intelli-router/
├── SKILL.md                  # OpenClaw skill definition
├── scripts/
│   ├── classify.py           # Triage classifier
│   └── test_classify.py      # 12-prompt validation suite
├── config/
│   └── openclaw.example.json # Example OpenClaw config snippet
├── README.md
├── LICENSE
└── .gitignore
```

## How Classification Works

The triage model receives a minimal system prompt with four tier definitions and example JSON responses. Key design decisions from testing:

- **`think: false`** in the Ollama API call disables the model's internal reasoning mode. Without this, small models burn their entire token budget on thinking and return empty responses.
- **`normalize_tier()`** handles cases where the model returns multiple tiers (e.g., `"coding|complex"`) by picking the highest-priority valid one.
- **`extract_json()`** strips markdown code fences that small models often wrap around JSON output.
- **Fallback to moderate** on any failure (Ollama down, parse error, invalid tier) so the router never blocks the user.

## Performance

Tested on RTX 5090 (32 GB VRAM):

| Metric | Value |
|--------|-------|
| Triage latency | ~200-500ms |
| Triage VRAM | ~1.4 GB |
| Accuracy (qwen3:1.7b) | 12/12 test prompts |
| Accuracy (qwen3:0.6b) | 7/12 test prompts |

## License

MIT
