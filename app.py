import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from katha import (analyze_script, connect, export_files, get_glossary,
                   review_line, save_term)

st.set_page_config(page_title="Katha-Lens", page_icon="📚", layout="wide")
st.title("Katha-Lens")
st.caption("A small review desk for Hindi story translations. Flags are hints; a person makes the call.")

page = st.sidebar.radio("Open", ["Translate", "Review queue", "Glossary"])
if page == "Translate":
    st.subheader("Start with a few lines")
    language = st.selectbox(
        "Translate into", ["en", "ta", "bn"],
        format_func=lambda code: {"en": "English", "ta": "Tamil", "bn": "Bengali"}[code])
    uploaded = st.file_uploader("Or upload a plain text story", type=["txt"])
    initial = uploaded.getvalue().decode("utf-8", errors="replace") if uploaded else ""
    script = st.text_area("Hindi script", value=initial, height=260,
                          placeholder="Paste one line per paragraph")
    if st.button("Translate and check", type="primary", disabled=not script.strip()):
        with st.spinner("Translating lines..."):
            mt_name, llm_name = analyze_script(script, language)
        st.success(f"Plain route: {mt_name}. Glossary route: {llm_name}.")
    with connect() as db:
        count = db.execute("SELECT count(*) FROM lines").fetchone()[0]
    if count:
        output, report = export_files()
        st.download_button("Download translation", output, file_name="translation.txt")
        st.download_button("Download change report", report, file_name="change-report.md")

elif page == "Review queue":
    st.subheader("Lines to look at")
    with connect() as db:
        rows = db.execute("SELECT * FROM lines ORDER BY id").fetchall()
    if not rows:
        st.info("Run a script first.")
    for row in rows:
        flags = json.loads(row["flags"])
        if flags and not row["reviewed"]:
            label = ", ".join(flags) if flags else "not reviewed"
            with st.expander(f"Line {row['id']} · {label}"):
                st.write("**Hindi**")
                st.write(row["source"])
                left, right = st.columns(2)
                left.write("Plain route")
                left.write(row["plain"])
                right.write("Glossary route")
                right.write(row["assisted"] or "Unavailable; check your Groq key.")
                edit = st.text_area("Final wording", value=row["final"], key=f"edit-{row['id']}")
                term = st.text_input("Term to pin for later (optional)", key=f"term-{row['id']}")
                keep_as = st.text_input("Keep or translate it as", key=f"keep-{row['id']}")
                if st.button("Save review", key=f"save-{row['id']}"):
                    review_line(row["id"], edit, term, keep_as)
                    st.rerun()

else:
    st.subheader("Keep names and terms consistent")
    with st.form("term"):
        source = st.text_input("Hindi term")
        target = st.text_input("Keep or translate as")
        note = st.text_input("Note (optional)")
        if st.form_submit_button("Save term"):
            save_term(source, target, note)
            st.success("Saved.")
    for source, target in get_glossary().items():
        st.write(f"**{source}** → {target}")
