"""HTTP entry point for n8n and other local automations."""
import json
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from katha import analyze_script, connect, export_files

app = FastAPI(title="Katha-Lens API", version="0.1.0")


class ScriptRequest(BaseModel):
    script: str = Field(min_length=1, max_length=30000)
    target: Literal["en", "ta", "bn"] = "en"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: ScriptRequest, authorization: str = Header(default="")):
    expected = os.getenv("KATHA_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Set KATHA_API_TOKEN before using the API")
    if authorization != "Bearer " + expected:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    mt_name, llm_name = analyze_script(request.script, request.target)
    export_files()
    with connect() as db:
        rows = db.execute("SELECT * FROM lines ORDER BY id").fetchall()

    lines = []
    for row in rows:
        lines.append({
            "id": row["id"],
            "source": row["source"],
            "plain": row["plain"],
            "assisted": row["assisted"],
            "final": row["final"],
            "flags": json.loads(row["flags"]),
        })
    flagged = [line for line in lines if line["flags"]]
    return {
        "total_lines": len(lines),
        "flagged_lines": len(flagged),
        "plain_route": mt_name,
        "assisted_route": llm_name,
        "review_preview": [
            f'{line["id"]}. {line["source"]} — {", ".join(line["flags"])}'
            for line in flagged[:8]
        ],
        "lines": lines,
        "files": ["data/outputs/translation.txt", "data/outputs/change-report.md"],
    }
