# Rationale and LLM

How prop rationales and AI-generated text work, which models are used, and how to configure them.

---

## How rationales work

**Rationales** are short, human-readable explanations for a prop suggestion (e.g. “Over 24.5 PTS”) or for game predictions and over/under recommendations.

1. **LLM chain** – The app tries each configured LLM in order until one succeeds.
2. **Rule-based fallback** – If no LLM is available or all fail, a **rule-based rationale** is built from:
   - Player name, trend (up/down/flat), hit rate vs line, rest days, home/away
   - ESPN context when present: injury status, conference rank, news sentiment

So you always get a rationale; LLM improves quality when enabled.

---

## Where rationales are used

| Use | Description |
|-----|-------------|
| **Prop suggestions** | When you request a suggestion for a player/stat/line, the backend returns a recommendation plus a rationale (LLM or rule-based). |
| **Game predictions** | One-sentence summary for “why X might win” and a short paragraph for the game detail page. |
| **Over/Under** | Live game total recommendation with a short explanation. |

AI must be **enabled** (Admin → settings or `POST /api/v1/admin/settings/ai-enabled` with `{"enabled": true}`) for the LLM chain to be used; otherwise only the rule-based fallback runs.

---

## LLM service order and models

The **RationaleGenerator** tries services in this order:

| Order | Service | When used | Model / config |
|-------|---------|-----------|----------------|
| 1 | **OpenAI** | If `OPENAI_API_KEY` is set | Default: **gpt-4o-mini** (cost-efficient). |
| 2 | **Ollama** | If OpenAI not configured or fails | Model from `OLLAMA_MODEL` (default: **llama3.2**). Can be local or remote (e.g. VPS). |
| 3 | **Rule-based** | If no LLM is available or all fail | No model; built from stats and context only. |

So: **OpenAI first** (if key set), then **Ollama** (local or `OLLAMA_HOST`), then **rule-based**.

---

## What the LLM receives (prop rationale)

The prompt includes:

- **Player**, **prop** (e.g. PTS over 24.5), **confidence** (0–100), optional **ML confidence**
- **Stats:** hit rate (over/under), recent form (trend + avg), season hit rate
- **Context:** rest days, home/away, opponent defensive rank
- **ESPN context** (when available): injury status, conference rank, news sentiment

The model is asked for a **concise rationale** (no extra prefix). Response is trimmed and length-capped.

---

## Configuration

### OpenAI (optional)

- **Env:** `OPENAI_API_KEY`
- **Model:** `gpt-4o-mini` (default in code; can be overridden if the app supports a model setting).

### Ollama (local or remote)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` or `LLM_OLLAMA_BASE_URL` | Ollama API base URL (e.g. `http://vps-ip:11434`) | localhost |
| `OLLAMA_MODEL` | Model name (must be pulled on the Ollama server) | `llama3.2` |
| `OLLAMA_TIMEOUT` | Request timeout (seconds) | `90` |

Example for a VPS:

```bash
OLLAMA_HOST=http://your-vps-ip:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=90
```

Ensure the model is pulled on the server (e.g. `ollama pull llama3.2`).

---

## Health and behavior

- **Health:** LLM health is reported via the rationale generator’s health check (lists each service and availability).
- **Errors:** If a service fails (timeout, API error), the next service in the chain is tried; if all fail, the rule-based rationale is returned.
