"""Agent construction shared by the CLI (chat.py) and the HTTP service (app.py)."""

import os

from dotenv import load_dotenv

load_dotenv()

# python-dotenv sets blank .env values (e.g. `AWS_PROFILE=`) as empty strings
# in the environment. boto3 treats an empty AWS_PROFILE / access-key value as
# an explicit (invalid) override rather than "unset", so strip blanks here to
# let the normal AWS credential chain (SSO, instance role, etc.) take over.
for _var in (
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
):
    if not os.environ.get(_var):
        os.environ.pop(_var, None)

import otel_compat
from strands import Agent
from strands.models import BedrockModel

otel_compat.apply()


def build_agent(*, stream_to_stdout: bool = True) -> Agent:
    region = os.environ.get("AWS_REGION", "us-east-1")
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    system_prompt = os.environ.get(
        "AGENT_SYSTEM_PROMPT",
        "You are a friendly, concise assistant chatting with a user in a terminal.",
    )

    api_key = os.environ.get("BEDROCK_API_KEY")

    # Two mutually exclusive auth paths:
    #  - api_key set: use Bedrock's bearer-token auth (no IAM creds needed).
    #  - otherwise: fall back to the standard boto3 credential chain (env
    #    vars, AWS_PROFILE, SSO, instance role, etc.) set up via
    #    `aws configure` / `aws sso login`.
    model = BedrockModel(
        model_id=model_id,
        region_name=region,
        temperature=0.7,
        **({"api_key": api_key} if api_key else {}),
    )

    # Strands' default callback handler streams tokens to stdout; the service must not.
    return Agent(
        model=model,
        system_prompt=system_prompt,
        **({} if stream_to_stdout else {"callback_handler": None}),
    )
