# LLM / Ollama Configuration

The AI/ML path for prop rationales can use **Ollama** (local or remote) for LLM-generated explanations. This document describes how to point the backend at an Ollama instance running in a container on your VPS.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OLLAMA_HOST` | Base URL of the Ollama API (remote VPS or local) | `http://your-vps-ip:11434` |
| `LLM_OLLAMA_BASE_URL` | Alternative to `OLLAMA_HOST` (same behavior) | `http://10.0.0.5:11434` |
| `OLLAMA_MODEL` | Model name to use (must be pulled on the Ollama server) | `llama3.2`, `llama3.1`, `mistral` |
| `OLLAMA_TIMEOUT` | Request timeout in seconds (default: 90; increase for slow VPS) | `120` |

## Using Ollama on a VPS (llm-runtime container)

1. **Run Ollama on the VPS** (e.g. in a container):
   - Expose the default Ollama port `11434` so the NBA Stat Spot backend can reach it.
   - Ensure the model you want is pulled on that instance (e.g. `ollama pull llama3.2`).

2. **Configure the backend** (on the machine running the NBA Stat Spot API):
   - Set `OLLAMA_HOST` to the full URL of your Ollama API, e.g.:
     - `OLLAMA_HOST=http://your-vps-ip:11434`
     - or `OLLAMA_HOST=http://llm-runtime:11434` if the container is on the same Docker network and the service name is `llm-runtime`.
   - Optionally set `OLLAMA_MODEL` to the model name (default is `llama3.2`).
   - Optionally set `OLLAMA_TIMEOUT` if requests are slow (e.g. `120`).

3. **Enable AI in the app** so the rationale generator is used:
   - AI features must be enabled (e.g. via Admin dashboard or `POST /api/v1/admin/settings/ai-enabled` with `{"enabled": true}`).

## Service order

The rationale generator tries LLM services in order:

1. **OpenAI** (if `OPENAI_API_KEY` is set)
2. **Ollama** (local or remote via `OLLAMA_HOST` / `LLM_OLLAMA_BASE_URL`)
3. **Rule-based fallback** if no LLM is available

So when OpenAI is not configured, Ollama on your VPS will be used for rationales when AI is enabled.

## Example .env (VPS Ollama)

```bash
# Ollama on VPS (llm-runtime container)
OLLAMA_HOST=http://your-vps-ip:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=90
```

## Health check

To verify the backend can reach Ollama, check the LLM health endpoint (if exposed) or trigger a prop suggestion with AI enabled and confirm a rationale is returned with an LLM source.
