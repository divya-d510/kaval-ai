import os

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_INTERNAL_URL", "http://localhost:8000") + "/api"

st.set_page_config(page_title="KSP Crime Analytics", page_icon="🚨", layout="wide")

st.title("🚨 KSP Crime Analytics")
st.caption("Bilingual (English / ಕನ್ನಡ) natural-language crime data intelligence — Karnataka State Police")

tab_query, tab_dashboard, tab_graph = st.tabs(["🔍 Ask a Question", "📊 Dashboard", "🕸️ Suspect Network"])


def api_get(path: str, **params):
    r = httpx.get(f"{API_URL}{path}", params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict):
    r = httpx.post(f"{API_URL}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


# ---------------- Query tab ----------------
with tab_query:
    st.subheader("Ask in English or Kannada")

    with st.expander("🎤 Voice input (Chrome/Edge)"):
        lang_choice = st.radio("Speech language", ["en-IN", "kn-IN"], horizontal=True)
        components.html(
            f"""
            <button id="rec" style="padding:8px 16px;font-size:15px;cursor:pointer;">🎤 Start recording</button>
            <p id="out" style="font-family:sans-serif;font-size:15px;"></p>
            <script>
            const btn = document.getElementById('rec');
            const out = document.getElementById('out');
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{ out.textContent = 'Speech recognition not supported in this browser.'; }}
            else {{
                const rec = new SR();
                rec.lang = '{lang_choice}';
                rec.interimResults = false;
                btn.onclick = () => {{ out.textContent = 'Listening...'; rec.start(); }};
                rec.onresult = (e) => {{
                    const text = e.results[0][0].transcript;
                    out.textContent = 'Heard: ' + text + ' — copy it into the question box below.';
                }};
                rec.onerror = (e) => {{ out.textContent = 'Error: ' + e.error; }};
            }}
            </script>
            """,
            height=110,
        )

    examples = [
        "How many thefts were reported in Bengaluru Urban?",
        "Which police station has the most open cases?",
        "ಮೈಸೂರಿನಲ್ಲಿ ಎಷ್ಟು ಸೈಬರ್ ಅಪರಾಧ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?",
        "List suspects with more than 3 prior cases",
    ]
    example = st.selectbox("Try an example", ["(type your own)"] + examples)
    default_q = "" if example == "(type your own)" else example
    question = st.text_input("Your question", value=default_q, placeholder="e.g. How many robberies in Whitefield this year?")

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Analyzing..."):
            try:
                result = api_post("/query", {"question": question})
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        st.markdown(f"**Answer:** {result['answer']}")
        if result.get("rows"):
            st.dataframe(pd.DataFrame(result["rows"]), use_container_width=True)
        with st.expander("Generated SQL"):
            st.code(result["sql"], language="sql")
            if result.get("explanation"):
                st.caption(result["explanation"])


# ---------------- Dashboard tab ----------------
with tab_dashboard:
    st.subheader("Crime Overview")
    lang = st.radio("Briefing language", ["en", "kn"], horizontal=True, format_func=lambda x: "English" if x == "en" else "ಕನ್ನಡ")

    if st.button("Load dashboard", type="primary"):
        with st.spinner("Computing statistics..."):
            try:
                stats = api_get("/analytics", language=lang, summary=True)
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        st.info(stats["summary"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Total FIRs", stats["total_firs"])
        c2.metric("Districts", len(stats["by_district"]))
        c3.metric("Open cases", stats["by_status"].get("Open", 0))

        col1, col2 = st.columns(2)
        with col1:
            df = pd.DataFrame(list(stats["by_crime_type"].items()), columns=["Crime Type", "FIRs"])
            st.plotly_chart(px.bar(df, x="Crime Type", y="FIRs", title="FIRs by Crime Type"), use_container_width=True)
        with col2:
            df = pd.DataFrame(list(stats["by_district"].items()), columns=["District", "FIRs"])
            st.plotly_chart(px.pie(df, names="District", values="FIRs", title="FIRs by District"), use_container_width=True)

        df = pd.DataFrame(list(stats["by_month"].items()), columns=["Month", "FIRs"])
        st.plotly_chart(px.line(df, x="Month", y="FIRs", title="FIRs per Month", markers=True), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            df = pd.DataFrame(list(stats["top_areas"].items()), columns=["Area", "FIRs"])
            st.plotly_chart(px.bar(df, x="FIRs", y="Area", orientation="h", title="Top 10 Hotspot Areas"), use_container_width=True)
        with col4:
            df = pd.DataFrame(list(stats["by_status"].items()), columns=["Status", "FIRs"])
            st.plotly_chart(px.pie(df, names="Status", values="FIRs", title="Case Status", hole=0.4), use_container_width=True)


# ---------------- Graph tab ----------------
with tab_graph:
    st.subheader("Suspect Association Network")
    st.caption("Edges = known associations (gang/family) + co-accusation in the same FIR. Node size = prior cases.")

    if st.button("Build network", type="primary"):
        with st.spinner("Building graph..."):
            try:
                g = api_get("/graph")
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        stats = g["stats"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Connected suspects", stats["num_suspects"])
        c2.metric("Links", stats["num_links"])
        c3.metric("Detected groups", stats["num_communities"])

        edge_x, edge_y = [], []
        pos = {n["id"]: (n["x"], n["y"]) for n in g["nodes"]}
        for e in g["edges"]:
            x0, y0 = pos[e["source"]]
            x1, y1 = pos[e["target"]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                 line=dict(width=0.6, color="#94a3b8"), hoverinfo="none"))
        fig.add_trace(go.Scatter(
            x=[n["x"] for n in g["nodes"]],
            y=[n["y"] for n in g["nodes"]],
            mode="markers",
            marker=dict(
                size=[8 + 3 * n["prior_cases"] for n in g["nodes"]],
                color=[n["community"] for n in g["nodes"]],
                colorscale="Turbo",
                line=dict(width=1, color="white"),
            ),
            text=[f"{n['name']} ({n['id']})<br>Prior cases: {n['prior_cases']}<br>Connections: {n['degree']}"
                  for n in g["nodes"]],
            hoverinfo="text",
        ))
        fig.update_layout(showlegend=False, height=650,
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Most connected suspects (network centrality)**")
        st.dataframe(pd.DataFrame(stats["top_central"]), use_container_width=True)
