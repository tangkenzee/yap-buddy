"""Check the live agent + knowledge base are healthy. Reads .env. Creates nothing.

Usage:
    python3 verify_agent.py
"""

import os
import sys

from elevenlabs import ElevenLabs

from create_quiz_agent import load_dotenv


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("AGENT_ID")
    doc_id = os.environ.get("KB_DOC_ID")
    if not (api_key and agent_id and doc_id):
        print("ELEVENLABS_API_KEY, AGENT_ID and KB_DOC_ID must be in .env", file=sys.stderr)
        return 1

    # Pass the key explicitly: the SDK binds os.getenv("ELEVENLABS_API_KEY") as an
    # import-time default, so a value loaded from .env afterwards is not picked up.
    client = ElevenLabs(api_key=api_key)

    agent = client.conversational_ai.agents.get(agent_id=agent_id)
    prompt = agent.conversation_config.agent.prompt
    kb_ids = [d.id for d in (prompt.knowledge_base or [])]
    print(f"agent:        {agent.name} ({agent_id})")
    print(f"llm:          {prompt.llm}")
    print(f"voice:        {agent.conversation_config.tts.voice_id}")
    print(f"attached kb:  {kb_ids}")

    index = client.conversational_ai.knowledge_base.get_or_create_rag_indexes(
        items=[
            {
                "document_id": doc_id,
                "model": "multilingual_e5_large_instruct",
                "create_if_missing": False,
            }
        ]
    )[doc_id]
    print(f"rag index:    {index.data.status} ({index.data.progress_percentage}%)")

    ok = doc_id in kb_ids and index.data.status == "succeeded"
    print("OK" if ok else "NOT READY")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
