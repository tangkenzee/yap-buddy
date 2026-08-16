"""Push the current SYSTEM_PROMPT in create_quiz_agent.py to the live agent.

Updates in place — the agent ID and knowledge base are untouched.

Usage:
    python3 update_agent.py
"""

import os
import sys

from elevenlabs import ElevenLabs

from create_quiz_agent import SYSTEM_PROMPT, load_dotenv


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("AGENT_ID")
    if not (api_key and agent_id):
        print("ELEVENLABS_API_KEY and AGENT_ID must be in .env", file=sys.stderr)
        return 1

    client = ElevenLabs(api_key=api_key)

    # Partial update: only the prompt text changes. Everything else (knowledge
    # base, RAG config, voice, tools) is left exactly as it is.
    client.conversational_ai.agents.update(
        agent_id=agent_id,
        conversation_config={"agent": {"prompt": {"prompt": SYSTEM_PROMPT}}},
    )

    agent = client.conversational_ai.agents.get(agent_id=agent_id)
    prompt = agent.conversation_config.agent.prompt
    live = prompt.prompt
    kb_ids = [d.id for d in (prompt.knowledge_base or [])]
    print(f"prompt updated: {live == SYSTEM_PROMPT}")
    print(f"knowledge base still attached: {kb_ids}")
    return 0 if live == SYSTEM_PROMPT and kb_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
