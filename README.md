# Katha-Lens

A small human-in-the-loop review desk for Hindi story localization. Paste a script, compare a plain translation route with a glossary-guided LLM route, and review only the lines that look risky.

## Run it

1. Install Python 3.10 or newer.
2. `py -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env`, then set credentials and service URLs if you want live translation.
5. `streamlit run app.py`

LibreTranslate can be self-hosted or any compatible endpoint can be set with `LIBRETRANSLATE_URL`. Set `GROQ_API_KEY` to enable the glossary-guided route. Without external services, the app uses a deliberately tiny word map to make the interface demonstrable; it is not a real translation system. The LLM route sends script lines to Groq, so use only text you are allowed to share.

## What is included

- SQLite glossary and review history for the current script. The LLM can suggest initial terms when configured; reviewer-pinned terms are preserved.
- English, Tamil, and Bengali target choices.
- Risk hints for a small set of idioms/cultural references, glossary mismatches, and unusually long output.
- Text and change report downloads.
- A local folder watcher (`watch_folder.py`) for dropping `.txt` files into `data/inbox`.

## What failed / current limits

This is an early prototype. The offline word map cannot translate full sentences. The cultural phrase list is intentionally small and will miss many risks; the review queue contains flagged lines only, so a line with no flag is not guaranteed safe. The current LLM prompt can still flatten voice or over-localize greetings such as “Ram Ram”. Glossary matching is literal and script-specific. The folder watcher is a simple local Python process, not a Drive or Telegram integration; it prints a reminder and leaves delivery to a configured workflow. No native-speaker ratings or reviewer adoption numbers have been collected yet, so this repo makes no quality or time-saved claims.

## Evaluation plan

`data/eval/challenge_lines.csv` contains 40 original practice lines for a first comparison. Have 3–5 fluent reviewers score meaning, voice, and cultural handling for both routes, while hiding which route produced each candidate. Record preference and time spent. Compare the results by category, and report cases where plain MT wins as well as estimated API cost per 1,000 words. These are starter prompts, not excerpts from a published story. Do not publish a score until real reviewers complete the sheet.

## Automation

Run `py watch_folder.py` in a second terminal. Each new `.txt` file is translated and exported under `data/outputs`. It watches locally and does not connect to Drive, Telegram, or email yet. A later n8n flow can mount/sync this folder and handle notifications.

The practice lines in the evaluation sheet are original examples, not excerpts from Premchand. The app accepts your own plain text stories; check the rights for the specific text and edition before sharing them. This project ships no published story text.
