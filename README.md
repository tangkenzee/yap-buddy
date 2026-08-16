# Yap Buddy

A voice study partner. It reads your lecture notes, asks you questions about them,
and you answer out loud. Built on the ElevenLabs Agents platform.

- **Agent ID:** `agent_1701m04xfzy0fssvkw59nq01s471`
- **Voice:** Sarah (`EXAVITQu4vr4xnSDxMaL`) on `eleven_flash_v2`
- **LLM:** `gemini-2.5-flash`
- **Currently loaded notes:** Operating Systems — Ch. 3, Processes

---

## Quick start

```bash
cd ~/Documents/Agents/Voice-agent
python3 -m http.server 8000
```

Open <http://localhost:8000/demo.html>, click the widget in the bottom-right,
and allow the microphone.

> **Use `localhost`, not the file itself.** Opening `demo.html` by double-clicking
> gives you a `file://` URL, and browsers only grant microphone access on a secure
> origin. `http://localhost` counts; `file://` does not. The widget will simply
> fail to connect with no obvious error.

Stop the server with `Ctrl-C`, or if it is running in the background:

```bash
pkill -f "http.server 8000"
```

---

## First-time setup

Only needed on a fresh machine.

```bash
python3 -m venv .venv
.venv/bin/pip install elevenlabs
cp .env.example .env      # then paste your API key into .env
```

All the scripts below assume the venv: run them as `.venv/bin/python <script>`.

### Getting an API key

1. Sign in at <https://elevenlabs.io> → profile menu → **API Keys** → **Create key**
2. Under **Endpoints**, set **ElevenAgents → Write**. Leave everything else on
   **No Access** — Write includes Read, and nothing else is needed.
3. Leave **Auto-disable if leaked** on.
4. Paste the key into `.env` as `ELEVENLABS_API_KEY=sk_...`

Text to Speech, Voices, and Models all stay on **No Access**. That looks wrong but
is correct: speech is synthesised server-side inside the agent session, so your key
never calls those endpoints.

---

## Adding a new subject to the knowledge base

### Option A — the dashboard (handles PDFs, Word docs, web pages)

1. <https://elevenlabs.io> → **Agents** in the sidebar → **Knowledge base**
2. **Add document** → upload your file, or paste a URL
3. **Agents** → **Revision Quiz Buddy** → scroll to **Knowledge base**
4. **Add document** → select the one you uploaded
5. Confirm **RAG / retrieval** is enabled for it, then **Save**

> **Watch step 5.** A document can be uploaded and attached but still be
> **unindexed**, in which case the agent lists it and retrieves nothing from it.
> If the dashboard shows an indexing status, wait for it to complete before testing.

### Option B — the script (does all of the above, including the indexing wait)

```bash
.venv/bin/python add_notes.py ~/Downloads/ch4.pdf "Operating Systems — Ch. 4, Threads"
```

The second argument is the label the agent sees, so make it descriptive — it is how
the agent tells subjects apart once several are loaded. It defaults to the filename.

The script uploads, triggers indexing, polls until `succeeded`, then attaches the
document *alongside* whatever is already loaded. Existing subjects are preserved.

### Converting slides to notes first

The agent reads text, so PowerPoint decks need converting. `ch3.md` was produced
from `ch3.pptx` this way — slide titles become headings and bullets are preserved.
Ask Claude to convert a new deck, or upload the PDF export directly.

---

## Changing how the agent behaves

The system prompt lives in `create_quiz_agent.py` as `SYSTEM_PROMPT`. It is the
single source of truth.

```bash
# 1. edit SYSTEM_PROMPT in create_quiz_agent.py
# 2. push it to the live agent
.venv/bin/python update_agent.py
```

This updates in place — same agent ID, knowledge base untouched. Refresh the
browser tab; the next session picks up the new prompt with no redeploy.

The prompt is tuned to keep the agent conversational rather than lecture-like. The
rules that matter most, if you edit it:

- **Never mention "the notes".** The notes are how it knows things, not something
  it talks about. Without this it says "according to your notes…" every turn.
- **At most two short sentences** before the next question.
- **One extra fact maximum.** Otherwise it recites every remaining item in a list,
  which is what makes it feel like a summary generator instead of a friend.
