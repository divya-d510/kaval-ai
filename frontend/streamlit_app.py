import json
import os
from datetime import datetime

import httpx
import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from fpdf import FPDF

load_dotenv()

API_URL = os.getenv("FASTAPI_INTERNAL_URL", "http://localhost:8000") + "/api"
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansKannada.ttf")

st.set_page_config(page_title="KAVAL AI — KSP Crime Intelligence", page_icon="🚨", layout="wide")

if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "role" not in st.session_state:
    st.session_state.role = "Investigator"

ROLES = ["Investigator", "Analyst", "Supervisor", "Policymaker"]
PERMISSIONS = {
    "query": {"Investigator", "Analyst", "Supervisor"},
    "analytics": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "graph": {"Investigator", "Analyst", "Supervisor"},
    "profiling": {"Investigator", "Analyst", "Supervisor"},
    "sociological": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "financial": {"Supervisor"},
    "forecast": {"Investigator", "Analyst", "Supervisor", "Policymaker"},
    "decision_support": {"Investigator", "Analyst", "Supervisor"},
    "audit_log": {"Supervisor"},
}
NAV_ITEMS = [
    ("🔍 Ask a Question", "query"),
    ("📊 Dashboard", "analytics"),
    ("🕸️ Suspect Network", "graph"),
    ("🧬 Offender Profiling", "profiling"),
    ("🏛️ Sociological Insights", "sociological"),
    ("📈 Forecast & Early Warning", "forecast"),
    ("🗂️ Case Decision Support", "decision_support"),
    ("💰 Financial Network", "financial"),
    ("🧾 Audit Log", "audit_log"),
]

with st.sidebar:
    st.markdown("### 👤 Role")
    st.session_state.role = st.selectbox("Acting as", ROLES, index=ROLES.index(st.session_state.role))
    ROLE = st.session_state.role

    st.markdown("### 🧭 Navigate")
    visible_nav = [(label, group) for label, group in NAV_ITEMS if ROLE in PERMISSIONS[group]]
    nav_labels = [label for label, _ in visible_nav]
    label_to_group = dict(visible_nav)
    selected_label = st.radio("Navigate", nav_labels, label_visibility="collapsed")
    SELECTED = label_to_group[selected_label]

st.title("🚨 KAVAL AI")
st.caption(
    "Karnataka AI Voice & Analytics for Law enforcement — Intelligent Conversational AI for the "
    "KSP Crime Database, bilingual (English / ಕನ್ನಡ)"
)


def api_get(path: str, **params):
    r = httpx.get(f"{API_URL}{path}", params=params, headers={"X-User-Role": ROLE}, timeout=120)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict):
    r = httpx.post(f"{API_URL}{path}", json=payload, headers={"X-User-Role": ROLE}, timeout=120)
    r.raise_for_status()
    return r.json()


def speak_button(text: str, lang: str, key: str):
    voice_lang = "kn-IN" if lang == "kn" else "en-IN"
    components.html(
        f"""
        <button id="spk-{key}" style="padding:5px 12px;font-size:12px;cursor:pointer;">🔊 Listen</button>
        <script>
        document.getElementById('spk-{key}').onclick = () => {{
            const u = new SpeechSynthesisUtterance({json.dumps(text)});
            u.lang = '{voice_lang}';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
        }};
        </script>
        """,
        height=36,
    )


