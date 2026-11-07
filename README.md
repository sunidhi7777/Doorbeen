# Katha-Lens

A small human-in-the-loop review desk for Hindi story localization. Paste a script, compare a plain translation route with a glossary-guided LLM route, and review only the lines that look risky.

## Run it

1. Install Python 3.10 or newer.
2. `py -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, then set credentials and service URLs if you want live translation.
5. `streamlit run app.py`

For the n8n bridge, open a second terminal and run `uvicorn api:app --host 0.0.0.0 --port 8000`. Set `KATHA_API_TOKEN` in `.env` first. Keep this API on a trusted local network; it is not intended to be exposed directly to the public internet.

LibreTranslate can be self-hosted or any compatible endpoint can be set with `LIBRETRANSLATE_URL`. Set `GROQ_API_KEY` to enable the glossary-guided route. Without external services, the app uses a deliberately tiny word map to make the interface demonstrable; it is not a real translation system. The LLM route sends script lines to Groq, so use only text you are allowed to share.

## What is included

- SQLite glossary and review history for the current script. The LLM can suggest initial terms when configured; reviewer-pinned terms are preserved.
- English, Tamil, and Bengali target choices.
- Risk hints for a small set of idioms/cultural references, glossary mismatches, and unusually long output.
- Text and change report downloads.
- A local folder watcher (`watch_folder.py`) for dropping `.txt` files into `data/inbox`.
- A FastAPI endpoint that n8n can call to analyze a script and return a review summary.

## What failed / current limits

This is an early prototype. The offline word map cannot translate full sentences. The cultural phrase list is intentionally small and will miss many risks; the review queue contains flagged lines only, so a line with no flag is not guaranteed safe. The current LLM prompt can still flatten voice or over-localize greetings such as “Ram Ram”. Glossary matching is literal and script-specific. The folder watcher is a simple local Python process, not a Drive or Telegram integration; it prints a reminder and leaves delivery to a configured workflow. No native-speaker ratings or reviewer adoption numbers have been collected yet, so this repo makes no quality or time-saved claims.

## Evaluation plan

`data/eval/challenge_lines.csv` contains 40 original practice lines for a first comparison. Have 3–5 fluent reviewers score meaning, voice, and cultural handling for both routes, while hiding which route produced each candidate. Record preference and time spent. Compare the results by category, and report cases where plain MT wins as well as estimated API cost per 1,000 words. These are starter prompts, not excerpts from a published story. Do not publish a score until real reviewers complete the sheet.

## Automation

Import `n8n/katha-lens-webhook.json` into n8n and activate it. The webhook accepts JSON such as `{"script":"राम राम भैया","target":"en"}`. In the HTTP Request node, replace the bearer token placeholder with the same `KATHA_API_TOKEN` from the app's `.env`. The workflow sends the script to the local API and returns the line flags and summary. To send a Telegram note, connect a Telegram credential and replace the chat ID placeholder. For a Drive-folder flow, add n8n's Google Drive Trigger and file download/extraction nodes before this webhook's HTTP Request step. The older local watcher is still available as a simple alternative.

The practice lines in the evaluation sheet are original examples, not excerpts from Premchand. The app accepts your own plain text stories; check the rights for the specific text and edition before sharing them. This project ships no published story text.