- **No narrating** — no "let me ask you another", no "good question".

### Testing a prompt change without talking

```bash
.venv/bin/python -c "
import os
from create_quiz_agent import load_dotenv; load_dotenv()
from elevenlabs import ElevenLabs
c = ElevenLabs(api_key=os.environ['ELEVENLABS_API_KEY'])
r = c.conversational_ai.agents.simulate_conversation(
    agent_id=os.environ['AGENT_ID'],
    simulation_specification={'simulated_user_config': {
        'first_message': 'ok go',
        'prompt': {'prompt': 'You are a student. Answer briefly. Get some right, some wrong.'}}},
)
for m in r.simulated_conversation:
    print(f'[{m.role}] {m.message}')
"
```

Runs a full conversation against a simulated student in about a minute. Good for
checking tone and length before a live demo.

---

## Health check

```bash
.venv/bin/python verify_agent.py
```

```
agent:        Revision Quiz Buddy (agent_1701m04xfzy0fssvkw59nq01s471)
llm:          gemini-2.5-flash
voice:        EXAVITQu4vr4xnSDxMaL
attached kb:  ['dW7S95tqavC2JEb0P45R']
rag index:    succeeded (100.0%)
OK
```

Exits non-zero if the knowledge base is detached or unindexed. Worth running before
any demo.

---

## Embedding the widget elsewhere

```html
<elevenlabs-convai agent-id="agent_1701m04xfzy0fssvkw59nq01s471"></elevenlabs-convai>
<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
```

No API key involved — the widget authenticates by agent ID, which is why it is safe
on a public page. It must be served over HTTPS (or localhost) for the mic to work.

Widget colours and button copy are configured **on the agent**
(`platform_settings.widget`), not as HTML attributes, so they follow the widget
wherever it is embedded. Attributes like `action-text` look plausible but do
nothing.

---

## Files

| File | What it does |
|---|---|
| `demo.html` | The Yap Buddy page. Self-contained apart from Google Fonts and the widget script. |
| `create_quiz_agent.py` | Creates the agent from scratch. Holds `SYSTEM_PROMPT`. |
| `update_agent.py` | Pushes prompt edits to the live agent. |
| `add_notes.py` | Uploads, indexes, and attaches a new subject. |
| `verify_agent.py` | Health check. Creates nothing. |
| `ch3.md` | Chapter 3 notes, converted from `ch3.pptx`. Not committed — course material. |
| `.env` | API key and IDs. Never commit — `.gitignore` covers it. |

---

## Gotchas

Things that cost time once already:

- **The SDK ignores `.env`.** `ElevenLabs()` binds `os.getenv("ELEVENLABS_API_KEY")`
  as an import-time default argument, so a key loaded from `.env` afterwards is
  never picked up and you get a 401 that looks like a bad key. Always pass
  `ElevenLabs(api_key=...)` explicitly.
- **RAG indexing is not automatic.** Uploading and attaching a document is not
  enough; it must be indexed separately. `add_notes.py` handles this.
- **English agents need v2 TTS models.** `eleven_flash_v2_5` is rejected with
  "English Agents must use turbo or flash v2".
- **`built_in_tools` need full definitions.** `{"end_call": {}}` returns a 422; each
  tool needs an explicit `name` and `params`.
- **Valid embedding models** are `e5_mistral_7b_instruct` and
  `multilingual_e5_large_instruct`. Nothing else.
- **The widget has legacy config fields that silently do nothing.** `bg_color`,
  `btn_color`, `action_text` and `start_call_text` are accepted by the API, stored,
  and served back to you — but the current widget ignores them. The fields it
  actually reads are `text_contents` (labels: `main_label`, `start_call`,
  `end_call`, `listening_status`, …) and `styles` (semantic tokens: `base`,
  `base_border`, `accent`, `accent_hover`, `button_radius`, …).
- **`action-text` and friends are not HTML attributes.** They look like they should
  work on `<elevenlabs-convai>`. They don't. Widget copy is agent-side config.
- **The agent is currently public** (`enable_auth=False`, empty allowlist). Anyone
  with the agent ID can talk to it on your credits. Fine for a demo; before putting
  it anywhere public, add your domain to the allowlist and enable
  `require_origin_header`, or switch on auth and mint signed URLs from a backend.
