"""Translation and review helpers for Katha-Lens."""
import json
import os
import re
import sqlite3
from pathlib import Path

import requests

DB_PATH = Path(os.getenv("KATHA_DB", "data/katha.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS glossary
        (source TEXT PRIMARY KEY, target TEXT NOT NULL, note TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS lines
        (id INTEGER PRIMARY KEY, source TEXT NOT NULL, plain TEXT DEFAULT '',
         assisted TEXT DEFAULT '', language TEXT DEFAULT 'en',
         flags TEXT DEFAULT '[]', final TEXT DEFAULT '', reviewed INTEGER DEFAULT 0)""")
    db.commit()
    return db


def get_glossary():
    with connect() as db:
        rows = db.execute("SELECT source,target FROM glossary ORDER BY source")
        return {row["source"]: row["target"] for row in rows}


def save_term(source, target, note=""):
    if source.strip() and target.strip():
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO glossary VALUES(?,?,?)",
                       (source.strip(), target.strip(), note.strip()))


def flag_line(line, translation, glossary):
    flags = []
    if re.search(r"(आँखों का तारा|नाक कटना|दाल नहीं गलना|राम राम|होली|दीवाली|ईद|प्रसाद|पंचायत)", line):
        flags.append("idiom or cultural reference")
    for source, target in glossary.items():
        if source in line and target.casefold() not in translation.casefold():
            flags.append("glossary mismatch: " + source)
    if len(translation.split()) > max(8, len(line.split()) * 3):
        flags.append("possible tone or length shift")
    return flags


def translate_mt(text, target):
    url = os.getenv("LIBRETRANSLATE_URL", "").strip()
    if url:
        try:
            body = {"q": text, "source": "hi", "target": target, "format": "text"}
            key = os.getenv("LIBRETRANSLATE_API_KEY", "")
            if key:
                body["api_key"] = key
            response = requests.post(url, json=body, timeout=25)
            response.raise_for_status()
            return response.json()["translatedText"], "LibreTranslate"
        except (requests.RequestException, KeyError, ValueError):
            pass

    # This tiny map is only here to let the screens run without a translation service.
    words = {"राम राम": "Ram Ram", "राम": "Ram", "भैया": "Bhaiya",
             "चौधरी": "Chaudhary", "जी": "ji", "गाँव": "village",
             "घर": "home", "पानी": "water", "आओ": "come", "जाओ": "go"}
    result = text
    for source in sorted(words, key=len, reverse=True):
        result = result.replace(source, words[source])
    return result, "offline demo word map"


def translate_llm(text, target, context):
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return "", "GROQ_API_KEY is not set"
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    language_name = {"en": "English", "ta": "Tamil", "bn": "Bengali"}.get(target, target)
    prompt = (
        f"Translate this Hindi story line into {language_name}. Keep meaning and voice natural. "
        "Follow the glossary exactly; do not replace cultural greetings with a different greeting. "
        "Return only the translation.\nGlossary: "
        + json.dumps(get_glossary(), ensure_ascii=False)
        + "\nNearby lines: " + context + "\nLine: " + text
    )
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2},
            timeout=45,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"].strip()
        return answer, model
    except (requests.RequestException, KeyError, ValueError) as exc:
        return "", "LLM request failed: " + str(exc)


def suggest_terms(script):
    """Ask the model for a few names and culture-specific terms, if it is configured."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return 0
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "Find recurring character names, honorifics, relationships, foods, festivals, "
        "and idioms in this Hindi story. Return only JSON with a terms array. Each item "
        "must have source, target, note. Keep names and greetings in their original form "
        "unless the story clearly gives another rendering. Do not guess terms absent from "
        "the text.\nStory:\n" + script[:12000]
    )
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0}, timeout=45,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        added = 0
        with connect() as db:
            for item in data.get("terms", []):
                source = str(item.get("source", "")).strip()
                target = str(item.get("target", "")).strip()
                if source and target:
                    cursor = db.execute(
                        "INSERT OR IGNORE INTO glossary(source,target,note) VALUES(?,?,?)",
                        (source, target, str(item.get("note", "LLM suggestion"))),
                    )
                    added += cursor.rowcount
        return added
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return 0


def analyze_script(script, target="en"):
    lines = [line.strip() for line in script.splitlines() if line.strip()]
    suggest_terms(script)
    glossary = get_glossary()
    with connect() as db:
        db.execute("DELETE FROM lines")
        mt_name = llm_name = ""
        for i, line in enumerate(lines):
            plain, mt_name = translate_mt(line, target)
            context = " ".join(lines[max(0, i - 1):i] + lines[i + 1:i + 2])
            assisted, llm_name = translate_llm(line, target, context)
            final = assisted or plain
            flags = flag_line(line, final, glossary)
            db.execute("""INSERT INTO lines(source,plain,assisted,language,flags,final)
                          VALUES(?,?,?,?,?,?)""",
                       (line, plain, assisted, target,
                        json.dumps(flags, ensure_ascii=False), final))
        db.commit()
    return mt_name or "no lines", llm_name or "no lines"


def review_line(line_id, correction, term="", keep_as=""):
    with connect() as db:
        db.execute("UPDATE lines SET final=?,reviewed=1 WHERE id=?",
                   (correction.strip(), line_id))
        if term.strip() and keep_as.strip():
            db.execute("INSERT OR REPLACE INTO glossary(source,target,note) VALUES(?,?,?)",
                       (term.strip(), keep_as.strip(), "Pinned during line review"))
        db.commit()


def export_files():
    with connect() as db:
        rows = db.execute("SELECT * FROM lines ORDER BY id").fetchall()
    output = "\n".join(row["final"] for row in rows)
    report = ["# Change report", ""]
    for row in rows:
        flags = json.loads(row["flags"])
        if row["reviewed"]:
            report.append(f"- Line {row['id']}: reviewer saved a correction.")
        elif flags:
            report.append(f"- Line {row['id']}: still flagged ({', '.join(flags)}).")
    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "translation.txt").write_text(output, encoding="utf-8")
    (out_dir / "change-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return output, "\n".join(report)
