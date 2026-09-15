# Sample Strands Agent (Amazon Bedrock)

A minimal chat agent built with the [Strands Agents SDK](https://strandsagents.com/), backed by an Anthropic Claude model on Amazon Bedrock. It runs either as a terminal REPL or as an HTTP service.

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Enable Bedrock model access.** In the AWS console, go to Bedrock → Model access, and request access to the Claude model(s) you want to use, in the region you plan to call from.

3. **Authenticate to Bedrock.** There are two options — pick one:

   - **Option A — Bedrock API key (bearer token).** The simplest path, no IAM setup required. In the AWS console go to **Amazon Bedrock → API keys → Generate API key** (short-term keys expire in up to 12h; long-term keys can be scoped with an attached IAM policy). Paste the key into `.env` as `BEDROCK_API_KEY`. This is what you already have if someone gave you "a Bedrock access token."
   - **Option B — standard IAM credentials (SigV4).** Use whatever your org normally uses:

     ```bash
     aws configure          # long-lived access key/secret
     aws sso login          # IAM Identity Center / SSO
     ```

     Or run from an environment that already has an IAM role attached (EC2, ECS, Lambda, CloudShell). Leave `BEDROCK_API_KEY` blank in this case.

4. **Edit `.env`** to set your region, model, and chosen auth method:

   ```ini
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

   # Option A: paste your Bedrock API key here, leave Option B fields blank
   BEDROCK_API_KEY=

   # Option B: leave blank to use aws configure/sso/instance-role instead
   AWS_PROFILE=
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   AWS_SESSION_TOKEN=
   ```

   - If `BEDROCK_API_KEY` is set, it takes priority and the IAM fields are ignored.
   - Otherwise, leave `AWS_PROFILE` / `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` blank to use whatever credentials `aws configure`/`aws sso login` already set up. Only fill in `AWS_PROFILE` if you need a specific named profile.
   - To see the current list of Claude model IDs available on Bedrock in your region:

     ```bash
     aws bedrock list-inference-profiles --region us-east-1 \
       --query "inferenceProfileSummaries[?contains(inferenceProfileId,'claude')].inferenceProfileId"
     ```

     Most current Claude models on Bedrock require a **cross-region inference profile** ID (the `us.anthropic....` form) rather than the bare `anthropic....` model ID.

## Run

### As an HTTP service (for deployment)

```bash
python main.py
```

Serves `POST /chat` on `0.0.0.0:8000`:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "session_123", "message": "What is the capital of France?"}'
```

```json
{"response": "The capital of France is Paris."}
```

Reusing a `session_id` continues that conversation. See [`openapi.yaml`](openapi.yaml) for the full contract.

### As a terminal chat (for local use)

```bash
python chat.py
```

```
Strands + Bedrock chat agent. Type 'exit' or 'quit' to leave, Ctrl+C to force-quit.

You: What can you help me with?
Agent: ...
```

Type `exit`, `quit`, or press Ctrl+C to leave the chat.

Note that `chat.py` reads from stdin, so it exits immediately in a container (where stdin is closed). Deploy `main.py` instead.

## How it works

- [`agent.py`](agent.py) loads config from `.env` and builds a Strands `BedrockModel` pointed at your chosen Claude model/region, wrapped in a Strands `Agent`. Both entry points use it.
- [`main.py`](main.py) / [`app.py`](app.py) serve that agent over `POST /chat` with FastAPI. Each `session_id` gets its own `Agent`, so history is per session; the registry is LRU-bounded by `MAX_SESSIONS` (default 1000).
- [`chat.py`](chat.py) runs the same agent as a read-eval-print loop against stdin.
- [`telemetry.py`](telemetry.py) points Strands' built-in agent tracing at AMP, using `AMP_OTEL_ENDPOINT` and `AMP_AGENT_API_KEY`. Disable AMP's auto-instrumentation on the component, or both will export the same spans.
- The `Agent` object keeps conversation history internally across turns, so follow-up questions have context.
- Bedrock credentials are resolved through the normal boto3 credential chain (env vars → shared config/profile → SSO → instance role), so this reuses whatever AWS auth you already have set up.

## Tracing

Strands emits OpenTelemetry GenAI spans on its own. [`telemetry.py`](telemetry.py) installs a global tracer provider that ships them to AMP over OTLP/HTTP, so no auto-instrumentation agent is needed:

- endpoint: `$AMP_OTEL_ENDPOINT/v1/traces`
- headers: `x-amp-api-key: $AMP_AGENT_API_KEY`

Both env vars are injected by the platform. If either is unset (local runs), tracing is skipped and the agent still works.

Leave Strands' `use_latest_genai_conventions` at its default — enabling it swaps `gen_ai.system` for `gen_ai.provider.name`, which AMP's span contract does not read.

## Troubleshooting

- `AccessDeniedException` / `ValidationException` mentioning model access: you haven't enabled that model in Bedrock's Model access page for that region.
- `ProfileNotFound`: an `AWS_PROFILE` value is set but doesn't exist — clear it in `.env` or run `aws configure --profile <name>`.
- `ExpiredTokenException`: re-run `aws sso login` (or refresh your temporary credentials).
- `401`/`UnrecognizedClientException` with `BEDROCK_API_KEY` set: the key has expired (short-term keys last up to 12h) or doesn't have access to the model/region you're calling — generate a new one or use a long-term key scoped with the right IAM policy.
