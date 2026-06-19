"""
TruthLens AI — Streamlit application (advanced UI).

Run:  streamlit run app.py   (or:  python -m streamlit run app.py)

A modern, multi-page UI over the multi-agent misinformation-detection engine:
 - animated confidence gauge
 - in-text highlighting of suspicious / credible language
 - styled agentic reasoning timeline
 - an Insights dashboard with model-performance charts
 - per-session analysis history and downloadable reports
It auto-trains the model on first launch, so a fresh clone runs in one command.
"""
from __future__ import annotations

import html as ihtml
import re
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config                      # noqa: E402
from src.agents import AgentOrchestrator    # noqa: E402
from src.llm import get_llm                 # noqa: E402
from src.model import load_metrics, model_exists  # noqa: E402

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# --------------------------------------------------------------------------- #
st.set_page_config(page_title=f"{config.APP_TITLE} — Misinformation Detector",
                   page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
:root { --navy:#0f2027; --teal:#2c5364; --green:#11998e; --ink:#1f2d3d; --muted:#64748b; }
html, body, [class*="css"] { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
.block-container { padding-top: 1.4rem; max-width: 1250px; }
#MainMenu, footer {visibility: hidden;}

.tl-hero {
  background: radial-gradient(1200px 300px at 10% -20%, #2c5364 0%, transparent 60%),
              linear-gradient(120deg, #0f2027 0%, #203a43 55%, #2c5364 100%);
  padding: 1.8rem 2rem; border-radius: 20px; color: #fff; margin-bottom: 1.3rem;
  box-shadow: 0 12px 30px rgba(15,32,39,.28);
}
.tl-hero h1 { margin: 0; font-size: 2.15rem; font-weight: 800; letter-spacing:.3px; }
.tl-hero p  { margin: .4rem 0 0; opacity: .92; font-size: 1.04rem; max-width: 820px; }
.tl-badge { display:inline-block; margin-top:.7rem; background:rgba(155,227,216,.18);
  border:1px solid rgba(155,227,216,.45); color:#d7f5ee; padding:.2rem .7rem;
  border-radius:999px; font-size:.78rem; margin-right:.4rem; }

.kpi { border-radius:16px; padding:1rem 1.1rem; background:#fff; border:1px solid #e7edf3;
  box-shadow:0 6px 16px rgba(31,45,61,.06); border-top:4px solid var(--green); }
.kpi .v { font-size:1.7rem; font-weight:800; color:var(--ink); line-height:1.1; }
.kpi .l { font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; }

.verdict { padding:1.4rem 1.6rem; border-radius:18px; color:#fff; margin:.2rem 0 1rem;
  box-shadow:0 12px 26px rgba(0,0,0,.18); }
.v-fake { background:linear-gradient(120deg,#c31432,#8e0e00); }
.v-real { background:linear-gradient(120deg,#11998e,#0f7b5f); }
.verdict h2 { margin:0; font-size:1.9rem; font-weight:800; }
.verdict p  { margin:.35rem 0 0; opacity:.96; font-size:1rem; }

.panel { background:#fff; border:1px solid #e7edf3; border-radius:16px; padding:1.1rem 1.2rem;
  box-shadow:0 6px 16px rgba(31,45,61,.05); margin-bottom:1rem; }
.panel h4 { margin:.1rem 0 .7rem; color:var(--navy); font-size:1.02rem; }

.article-box { line-height:1.85; font-size:.98rem; color:#243; background:#fbfdff;
  border:1px solid #e7edf3; border-radius:12px; padding:1rem 1.1rem; }
mark.hl-red   { background:#ffe1e1; color:#a01029; padding:.05rem .25rem; border-radius:5px; font-weight:600;}
mark.hl-amber { background:#fff3cd; color:#7a5b00; padding:.05rem .25rem; border-radius:5px; font-weight:600;}
mark.hl-green { background:#dcf6ec; color:#0c6b52; padding:.05rem .25rem; border-radius:5px; font-weight:600;}
.legend span { font-size:.8rem; color:var(--muted); margin-right:1rem;}
.dot { display:inline-block; width:10px;height:10px;border-radius:3px; margin-right:5px; vertical-align:middle;}

.tl-step { position:relative; padding:.55rem .9rem .55rem 2.4rem; margin:.45rem 0;
  background:#f6f9fc; border:1px solid #e7edf3; border-radius:10px; }
.tl-step .num { position:absolute; left:.7rem; top:.55rem; width:1.15rem; height:1.15rem;
  background:var(--green); color:#fff; border-radius:50%; font-size:.72rem; font-weight:700;
  text-align:center; line-height:1.15rem; }
.tl-step b { color:#15435c; }
.evi { background:#f8fafc; border:1px solid #e7edf3; border-left:4px solid var(--teal);
  border-radius:10px; padding:.7rem .9rem; margin:.45rem 0; font-size:.92rem; }
.chip { display:inline-block; background:#eef3f8; color:#1f2d3d; padding:.22rem .65rem;
  border-radius:999px; font-size:.78rem; margin:.12rem .25rem .12rem 0; border:1px solid #dde6ef;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_engine() -> AgentOrchestrator:
    if not model_exists():
        from src.train import train_and_evaluate
        train_and_evaluate()
    return AgentOrchestrator()


SAMPLE_FAKE = ("SHOCKING: Doctors HATE this one secret miracle cure they don't want you to "
    "know about!! Sources say the mainstream media is hiding the explosive truth about a "
    "banned remedy that fixes everything overnight. Share before it's deleted — wake up "
    "and do your own research!!!")
SAMPLE_REAL = ("According to the Reserve Bank, inflation rose 3 percent in the last quarter, "
    "based on data collected over 12 months. In a statement on March 14, Governor Lee said "
    "the committee would review the figures before the next policy meeting. The report was "
    "reviewed by the National Statistics Office.")


# --------------------------- helpers --------------------------- #
def kpi(label, value, accent="#11998e"):
    return (f"<div class='kpi' style='border-top-color:{accent}'>"
            f"<div class='v'>{value}</div><div class='l'>{label}</div></div>")


def highlight_article(text: str, signals: dict) -> str:
    """Wrap detected suspicious / credible phrases in coloured marks (single pass, no nesting)."""
    mapping, order = {}, []
    def add(words, cls):
        for w in words:
            k = ihtml.escape(w).lower().strip()
            if len(k) >= 2 and k not in mapping:
                mapping[k] = cls
                order.append(ihtml.escape(w))
    add(signals.get("sensational_hits", []), "hl-red")
    add(signals.get("clickbait_hits", []), "hl-red")
    add(signals.get("vague_sourcing_hits", []), "hl-amber")
    add(signals.get("credibility_marker_hits", []), "hl-green")
    safe = ihtml.escape(text or "")
    if not order:
        return safe.replace("\n", "<br>")
    alt = "|".join(re.escape(p) for p in sorted(order, key=lambda x: -len(x)))
    pat = re.compile(r"(?<!\w)(" + alt + r")(?!\w)", re.IGNORECASE)
    safe = pat.sub(lambda m: f"<mark class='{mapping.get(m.group(0).lower(), 'hl-red')}'>{m.group(0)}</mark>", safe)
    return safe.replace("\n", "<br>")


def gauge(fused: float):
    if not HAS_PLOTLY:
        return None
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(fused * 100, 1),
        number={"suffix": "%", "font": {"size": 38, "color": "#1f2d3d"}},
        gauge={"axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
               "bar": {"color": "#1f2d3d", "thickness": 0.22},
               "borderwidth": 0,
               "steps": [{"range": [0, 40], "color": "#bfe9df"},
                         {"range": [40, 60], "color": "#ffe39b"},
                         {"range": [60, 100], "color": "#f5a3ae"}],
               "threshold": {"line": {"color": "#0f2027", "width": 4},
                             "thickness": 0.8, "value": round(fused * 100, 1)}}))
    fig.update_layout(height=250, margin=dict(l=15, r=15, t=15, b=5),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def report_text(title, text, r) -> str:
    s = r["signals"]
    lines = [f"# TruthLens AI — Analysis Report", f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             "", f"## Verdict: {r['verdict']}  ({r['confidence']*100:.1f}% — {r['confidence_band']})",
             f"Recommendation: {r['recommendation']}", "",
             f"Headline: {title or '(none)'}", "", "## Scores",
             f"- Fused fake-score: {r['fused_fake_score']:.3f}",
             f"- Model P(fake): {r['model_p_fake']:.3f}",
             f"- Signal risk: {r['signal_risk']:.3f}", "", "## Explanation", r["explanation"], "",
             "## Detected signals",
             f"- Sensational: {', '.join(s['sensational_hits']) or '-'}",
             f"- Clickbait: {', '.join(s['clickbait_hits']) or '-'}",
             f"- Vague sourcing: {', '.join(s['vague_sourcing_hits']) or '-'}",
             f"- Credibility markers: {', '.join(s['credibility_marker_hits']) or '-'}", "",
             "## Retrieved evidence (RAG)"]
    for e in r.get("evidence", []):
        lines.append(f"- [{e['topic']}] {e['statement']}")
    lines += ["", f"Article:", text or ""]
    return "\n".join(lines)


# --------------------------- pages --------------------------- #
def page_analyze(engine, metrics):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    cta, cb = st.columns([3, 1])
    with cb:
        st.markdown("**Quick samples**")
        if st.button("⚠️ Load fake example", use_container_width=True):
            st.session_state["title_in"] = "Doctors HATE this miracle cure!"
            st.session_state["text_in"] = SAMPLE_FAKE
        if st.button("✅ Load real example", use_container_width=True):
            st.session_state["title_in"] = "Reserve Bank reports quarterly inflation"
            st.session_state["text_in"] = SAMPLE_REAL
    with cta:
        title_in = st.text_input("Headline (optional)", key="title_in",
                                 placeholder="e.g. Reserve Bank reports quarterly inflation")
        text_in = st.text_area("Article text", key="text_in", height=180,
                               placeholder="Paste the article body here…")
    analyze = st.button("🔍  Analyze article", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if not analyze:
        st.info("👆 Paste an article and click **Analyze**, or load a sample on the right.")
        return

    if not (text_in or "").strip():
        st.error("Please paste some article text (or load a sample) first.")
        return

    with st.spinner("Running the multi-agent pipeline…"):
        try:
            r = engine.analyze(text=text_in, title=title_in)
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            return

    st.session_state.setdefault("history", [])
    st.session_state["history"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"), "verdict": r["verdict"],
        "confidence": f"{r['confidence']*100:.0f}%",
        "snippet": (text_in[:60] + "…") if len(text_in) > 60 else text_in})

    is_fake = r["verdict"] == "FAKE"
    st.markdown(
        f"<div class='verdict {'v-fake' if is_fake else 'v-real'}'>"
        f"<h2>{'⚠️' if is_fake else '✅'} Verdict: {r['verdict']}</h2>"
        f"<p>Confidence <b>{r['confidence']*100:.1f}%</b> ({r['confidence_band']}) · "
        f"{r['recommendation']}</p></div>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi("Fused fake-score", f"{r['fused_fake_score']:.2f}", "#c31432" if is_fake else "#11998e"), unsafe_allow_html=True)
    k2.markdown(kpi("Model P(fake)", f"{r['model_p_fake']:.2f}", "#2c5364"), unsafe_allow_html=True)
    k3.markdown(kpi("Signal risk", f"{r['signal_risk']:.2f}", "#e0a106"), unsafe_allow_html=True)
    k4.markdown(kpi("Latency", f"{r['total_ms']:.0f} ms", "#64748b"), unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="panel"><h4>🧭 Confidence gauge</h4>', unsafe_allow_html=True)
        fig = gauge(r["fused_fake_score"])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.progress(min(r["fused_fake_score"], 1.0),
                        text=f"Misinformation likelihood: {r['fused_fake_score']*100:.0f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><h4>🤖 Agentic reasoning pipeline</h4>', unsafe_allow_html=True)
        st.caption(f"GenAI: {r.get('llm_backend')} · Retrieval: {r.get('retrieval_backend')}")
        for i, step in enumerate(r.get("trace", []), 1):
            st.markdown(f"<div class='tl-step'><span class='num'>{i}</span>"
                        f"<b>{step['agent']}</b> · {step['elapsed_ms']:.0f} ms<br>{step['summary']}</div>",
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Highlighted article
    st.markdown('<div class="panel"><h4>🖍️ Article with detected language</h4>'
                "<div class='legend'>"
                "<span><span class='dot' style='background:#ffb3b3'></span>sensational / clickbait</span>"
                "<span><span class='dot' style='background:#ffe39b'></span>vague sourcing</span>"
                "<span><span class='dot' style='background:#a9ead3'></span>credibility marker</span></div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='article-box'>{highlight_article(text_in, r['signals'])}</div>",
                unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["🧠 Explanation", "🔎 Signals & terms", "📚 Evidence (RAG)"])
    with t1:
        st.markdown(r["explanation"])
    with t2:
        sg = r["signals"]
        chips = [f"Words: {sg['word_count']}", f"Sentences: {sg['sentence_count']}",
                 f"Exclamations: {sg['exclamation_count']}", f"ALL-CAPS: {sg['all_caps_ratio']:.2f}",
                 f"Quotes: {sg['quote_count']}", f"Entities≈ {sg['named_entity_estimate']}",
                 f"Dates: {'yes' if sg['has_dates'] else 'no'}"]
        st.markdown(" ".join(f"<span class='chip'>{c}</span>" for c in chips), unsafe_allow_html=True)
        terms = r.get("indicative_terms", {})
        import pandas as pd
        c1, c2 = st.columns(2)
        c1.caption("Top FAKE-leaning terms")
        c1.table(pd.DataFrame(terms.get("toward_fake", []), columns=["term", "weight"]))
        c2.caption("Top REAL-leaning terms")
        c2.table(pd.DataFrame(terms.get("toward_real", []), columns=["term", "weight"]))
    with t3:
        if r.get("evidence"):
            for e in r["evidence"]:
                st.markdown(f"<div class='evi'>📌 <b>[{e['topic']}]</b> {e['statement']}"
                            f"<br><small style='color:#64748b'>relevance {e['score']:.2f}</small></div>",
                            unsafe_allow_html=True)
        else:
            st.info("No closely matching reference statements were found.")

    st.download_button("⬇️  Download analysis report (.md)",
                       data=report_text(title_in, text_in, r),
                       file_name="truthlens_report.md", use_container_width=True)

    if st.session_state.get("history"):
        with st.expander(f"🕓 Session history ({len(st.session_state['history'])})"):
            import pandas as pd
            st.table(pd.DataFrame(st.session_state["history"]))


def page_dashboard(metrics):
    st.markdown('<div class="panel"><h4>📊 Model performance</h4>', unsafe_allow_html=True)
    if metrics:
        c = st.columns(5)
        c[0].markdown(kpi("Accuracy", f"{metrics.get('accuracy',0)*100:.1f}%"), unsafe_allow_html=True)
        c[1].markdown(kpi("Precision", f"{metrics.get('precision_fake',0)*100:.1f}%", "#2c5364"), unsafe_allow_html=True)
        c[2].markdown(kpi("Recall", f"{metrics.get('recall_fake',0)*100:.1f}%", "#2c5364"), unsafe_allow_html=True)
        c[3].markdown(kpi("F1 (fake)", f"{metrics.get('f1_fake',0)*100:.1f}%", "#11998e"), unsafe_allow_html=True)
        c[4].markdown(kpi("ROC-AUC", f"{metrics.get('roc_auc',0):.3f}", "#c31432"), unsafe_allow_html=True)
        st.caption(f"Model: {metrics.get('model','n/a')} · Dataset: {metrics.get('dataset_source','n/a')} · "
                   f"{metrics.get('n_train',0):,} train / {metrics.get('n_test',0):,} test · "
                   f"CV {metrics.get('cv_accuracy_mean',0)*100:.1f}% ± {metrics.get('cv_accuracy_std',0)*100:.1f}%")
    else:
        st.warning("Train the model first (run `python -m src.train`) to populate metrics.")
    st.markdown('</div>', unsafe_allow_html=True)

    imgs = [("metrics_bar.png", "Performance metrics"), ("confusion_matrix.png", "Confusion matrix"),
            ("roc_curve.png", "ROC curve"), ("dataset_distribution.png", "Dataset distribution")]
    cols = st.columns(2)
    for i, (fn, cap) in enumerate(imgs):
        path = config.IMAGES_DIR / fn
        if path.exists():
            with cols[i % 2]:
                st.markdown(f"<div class='panel'><h4>{cap}</h4>", unsafe_allow_html=True)
                st.image(str(path), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

    for fn, cap in [("architecture.png", "System architecture"), ("workflow.png", "Analysis workflow")]:
        path = config.IMAGES_DIR / fn
        if path.exists():
            st.markdown(f"<div class='panel'><h4>{cap}</h4>", unsafe_allow_html=True)
            st.image(str(path), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


def page_about():
    st.markdown(
        "<div class='panel'><h4>ℹ️ About TruthLens AI</h4>"
        "<p>TruthLens AI detects misinformation and <b>explains why</b>, combining an "
        "interpretable ML classifier (TF-IDF + Logistic Regression), a transparent "
        "linguistic credibility-signal engine, retrieval-augmented fact-checking (RAG), "
        "and a multi-agent Generative-AI layer — running fully offline on a laptop.</p>"
        "<p><b>Agents:</b> ClassifierAgent → ExplainerAgent → FactCheckAgent, fused into one "
        "calibrated verdict (0.70 × model + 0.30 × signal-risk) with a visible reasoning trace.</p>"
        "<p style='color:#64748b'>Built by Dikshant Aggarwal (Roll 12303021) · Punjabi University, "
        "Patiala · Guide: Dr. Chandan Deep Singh</p></div>", unsafe_allow_html=True)


# --------------------------- main --------------------------- #
def main():
    st.markdown(
        f"<div class='tl-hero'><h1>🛡️ {config.APP_TITLE}</h1>"
        f"<p>{config.APP_TAGLINE} — paste any news article to get an explainable, "
        f"evidence-grounded verdict in milliseconds.</p>"
        f"<span class='tl-badge'>Interpretable ML</span>"
        f"<span class='tl-badge'>RAG fact-check</span>"
        f"<span class='tl-badge'>Multi-agent GenAI</span>"
        f"<span class='tl-badge'>100% offline</span></div>", unsafe_allow_html=True)

    with st.spinner("Loading model & agents (first run trains the model, ~a few seconds)…"):
        engine = get_engine()
    metrics = load_metrics()

    with st.sidebar:
        st.markdown(f"### 🛡️ {config.APP_TITLE}")
        st.caption(config.APP_TAGLINE)
        page = st.radio("Navigate", ["🔍 Analyze", "📊 Dashboard", "ℹ️ About"], label_visibility="collapsed")
        st.divider()
        st.markdown("#### System status")
        if model_exists():
            st.success("Model: trained & loaded")
        else:
            st.warning("Model: not trained")
        st.info(f"GenAI backend: {get_llm().backend_name()}")
        st.caption("Retrieval (RAG): auto — dense if installed, else TF-IDF")
        if metrics:
            st.divider()
            st.metric("Test accuracy", f"{metrics.get('accuracy',0)*100:.1f}%")
            st.metric("ROC-AUC", f"{metrics.get('roc_auc',0):.3f}")
        st.divider()
        st.caption("Dikshant Aggarwal · 12303021\n\nPunjabi University, Patiala")

    if page.startswith("🔍"):
        page_analyze(engine, metrics)
    elif page.startswith("📊"):
        page_dashboard(metrics)
    else:
        page_about()


if __name__ == "__main__":
    main()
