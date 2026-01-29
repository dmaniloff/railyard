## Setup

Create the virtual environment.

```bash
uv venv
```

Install dependencies.

```bash
uv sync
```

## Probe the unguardrailed model

Ensure `.env` contains `OPENAICOMPATIBLE_API_KEY=<your-api-key>`, then run:

```bash
uv run dotenv run garak \
  --target_type openai.OpenAICompatible \
  --target_name Mistral-Small-24B-W8A8 \
  --generator_options '{"openai": {"OpenAICompatible": {"uri": "<your-api-base-url>", "model": "Mistral-Small-24B-W8A8"}}}' \
  --generations 1 \
  --probes promptinject.HijackKillHumans 
```

## Start and test the guardrail server

Start the guardrail server.

```bash
uv run python guardrail_server.py
```

Test the guardrail server (this should return something like `{"label":"SAFE","score":0.9999971389770508}`).

```bash
curl -X POST "http://localhost:8000/v1/classify" -H "Content-Type: application/json" -d '{"text": "What is  the weather today?"}'
```

## Probe the guardrailed model

```bash
uv run dotenv run garak \
  --target_type guardrails \
  --target_name nemo-config \
  --generations 1 \
  --probes promptinject.HijackKillHumans
```

