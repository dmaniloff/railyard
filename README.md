# 🛤️ Railyard

## Setup

Create the virtual environment.

```bash
uv venv
```

Install dependencies.

```bash
uv sync
```

## Start Railyard

```bash
uv run dotenv run python railyard_server.py # or uv run dotenv run gradio railyard_server.py
```

## Test the Railyard commands manually

### Probe the unguardrailed model

Ensure `.env` contains `OPENAICOMPATIBLE_API_KEY=<your-api-key>`, then run:

```bash
uv run dotenv run garak \
  --config garak-config/config.yaml \
  --target_type openai.OpenAICompatible \
  --target_name Mistral-Small-24B-W8A8 \
  --generator_options '{"openai": {"OpenAICompatible": {"uri": "<your-api-base-url>", "model": "Mistral-Small-24B-W8A8"}}}' \
  --probes promptinject.HijackKillHumans 
```

### Start and test the guardrail server

Start the guardrail server.

```bash
uv run python guardrail_server.py
```

Test the guardrail server (this should return something like `{"label":"SAFE","score":0.9999971389770508}`).

```bash
curl -X POST "http://localhost:8000/v1/classify" -H "Content-Type: application/json" -d '{"text": "How are you doing today?"}'
```

### Probe the guardrailed model

```bash
uv run dotenv run garak \
  --config garak-config/config.yaml \
  --target_type guardrails \
  --target_name nemo-config \
  --probes promptinject.HijackKillHumans
```

