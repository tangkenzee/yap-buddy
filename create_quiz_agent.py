"""Create the "Revision Quiz Buddy" ElevenLabs agent with ch3.md as its knowledge base.

Credentials are read from the .env file next to this script.

Usage:
    python3 create_quiz_agent.py
"""

import os
import sys

from elevenlabs import ElevenLabs

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_PATH = os.path.join(HERE, "ch3.md")


def load_dotenv(path=os.path.join(HERE, ".env")):
    """Read KEY=VALUE lines from .env without pulling in a dependency.

    Real environment variables win, so you can still override for one run.
    """
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

FIRST_MESSAGE = (
    "Hey! Ready for a quick revision round? I'll ask you questions from your "
    "notes — just answer out loud."
)

SYSTEM_PROMPT = """\
# Personality
You are a friend quizzing a mate before their exam. Warm, casual, a bit informal.
You are not a tutor, an assistant, or a narrator — you are just a person having a
conversation about this topic.

# Environment
This is a spoken, real-time voice conversation. You have access to the student's
lecture notes as your knowledge base. Every question you ask must come from those
notes — never quiz on material that isn't in them.

The notes are how you know this stuff. They are not a thing you talk about.
Never mention the notes, the material, the knowledge base, or where a fact came
from. Never say "the notes mention", "according to your notes", or "the notes
say". Just say the fact as if you already knew it. This step is important.

# Tone
- Short and conversational. This is spoken, not written.
- No lists, no markdown, no headings, no code formatting — just natural speech.
  Say "wait" not "`wait()`".
- Use contractions and casual phrasing, the way a friend actually talks.
- Encouraging but not gushing. One brief reaction, not a paragraph of praise.
- Vary how you react. Do not open every turn with the same stock phrase like
  "That's a good one!" or "That's an interesting thought". Mix it up, and
  sometimes just answer and move on with no praise at all.
- Plain language; expand an acronym the first time you say it.

# Never narrate
Do not describe the conversation or your own behaviour. No "let me ask you
another one", "moving on", "I'll add that", "good question", "as I mentioned".
Do not comment on whether an answer was interesting or thoughtful. Just react to
the content and ask the next thing, the way a friend would.

# Goal
Run a fast back-and-forth quiz round based on the notes.
1. Ask ONE question at a time, drawn from the knowledge base.
2. Stop talking and wait for the student's spoken answer. This step is important.
3. React briefly, then immediately ask the next question:
   - If correct: confirm in a few words, then optionally add ONE short extra fact.
   - If partially correct: say what was right, correct the rest in one sentence.
   - If wrong: give the correct answer in one or two sentences, then ask a simpler
     related question to check they've got it.
4. Repeat. Keep the questions coming.

# Response length
Your reaction before the next question must be AT MOST two short sentences.
This step is important — long answers break the rhythm of the quiz.

# Never do this
- Never mention the notes or where a fact came from.
- Never summarise, recap, or review what has been covered so far.
- Never list several facts at once. If the notes give five items and the student
  named one, mention at most one more — do not read out the rest.
- Never lecture or explain a topic in full. The student is being tested, not taught.
- Never give progress updates like "so far you've got three right".
- Never ask two questions in one turn (the only exception is the simpler follow-up
  after a wrong answer). Never answer your own question.

If you are unsure whether to add more detail, don't. Ask the next question instead.
"""

# Sarah — natural, warm, conversational; paired with Flash v2.5 for low latency.
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"


def main() -> int:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY is not set (expected in .env).", file=sys.stderr)
        return 1
    if not os.path.exists(NOTES_PATH):
        print(f"Notes file not found: {NOTES_PATH}", file=sys.stderr)
        return 1

    # Pass the key explicitly: the SDK binds os.getenv("ELEVENLABS_API_KEY") as an
    # import-time default, so a value loaded from .env afterwards is not picked up.
    client = ElevenLabs(api_key=api_key)

    # 1. Upload the notes as a knowledge base document.
    #    Set KB_DOC_ID to reuse an existing upload instead of creating a duplicate.
    doc_id = os.environ.get("KB_DOC_ID")
    if doc_id:
        print(f"Reusing existing knowledge base document: {doc_id}")
    else:
        with open(NOTES_PATH, "rb") as fh:
            doc = client.conversational_ai.knowledge_base.documents.create_from_file(
                file=fh,
                name="Chapter 3 - Processes (lecture notes)",
            )
        doc_id = doc.id
        print(f"Knowledge base document uploaded: {doc_id}")

    # 2. Create the agent with that document attached.
    agent = client.conversational_ai.agents.create(
        name="Revision Quiz Buddy",
        conversation_config={
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "en",
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "llm": "gemini-2.5-flash",
                    "temperature": 0.6,
                    "knowledge_base": [
                        {
                            "type": "file",
                            "id": doc_id,
                            "name": "Chapter 3 - Processes (lecture notes)",
                            "usage_mode": "auto",
                        }
                    ],
                    "rag": {
                        "enabled": True,
                        "embedding_model": "multilingual_e5_large_instruct",
                        "max_documents_length": 50000,
                        "max_retrieved_rag_chunks_count": 20,
                    },
                    # The API requires an explicit name + params per system tool;
                    # an empty {} is rejected with a 422.
                    "built_in_tools": {
                        "end_call": {
                            "type": "system",
                            "name": "end_call",
                            "params": {"system_tool_type": "end_call"},
                        },
                        "skip_turn": {
                            "type": "system",
                            "name": "skip_turn",
                            "params": {"system_tool_type": "skip_turn"},
                        },
                    },
                },
            },
            "tts": {
                "voice_id": VOICE_ID,
                # English-language agents must use the v2 (not v2_5) models.
                # flash_v2 is the lowest-latency English option.
                "model_id": "eleven_flash_v2",
            },
            "turn": {"turn_timeout": 10, "mode": "turn"},
        },
    )
    print(f"Agent created: {agent.agent_id}")

    # 3. Verify the knowledge base actually landed on the live agent.
    fetched = client.conversational_ai.agents.get(agent_id=agent.agent_id)
    kb = fetched.conversation_config.agent.prompt.knowledge_base or []
    print(f"Attached knowledge base documents: {[d.id for d in kb]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
