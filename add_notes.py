"""Add a file to Yap Buddy's knowledge base and attach it to the agent.

Uploads the file, waits for it to be indexed, and adds it alongside whatever
notes are already attached — existing subjects are kept.

Usage:
    python3 add_notes.py path/to/notes.pdf
    python3 add_notes.py notes.md "Biology — Ch. 5, Enzymes"
"""

import os
import sys
import time

from elevenlabs import ElevenLabs

from create_quiz_agent import load_dotenv

EMBEDDING_MODEL = "multilingual_e5_large_instruct"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"No such file: {path}", file=sys.stderr)
        return 1
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)

    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    agent_id = os.environ.get("AGENT_ID")
    if not (api_key and agent_id):
        print("ELEVENLABS_API_KEY and AGENT_ID must be in .env", file=sys.stderr)
        return 1

    client = ElevenLabs(api_key=api_key)
    kb = client.conversational_ai.knowledge_base

    # 1. Upload
    with open(path, "rb") as fh:
        doc = kb.documents.create_from_file(file=fh, name=name)
    print(f"Uploaded '{name}' -> {doc.id}")

    # 2. Index it. This does NOT happen automatically, and until it finishes
    #    the agent cannot retrieve anything from the document.
    kb.get_or_create_rag_indexes(
        items=[{"document_id": doc.id, "model": EMBEDDING_MODEL, "create_if_missing": True}]
    )
    for _ in range(60):
        state = kb.get_or_create_rag_indexes(
            items=[{"document_id": doc.id, "model": EMBEDDING_MODEL, "create_if_missing": False}]
        )[doc.id].data
        print(f"  indexing: {state.status} {state.progress_percentage:.0f}%")
        if state.status in ("succeeded", "failed"):
            break
        time.sleep(5)
    if state.status != "succeeded":
        print(f"Indexing did not finish: {state.status}", file=sys.stderr)
        return 1

    # 3. Attach, keeping the subjects already loaded
    agent = client.conversational_ai.agents.get(agent_id=agent_id)
    existing = agent.conversation_config.agent.prompt.knowledge_base or []
    entries = [
        {"type": d.type, "id": d.id, "name": d.name, "usage_mode": d.usage_mode}
        for d in existing
    ]
    if any(e["id"] == doc.id for e in entries):
        print("Already attached.")
        return 0
    entries.append({"type": "file", "id": doc.id, "name": name, "usage_mode": "auto"})

    client.conversational_ai.agents.update(
        agent_id=agent_id,
        conversation_config={"agent": {"prompt": {"knowledge_base": entries}}},
    )

    live = client.conversational_ai.agents.get(agent_id=agent_id)
    attached = live.conversation_config.agent.prompt.knowledge_base or []
    print("\nNow loaded:")
    for d in attached:
        print(f"  · {d.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
