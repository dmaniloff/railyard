# 🛤️ Railyard
**Welcome to Railyard** - a simple guardrails playground.
        
Railyard helps you:
- **Configure & test** [Nemo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) for your AI models
- **Run security probes** using [Garak](https://github.com/NVIDIA/Garak) to identify vulnerabilities  
- **Benchmark performance** via [GuideLLM](https://github.com/vllm-project/GuideLLM) to measure system throughput
- **Compare results** between protected and unprotected model interactions

## Setup

Create the virtual environment.

```bash
uv venv
```

Install dependencies.

```bash
uv sync
```

## Start Railyard locally

```bash
uv run dotenv run python railyard_server.py # or uv run dotenv run gradio railyard_server.py
```

## Kubernetes Deployment

Deploy Railyard to a Kubernetes cluster.

### Prerequisites

- `kubectl` configured to access your cluster
- Railyard container image: `quay.io/diegosquayorg/railyard:latest` (see Dockerfile for details)

### Setup Environment Variables

Create a `.env` file with the following environment variables:

```bash
# LittleLM configuration (for main model)
LITELLM_API_KEY=your-api-key
LITELLM_API_URL=your-api-base-url

# OpenAI Compatible API key (for Garak probes)
OPENAICOMPATIBLE_API_KEY=$LITELLM_API_KEY

# GuideLLM configuration (for performance benchmarks)
GUIDELLM_BACKEND_KWARGS={"api_key":"${LITELLM_API_KEY}"}

# Railyard authentication credentials
RAILYARD_USER=your-username
RAILYARD_PASS=your-password
```
### Deploy to Kubernetes

1. Create a secret from your environment file:

```bash
kubectl create secret generic railyard-env --from-env-file=.env
```

2. Apply the deployment manifest:

```bash
kubectl apply -f k8s-deployment.yaml
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
