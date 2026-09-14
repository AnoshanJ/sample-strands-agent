"""
Simple terminal chat client for a Strands Agent backed by Amazon Bedrock.

Run:
    python chat.py

Configuration is read from .env (see .env for AWS region / model id / creds).
"""

import os
import sys

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

from strands import Agent
from strands.models import BedrockModel


def build_agent() -> Agent:
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

    return Agent(model=model, system_prompt=system_prompt)


def main() -> None:
    try:
        agent = build_agent()
    except Exception as exc:  # noqa: BLE001 - surface setup errors clearly
        print(f"Failed to initialize the agent: {exc}", file=sys.stderr)
        print(
            "Check that .env has a valid AWS_REGION / BEDROCK_MODEL_ID, that "
            "you have Bedrock model access enabled for that model in that "
            "region, and that AWS credentials are configured "
            "(aws configure / aws sso login).",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Strands + Bedrock chat agent. Type 'exit' or 'quit' to leave, Ctrl+C to force-quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        print("Agent: ", end="", flush=True)
        try:
            # The agent's default callback handler streams the response text
            # to stdout as it's generated, so we don't need to print it again.
            agent(user_input)
        except Exception as exc:  # noqa: BLE001 - keep the chat loop alive
            print(f"\n[error] {exc}", file=sys.stderr)
        print()


if __name__ == "__main__":
    main()