def build_conversation_pdf(conversation: list[dict]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Noto", "", FONT_PATH)
    pdf.set_font("Noto", size=16)
    pdf.cell(0, 10, "KAVAL AI — Conversation History", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Noto", size=9)
    pdf.cell(0, 6, datetime.now().strftime("Generated %Y-%m-%d %H:%M"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for i, turn in enumerate(conversation, 1):
        pdf.set_font("Noto", size=12)
        pdf.multi_cell(0, 7, f"Q{i}: {turn['question']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Noto", size=11)
        pdf.multi_cell(0, 6, f"A{i}: {turn['answer']}", new_x="LMARGIN", new_y="NEXT")
        if turn.get("sql"):
            pdf.set_font("Noto", size=8)
            pdf.multi_cell(0, 5, f"SQL: {turn['sql']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    return bytes(pdf.output())


# ---------------- Ask a Question ----------------
if SELECTED == "query":
    st.subheader("Ask in English or Kannada")

    with st.expander("🎤 Voice input (Chrome/Edge)"):
        lang_choice = st.radio("Speech language", ["en-IN", "kn-IN"], horizontal=True, key="voice_lang_choice")
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
    question = st.text_input("Your question", value=default_q, placeholder="e.g. How many robberies in Whitefield this year? Then try a follow-up like 'and in Mysuru?'")

    ask_clicked = st.button("Ask", type="primary")

    if ask_clicked and question.strip():
        with st.spinner("Analyzing..."):
            try:
                history = [
                    {"question": t["question"], "answer": t["answer"]}
                    for t in st.session_state.conversation[-4:]
                ]
                result = api_post("/query", {"question": question, "history": history})
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()
        st.session_state.conversation.append(result)

    if st.session_state.conversation:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Clear conversation"):
                st.session_state.conversation = []
                st.rerun()
        with c2:
            st.download_button(
                "📄 Download conversation as PDF",
                data=build_conversation_pdf(st.session_state.conversation),
                file_name=f"kaval_ai_conversation_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
            )

    st.divider()
    for i, turn in enumerate(reversed(st.session_state.conversation)):
        idx = len(st.session_state.conversation) - i
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
            speak_button(turn["answer"], turn.get("language", "en"), key=f"turn{idx}")
            if turn.get("rows"):
                st.dataframe(pd.DataFrame(turn["rows"]), use_container_width=True)
            with st.expander("Generated SQL"):
                st.code(turn.get("sql", ""), language="sql")
                if turn.get("explanation"):
                    st.caption(turn["explanation"])


# ---------------- Dashboard ----------------
if SELECTED == "analytics":
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


# ---------------- Suspect Network ----------------
if SELECTED == "graph":
    st.subheader("Criminal Association Network")
    st.caption("Edges = known associations (gang/family) + co-accusation in the same FIR + shared case locations.")
    include_victims = st.checkbox("Include victims in network (denser graph)", value=False)

    if st.button("Build network", type="primary"):
        with st.spinner("Building graph..."):
            try:
                g = api_get("/graph", include_victims=include_victims)
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        stats = g["stats"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Suspects", stats["num_suspects"])
        c2.metric("Locations", stats["num_locations"])
        c3.metric("Victims", stats["num_victims"])
        c4.metric("Links", stats["num_links"])
        c5.metric("Groups", stats["num_communities"])

        pos = {n["id"]: (n["x"], n["y"]) for n in g["nodes"]}
        edge_x, edge_y = [], []
        for e in g["edges"]:
            x0, y0 = pos[e["source"]]
            x1, y1 = pos[e["target"]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                 line=dict(width=0.5, color="#cbd5e1"), hoverinfo="none", showlegend=False))

        suspects_n = [n for n in g["nodes"] if n["type"] == "suspect"]
        locations_n = [n for n in g["nodes"] if n["type"] == "location"]
        victims_n = [n for n in g["nodes"] if n["type"] == "victim"]

        if suspects_n:
            fig.add_trace(go.Scatter(
                x=[n["x"] for n in suspects_n], y=[n["y"] for n in suspects_n],
                mode="markers", name="Suspects",
                marker=dict(size=[8 + 3 * n["prior_cases"] for n in suspects_n],
                            color=[n["community"] for n in suspects_n], colorscale="Turbo",
                            line=dict(width=1, color="white")),
                text=[f"{n['name']} ({n['id']})<br>Prior cases: {n['prior_cases']}<br>Connections: {n['degree']}" for n in suspects_n],
                hoverinfo="text",
            ))
        if locations_n:
            fig.add_trace(go.Scatter(
                x=[n["x"] for n in locations_n], y=[n["y"] for n in locations_n],
                mode="markers", name="Locations",
                marker=dict(size=14, color="#111827", symbol="diamond", line=dict(width=1, color="white")),
                text=[f"📍 {n['name']}<br>Connections: {n['degree']}" for n in locations_n],
                hoverinfo="text",
            ))
        if victims_n:
            fig.add_trace(go.Scatter(
                x=[n["x"] for n in victims_n], y=[n["y"] for n in victims_n],
                mode="markers", name="Victims",
                marker=dict(size=7, color="#a855f7", symbol="circle", line=dict(width=1, color="white")),
                text=[f"🧍 {n['name']}" for n in victims_n],
                hoverinfo="text",
            ))

        fig.update_layout(showlegend=True, height=650,
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Most connected suspects (network centrality)**")
        st.dataframe(pd.DataFrame(stats["top_central"]), use_container_width=True)


# ---------------- Offender Profiling ----------------
if SELECTED == "profiling":
    st.subheader("Criminology-Based Offender Profiling")
    st.caption("Risk score is a transparent weighted formula — the breakdown shows exactly how each score is built.")

    if st.button("Load priority investigation list", type="primary"):
        with st.spinner("Scoring suspects..."):
            try:
                st.session_state.profiling_top = api_get("/profiling/top", limit=15)["suspects"]
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

    if st.session_state.get("profiling_top"):
        st.markdown("**Priority Investigation List (highest risk first)**")
        st.dataframe(pd.DataFrame(st.session_state.profiling_top), use_container_width=True)

    st.divider()
    suspect_id = st.text_input("Suspect ID for a full profile", placeholder="e.g. SUS-00040")
    if st.button("Build profile") and suspect_id.strip():
        with st.spinner("Building profile..."):
            try:
                profile = api_get(f"/profiling/{suspect_id.strip()}")
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()
        if profile.get("error"):
            st.error(profile["error"])
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Risk score", f"{profile['risk_score']} / 100")
                st.write(f"**Modus operandi:** {profile['modus_operandi']}")
            with c2:
                breakdown = profile["risk_breakdown"]
                df = pd.DataFrame([
                    {"factor": k.replace("_", " ").title(), "contribution": v["contribution"]}
                    for k, v in breakdown.items()
                ])
                st.plotly_chart(px.bar(df, x="contribution", y="factor", orientation="h",
                                        title="Risk score breakdown (points out of 100)"), use_container_width=True)
            st.markdown("**Behavioral summary**")
            st.info(profile["behavioral_summary"])
            st.markdown("**Case history**")
            st.dataframe(pd.DataFrame(profile["case_history"]), use_container_width=True)


# ---------------- Sociological Insights ----------------
if SELECTED == "sociological":
    st.subheader("Sociological Crime Insights")
    lang = st.radio("Briefing language", ["en", "kn"], horizontal=True,
                     format_func=lambda x: "English" if x == "en" else "ಕನ್ನಡ", key="socio_lang")

    if st.button("Load insights", type="primary"):
        with st.spinner("Analyzing demographics..."):
            try:
                data = api_get("/sociological", language=lang)
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        st.info(data["summary"])

        c1, c2, c3 = st.columns(3)
        with c1:
            df = pd.DataFrame(list(data["by_gender"].items()), columns=["Gender", "Count"])
            st.plotly_chart(px.pie(df, names="Gender", values="Count", title="Accused by Gender"), use_container_width=True)
        with c2:
            df = pd.DataFrame(list(data["by_socio_economic_band"].items()), columns=["Band", "Count"])
            st.plotly_chart(px.pie(df, names="Band", values="Count", title="Accused by Socio-Economic Band"), use_container_width=True)
        with c3:
            df = pd.DataFrame(list(data["by_education_level"].items()), columns=["Education", "Count"])
            st.plotly_chart(px.bar(df, x="Education", y="Count", title="Accused by Education Level"), use_container_width=True)

        rows = [
            {"Socio-Economic Band": band, "Crime Type": crime, "Count": count}
            for band, crimes in data["crime_type_by_socio_band"].items()
            for crime, count in crimes.items()
        ]
        if rows:
            df = pd.DataFrame(rows)
            st.plotly_chart(px.bar(df, x="Crime Type", y="Count", color="Socio-Economic Band", barmode="group",
                                    title="Crime Type by Socio-Economic Band"), use_container_width=True)

        df = pd.DataFrame(list(data["area_low_band_share"].items()), columns=["Area", "Low-band share"])
        df = df.sort_values("Low-band share", ascending=False).head(10)
        st.plotly_chart(px.bar(df, x="Low-band share", y="Area", orientation="h",
                                title="Top areas by share of accused from Low socio-economic band"), use_container_width=True)
        st.caption("Observed correlations in this dataset only — not causal claims.")


# ---------------- Forecast & Early Warning ----------------
if SELECTED == "forecast":
    st.subheader("Crime Forecasting & Early Warning")
    st.caption("Heuristic trend extrapolation (linear regression over the last 6 months per district + crime type) — "
               "a first-pass indicator, not a calibrated ML forecast.")

    if st.button("Run forecast", type="primary"):
        with st.spinner("Projecting trends..."):
            try:
                data = api_get("/forecast")
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        warnings = data["early_warnings"]
        if warnings:
            st.warning(f"⚠️ {len(warnings)} district/crime-type combination(s) flagged for an accelerating trend:")
            for w in warnings:
                st.markdown(f"- **{w['district']} — {w['crime_type']}**: projected {w['next_month_projection']} next "
                            f"month (recent trend slope {w['trend_slope']})")
        else:
            st.success("No early-warning combinations detected in the current window.")

        df = pd.DataFrame(data["projections"])
        if not df.empty:
            df["label"] = df["district"] + " — " + df["crime_type"]
            st.plotly_chart(
                px.bar(df.head(15), x="trend_slope", y="label", orientation="h",
                       color="early_warning", title="Trend slope by district/crime type (top 15)"),
                use_container_width=True,
            )
            st.dataframe(df[["district", "crime_type", "monthly_counts", "trend_slope",
                              "next_month_projection", "early_warning"]], use_container_width=True)


# ---------------- Case Decision Support ----------------
if SELECTED == "decision_support":
    st.subheader("Investigator Decision Support")
    fir_id = st.text_input("FIR ID", placeholder="e.g. FIR-2025-00023")
    if st.button("Build case summary", type="primary") and fir_id.strip():
        with st.spinner("Summarizing case..."):
            try:
                data = api_get(f"/case-summary/{fir_id.strip()}")
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()
        if data.get("error"):
            st.error(data["error"])
        else:
            fir = data["fir"]
            st.markdown(f"### {fir['fir_id']} — {fir['crime_type']} ({fir['status']})")
            st.write(f"**Filed:** {fir['date_filed']} · **{fir['police_station']}, {fir['district']}, {fir['area']}**")
            st.write(fir["description"])

            st.markdown("**AI case summary & suggested leads**")
            st.info(data["narrative"])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Accused**")
                st.dataframe(pd.DataFrame(data["accused"]), use_container_width=True)
            with c2:
                st.markdown("**Victims**")
                st.dataframe(pd.DataFrame(data["victims"]), use_container_width=True)

            st.markdown("**Similar past cases**")
            st.dataframe(pd.DataFrame(data["similar_cases"]), use_container_width=True)


# ---------------- Financial Network (Supervisor only) ----------------
if SELECTED == "financial":
    st.subheader("Financial Crime & Transaction Link Analysis")
    st.caption("Restricted to the Supervisor role. Flags are transparent heuristics (high-value transfers, "
               "FIR-linked transactions, multi-counterparty 'mule' accounts) — not ML.")

    if st.button("Load financial network", type="primary"):
        with st.spinner("Analyzing transactions..."):
            try:
                data = api_get("/financial")
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()

        stats = data["stats"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Accounts", stats["num_accounts"])
        c2.metric("Transactions", stats["num_transactions"])
        c3.metric("Flagged transactions", stats["num_flagged_transactions"])
        c4.metric("Possible mule accounts", stats["num_mule_accounts"])
        st.metric("Total flagged amount (Rs.)", f"{stats['total_flagged_amount']:,.0f}")

        st.markdown("**Flagged transactions**")
        st.dataframe(pd.DataFrame(data["flagged_transactions"]), use_container_width=True)

        g = nx.Graph()
        for n in data["nodes"]:
            g.add_node(n["id"])
        for e in data["edges"]:
            g.add_edge(e["source"], e["target"])
        pos = nx.spring_layout(g, seed=42, k=0.4)

        edge_x, edge_y = [], []
        for e in data["edges"]:
            if e["source"] in pos and e["target"] in pos:
                x0, y0 = pos[e["source"]]
                x1, y1 = pos[e["target"]]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

        plotted = [n for n in data["nodes"] if n["id"] in pos]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=0.5, color="#cbd5e1"),
                                 hoverinfo="none", showlegend=False))
        fig.add_trace(go.Scatter(
            x=[pos[n["id"]][0] for n in plotted],
            y=[pos[n["id"]][1] for n in plotted],
            mode="markers", name="Accounts",
            marker=dict(
                size=[16 if n["flagged_mule"] else 9 for n in plotted],
                color=["#dc2626" if n["flagged_mule"] else "#2563eb" for n in plotted],
                line=dict(width=1, color="white"),
            ),
            text=[f"{n['name']} — {n['bank']} ({n['type']})" + (" ⚠️ possible mule" if n["flagged_mule"] else "")
                  for n in plotted],
            hoverinfo="text",
        ))
        fig.update_layout(showlegend=False, height=550, xaxis=dict(visible=False), yaxis=dict(visible=False),
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


# ---------------- Audit Log (Supervisor only) ----------------
if SELECTED == "audit_log":
    st.subheader("Governance: Audit Log")
    st.caption("Every API access is logged with role, endpoint, and a short summary — restricted to the Supervisor role.")
    if st.button("Refresh audit log", type="primary"):
        try:
            data = api_get("/audit-log", limit=200)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()
        st.dataframe(pd.DataFrame(data["entries"]), use_container_width=True)
