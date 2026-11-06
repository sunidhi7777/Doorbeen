"""Watch a local inbox for new scripts and create translation exports."""
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from katha import analyze_script, export_files

load_dotenv()
inbox = Path(os.getenv("WATCH_FOLDER", "data/inbox"))
inbox.mkdir(parents=True, exist_ok=True)
seen = set()
print(f"Watching {inbox.resolve()} (Ctrl+C to stop)")
while True:
    for path in inbox.glob("*.txt"):
        if path in seen:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            mt, llm = analyze_script(text)
            export_files()
            print(f"Processed {path.name}: {mt}; {llm}")
            print("Review the queue in Streamlit before sharing the output.")
            seen.add(path)
        except (OSError, UnicodeError) as exc:
            print(f"Could not read {path.name}: {exc}")
    time.sleep(3)
