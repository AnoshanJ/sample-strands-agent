"""
Simple terminal chat client for a Strands Agent backed by Amazon Bedrock.

Run:
    python chat.py

Configuration is read from .env (see .env for AWS region / model id / creds).
"""

import sys

from agent import build_agent


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
