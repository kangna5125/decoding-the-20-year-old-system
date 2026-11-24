"""Decoding the 20 Year Old System — Decode. Understand. Modernize. Preserve.

Streamlit application entry point. Run with: streamlit run app.py
"""
import json
import os
import streamlit as st

import config
from business_rules import detect_candidate_business_rules
from code_improvement import compute_code_diff, detect_code_risks, generate_modernization_suggestions
from config import (
    CHATBOT_NAME,
    CODET5_MODEL_DIR,
    DB_PATH,
    PRIVACY_NOTE,
    PROJECT_NAME,
    PROJECT_TAGLINE,
    SUPPORTED_LANGUAGES,
)
from explanation_engine import ExplanationStudio
from explainer import CodeExplainer
from languages import detect_language, get_language_capabilities, parse_code_structure
from llm_service import (
    auto_select_best_model,
    call_gemini,
    get_active_model,
    is_api_key_configured,
    set_active_model,
    test_gemini_connection,
)
from repository_service import RepositoryIndex, safe_extract_zip
from samples import SAMPLES, SAMPLES_BY_LANGUAGE
from visualizer import generate_mermaid_flowchart
from walkthrough import build_walkthrough

MODEL_DIR = os.environ.get("MODEL_DIR", CODET5_MODEL_DIR)
ACTIVE_DB_PATH = os.environ.get("DB_PATH", DB_PATH)

st.set_page_config(
    page_title=f"{PROJECT_NAME} — {PROJECT_TAGLINE}",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling: animated subtle gradient, drifting faint code symbols, glass cards
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, rgba(243, 244, 246, 0.85) 0%, rgba(249, 250, 251, 0.95) 40%, rgba(238, 242, 255, 0.85) 100%);
        background-size: 200% 200%;
        animation: subtleGradientShift 22s ease infinite;
    }

    @media (prefers-color-scheme: dark) {
        .stApp {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 41, 59, 0.96) 45%, rgba(17, 24, 39, 0.98) 100%);
            background-size: 200% 200%;
            animation: subtleGradientShift 22s ease infinite;
        }
    }

    @keyframes subtleGradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .bg-symbols-container {
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
        opacity: 0.045;
        background-image: radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0);
        background-size: 32px 32px;
    }

    .drift-token {
        position: absolute;
        font-family: monospace;
        font-weight: 700;
        color: currentColor;
        user-select: none;
        animation: driftFloat 18s ease-in-out infinite alternate;
    }

    @keyframes driftFloat {
        0% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-16px) rotate(4deg); }
        100% { transform: translateY(8px) rotate(-3deg); }
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.65);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.03);
    }

    @media (prefers-color-scheme: dark) {
        .glass-card {
            background: rgba(30, 41, 59, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);
        }
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .hero-tagline {
        font-size: 1.15rem;
        color: #4b5563;
        margin-bottom: 1.2rem;
    }
    @media (prefers-color-scheme: dark) {
        .hero-tagline { color: #9ca3af; }
    }
    .badge-model {
        display: inline-block;
        background: #e0f2fe;
        color: #0369a1;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .badge-verified {
        display: inline-block;
        background: #dcfce7;
        color: #15803d;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .badge-rule {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .explanation-text {
        font-size: 1.25rem;
        font-weight: 600;
        line-height: 1.5;
        margin: 0.4rem 0;
    }
    .walkthrough-step {
        margin-bottom: 0.35rem;
        line-height: 1.5;
        font-size: 0.95rem;
    }
</style>

<!-- Drifting code symbols in background -->
<div class="bg-symbols-container">
    <div class="drift-token" style="top: 8%; left: 6%; font-size: 1.6rem; animation-delay: 0s;">def</div>
    <div class="drift-token" style="top: 25%; right: 10%; font-size: 1.8rem; animation-delay: 2s;">if</div>
    <div class="drift-token" style="top: 60%; left: 14%; font-size: 1.5rem; animation-delay: 4s;">return</div>
    <div class="drift-token" style="top: 75%; right: 18%; font-size: 2.2rem; animation-delay: 1s;">{ }</div>
    <div class="drift-token" style="top: 42%; left: 48%; font-size: 1.4rem; animation-delay: 3s;">01</div>
    <div class="drift-token" style="top: 85%; left: 35%; font-size: 1.5rem; animation-delay: 5s;">for</div>
</div>
""", unsafe_allow_html=True)

if not os.path.isdir(MODEL_DIR):
    st.error(f"Model not found at '{MODEL_DIR}'. Run prepare_data.py and train.py first.")
    st.stop()


@st.cache_resource
def load_explainer(model_dir: str, db_path: str):
    return CodeExplainer(model_dir, db_path=db_path)


ex = load_explainer(MODEL_DIR, ACTIVE_DB_PATH)
studio = ExplanationStudio(ex)

# Automatic Model Detection Initialization
if is_api_key_configured() and "auto_model_init" not in st.session_state:
    sel = auto_select_best_model()
    st.session_state.auto_model_init = True
    st.session_state.active_model_name = sel.get("model")
    st.session_state.available_models = sel.get("available_models", [])


def render_confidence_gauge(score, level):
    if score is None:
        return ""
    pct = int(round(score * 100))
    color = "#10b981" if level == "High" else ("#f59e0b" if level == "Medium" else "#ef4444")
    dash_array = 220
    dash_offset = max(0, min(dash_array, dash_array * (1.0 - score)))

    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0.4rem 0;">
        <svg width="180" height="105" viewBox="0 0 180 105">
            <path d="M 20 95 A 70 70 0 0 1 160 95" fill="none" stroke="rgba(128,128,128,0.25)" stroke-width="12" stroke-linecap="round"/>
            <path d="M 20 95 A 70 70 0 0 1 160 95" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"
                  stroke-dasharray="{dash_array}" stroke-dashoffset="{dash_offset}"/>
            <text x="90" y="80" text-anchor="middle" font-size="26" font-weight="bold" fill="currentColor">{pct}%</text>
            <text x="90" y="98" text-anchor="middle" font-size="11" font-weight="700" fill="{color}">{level.upper()} CONFIDENCE</text>
        </svg>
    </div>
    """


def set_result(result, code, language="Python"):
    st.session_state.result = result
    st.session_state.result_code = code
    st.session_state.result_lang = language
    st.session_state.result_id = st.session_state.get("result_id", 0) + 1
    if "session_history" not in st.session_state:
        st.session_state.session_history = []
    st.session_state.session_history.append({
        "id": st.session_state.result_id,
        "code": code,
        "language": language,
        "result": result
    })


def load_sample():
    choice = st.session_state.sample
    if choice != "(none)":
        lang = st.session_state.get("active_language", "Python")
        lang_samples = SAMPLES_BY_LANGUAGE.get(lang, SAMPLES)
        if choice in lang_samples:
            st.session_state.code_input = lang_samples[choice]
            st.session_state.result = None


# =====================================================================
# SIDEBAR NAVIGATION (Eight modules)
# =====================================================================
st.sidebar.markdown(f"### {PROJECT_NAME}")
st.sidebar.caption(PROJECT_TAGLINE)

MODULES = [
    "1. Dashboard",
    "2. Code Analyzer",
    "3. Explanation Studio",
    "4. AI Chatbot",
    "5. Repository Intelligence",
    "6. Business Rule Detective",
    "7. Code Improvement",
    "8. Knowledge Base & Model Report"
]

selected_module = st.sidebar.radio(
    "Modules",
    MODULES,
    index=1,
    key="nav_module"
)

st.sidebar.markdown("---")
st.sidebar.metric("Saved corrections", ex.store.count())
st.sidebar.caption(f"Backend DB: `{os.path.basename(ACTIVE_DB_PATH)}`")

curr_active_model = get_active_model()
llm_status = f"✅ Active ({curr_active_model})" if is_api_key_configured() and curr_active_model else ("✅ Key detected" if is_api_key_configured() else "⚠️ Not configured")
st.sidebar.caption(f"LLM Status: **{llm_status}**")

st.sidebar.markdown("---")
st.sidebar.info(PRIVACY_NOTE)


# =====================================================================
# MODULE 1: DASHBOARD
# =====================================================================
if selected_module == "1. Dashboard":
    st.markdown(f'<div class="hero-title">{PROJECT_NAME}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-tagline">{PROJECT_TAGLINE}</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Supported Languages", len(SUPPORTED_LANGUAGES), "Python, Java, JS, C++")
    col2.metric("Saved Human Corrections", ex.store.count())
    col3.metric("CodeT5 Status", "Active (Fine-Tuned)", "Held-out test set evaluated")
    col4.metric("Gemini Model", curr_active_model or "None", "Automatic selection")

    st.markdown("---")
    st.subheader("Language Support & Capabilities")
    lang_rows = []
    for lang in SUPPORTED_LANGUAGES:
        caps = get_language_capabilities(lang)
        lang_rows.append({
            "Language": lang,
            "Primary Model / Parser": caps["model_type"],
            "Validation Status": caps["status"],
            "Benchmark Details": caps["evaluation_status"]
        })
    st.table(lang_rows)

    st.markdown("---")
    with st.expander("⚙️ Settings & Dynamic LLM Configuration", expanded=not is_api_key_configured()):
        st.markdown("#### Automatic Model Discovery & Selection")
        if is_api_key_configured():
            st.success("✅ `GEMINI_API_KEY` is detected in `.env`.")
            avail = st.session_state.get("available_models", [])

            c_mod1, c_mod2 = st.columns([2, 1])
            with c_mod1:
                if avail:
                    st.write(f"**Using:** `{curr_active_model}`, selected automatically based on tier, version, and stability.")
                    chosen = st.selectbox(
                        "Override Active Model",
                        avail,
                        index=avail.index(curr_active_model) if curr_active_model in avail else 0
                    )
                    if chosen != curr_active_model:
                        set_active_model(chosen)
                        st.success(f"Active model updated to `{chosen}`.")
                else:
                    st.write(f"Active model: `{curr_active_model or 'Auto-selecting...'}`")

            with c_mod2:
                if st.button("Re-detect best model"):
                    with st.spinner("Calling models.list API and verifying best candidate..."):
                        sel = auto_select_best_model(force_refresh=True)
                        st.session_state.available_models = sel.get("available_models", [])
                        st.session_state.active_model_name = sel.get("model")
                        st.success(sel.get("message", "Model re-detected."))
                        st.rerun()

            if st.button("Test Model Connection"):
                with st.spinner(f"Verifying {curr_active_model}..."):
                    ok, msg = test_gemini_connection(curr_active_model)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        else:
            st.warning("⚠️ `GEMINI_API_KEY` is not configured. Add it to `.env` to enable Gemini features.")

        st.caption(PRIVACY_NOTE)


# =====================================================================
# MODULE 2: CODE ANALYZER (Main Code Input & Analysis)
# =====================================================================
elif selected_module == "2. Code Analyzer":
    st.markdown('<div class="hero-title">Code Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Paste old code. Get a plain-English explanation you can trust.</div>', unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:
        lang_col1, lang_col2 = st.columns([1, 1])
        with lang_col1:
            auto_detect = st.checkbox("Auto-detect language", value=True)
        with lang_col2:
            active_lang = st.selectbox(
                "Language",
                SUPPORTED_LANGUAGES,
                index=0,
                key="active_language",
                disabled=auto_detect
            )

        curr_lang = active_lang if not auto_detect else st.session_state.get("detected_lang", "Python")
        sample_dict = SAMPLES_BY_LANGUAGE.get(curr_lang, SAMPLES)
        st.selectbox("Load an example", ["(none)"] + list(sample_dict.keys()), key="sample", on_change=load_sample)

        uploaded = st.file_uploader("Upload a source file", type=["py", "java", "js", "cpp", "cc", "h"])
        if uploaded:
            content = uploaded.read().decode("utf-8", errors="replace")
            st.session_state.code_input = content
            if auto_detect:
                detected = detect_language(content, filename=uploaded.name)
                st.session_state.detected_lang = detected
                curr_lang = detected

        code = st.text_area(
            f"Source code ({curr_lang})",
            key="code_input",
            height=320,
            placeholder=f"Paste your legacy {curr_lang} function or class here..."
        )

        if auto_detect and code.strip():
            det = detect_language(code)
            st.session_state.detected_lang = det
            curr_lang = det
            st.caption(f"Detected language: **{det}**")

        explain_btn = st.button("Explain", type="primary")

        if explain_btn:
            if not code.strip():
                st.warning("Paste some code first.")
            else:
                with st.spinner("Analyzing code..."):
                    if curr_lang == "Python":
                        res = ex.explain(code)
                    else:
                        studio_res = studio.explain(code, curr_lang, "Quick Explanation", gemini_model=get_active_model())
                        res = {
                            "source": "model",
                            "explanation": studio_res["text"],
                            "confidence": None,
                            "level": None,
                            "truncated": False,
                            "is_llm": True
                        }
                    set_result(res, code, curr_lang)

    res = st.session_state.get("result")
    with right:
        if res is None:
            st.subheader("Explanation")
            st.info("The explanation, confidence gauge, and step-by-step walkthrough will appear here after clicking Explain.")
        else:
            is_verified = (res.get("source") == "verified")
            analysis_lang = st.session_state.get("result_lang", "Python")

            st.subheader("AI summary")
            with st.container():
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                if is_verified:
                    st.markdown('<span class="badge-verified">Verified by reviewer</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="explanation-text">{res["explanation"]}</div>', unsafe_allow_html=True)
                    meta = f"Verified by **{res.get('reviewer') or 'Reviewer'}** on {res.get('saved_at', 'recently')}"
                    if res.get("similarity") is not None and res["similarity"] < 1.0:
                        meta += f" (matched similar code: {res['similarity']:.0%})"
                    st.caption(meta)
                else:
                    if analysis_lang == "Python":
                        st.markdown('<span class="badge-model">AI summary (CodeT5, fine-tuned)</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="badge-rule">LLM-based ({analysis_lang}), not separately evaluated</span>', unsafe_allow_html=True)

                    st.markdown(f'<div class="explanation-text">{res["explanation"] or "(Empty description returned)"}</div>', unsafe_allow_html=True)

                    if res.get("confidence") is not None:
                        gauge_html = render_confidence_gauge(res["confidence"], res["level"])
                        st.markdown(gauge_html, unsafe_allow_html=True)

                        if res.get("level") == "Low":
                            st.warning("⚠️ **Needs human review:** The model confidence for this explanation is low (< 35%). Please verify and correct below.")

                    if res.get("truncated"):
                        st.caption("ℹ️ Note: The input function was truncated to the model's 256-token context limit.")
                st.markdown('</div>', unsafe_allow_html=True)

            st.subheader("Step-by-step walkthrough (rule-based, read directly from the code)")
            wt = build_walkthrough(st.session_state.result_code) if analysis_lang == "Python" else None

            if analysis_lang == "Python" and wt:
                if not wt["success"]:
                    st.info(wt["error"])
                else:
                    m = wt["metrics"]
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Inputs", m["inputs"])
                    c2.metric("Decisions", m["decisions"])
                    c3.metric("Loops", m["loops"])
                    c4.metric("Function Calls", m["calls"])
                    c5.metric("Lines of Code", m["loc"])

                    st.markdown(f"**Numbers used in this code:** `{wt['numbers_str']}`")

                    steps = wt["steps"]
                    total = len(steps)
                    limit = 40
                    initial_steps = steps[:limit]
                    remaining_steps = steps[limit:]

                    with st.container():
                        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                        for s in initial_steps:
                            indent = "&nbsp;" * s["indent_spaces"]
                            st.markdown(f'<div class="walkthrough-step">{indent}<strong>{s["prefix"]}</strong> {s["text"]}</div>', unsafe_allow_html=True)

                        if remaining_steps:
                            with st.expander(f"Show all steps ({total} total)"):
                                for s in remaining_steps:
                                    indent = "&nbsp;" * s["indent_spaces"]
                                    st.markdown(f'<div class="walkthrough-step">{indent}<strong>{s["prefix"]}</strong> {s["text"]}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                struct = parse_code_structure(st.session_state.result_code, analysis_lang)
                m = struct["metrics"]
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Inputs", m["inputs"])
                c2.metric("Decisions", m["decisions"])
                c3.metric("Loops", m["loops"])
                c4.metric("Function Calls", m["calls"])
                c5.metric("Lines of Code", m["loc"])
                st.markdown(f"**Structural Facts ({analysis_lang}):**")
                st.code(struct["facts"], language="text")

            rid = st.session_state.result_id
            with st.expander("Review and correct this explanation", expanded=(res.get("level") == "Low" or is_verified)):
                fixed = st.text_area("Correct explanation", value=res["explanation"], key=f"fixed_{rid}")
                who = st.text_input("Reviewer name (optional)", key="who")

                if st.button("Save correction"):
                    try:
                        orig = res["original"] if is_verified else res["explanation"]
                        ex.save_correction(st.session_state.result_code, orig, fixed, who)
                        st.session_state.saved_comparison = {"original": orig, "corrected": fixed, "reviewer": who}
                        set_result(ex.explain(st.session_state.result_code), st.session_state.result_code, analysis_lang)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

            comp = st.session_state.get("saved_comparison")
            if comp and is_verified:
                st.markdown("---")
                st.markdown("#### Review Comparison")
                col_orig, col_fixed = st.columns(2)
                with col_orig:
                    st.markdown("**Model said:**")
                    st.info(comp["original"] or "(none)")
                with col_fixed:
                    st.markdown(f"**Reviewer corrected** ({comp['reviewer'] or 'Reviewer'}):")
                    st.success(comp["corrected"])


# =====================================================================
# MODULE 3: EXPLANATION STUDIO
# =====================================================================
elif selected_module == "3. Explanation Studio":
    st.markdown('<div class="hero-title">Explanation Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Deep multi-perspective code comprehension across Python, Java, JavaScript, and C++.</div>', unsafe_allow_html=True)

    current_code = st.session_state.get("result_code", "")
    current_lang = st.session_state.get("result_lang", "Python")

    col_studio_in, col_studio_out = st.columns([1, 1], gap="large")

    with col_studio_in:
        st.subheader("Input Source")
        lang_pick = st.selectbox("Language", SUPPORTED_LANGUAGES, index=SUPPORTED_LANGUAGES.index(current_lang) if current_lang in SUPPORTED_LANGUAGES else 0, key="studio_lang")
        sample_pick = st.selectbox("Quick Template", ["(current input)"] + list(SAMPLES_BY_LANGUAGE.get(lang_pick, {}).keys()), key="studio_sample")

        if sample_pick != "(current input)":
            studio_code_val = SAMPLES_BY_LANGUAGE[lang_pick][sample_pick]
        else:
            studio_code_val = current_code or SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]

        studio_code = st.text_area("Source Code", value=studio_code_val, height=280, key="studio_code_box")

        MODES = [
            "Quick Explanation",
            "Detailed Explanation",
            "Line-by-Line Explanation",
            "Technical Explanation",
            "Business Explanation",
            "Execution Flow",
            "Documentation Generator"
        ]
        selected_mode = st.selectbox("Select Explanation Mode", MODES, index=1)

        run_studio = st.button("Generate Explanation", type="primary")

    with col_studio_out:
        st.subheader(f"Output — {selected_mode}")

        if run_studio or "studio_result" in st.session_state:
            if run_studio:
                with st.spinner(f"Generating {selected_mode}..."):
                    res_studio = studio.explain(studio_code, lang_pick, selected_mode, gemini_model=get_active_model())
                    st.session_state.studio_result = res_studio
            else:
                res_studio = st.session_state.studio_result

            st.markdown(f'<span class="badge-model">Source: {res_studio["source"]}</span>', unsafe_allow_html=True)

            if selected_mode == "Execution Flow":
                st.markdown("#### Visual Logic Flow (Mermaid)")
                st.markdown(f"```mermaid\n{res_studio['mermaid']}\n```")
                if res_studio.get("walkthrough") and res_studio["walkthrough"]["success"]:
                    st.markdown("#### Step Sequence")
                    for s in res_studio["walkthrough"]["steps"]:
                        st.markdown(f"- **{s['prefix']}** {s['text']}")
            elif selected_mode == "Line-by-Line Explanation":
                st.markdown("#### Statement-by-Statement Walkthrough")
                for item in res_studio.get("lines", []):
                    with st.container():
                        st.markdown(f"**Line {item['line_number']}:** `{item['code'].strip()}`")
                        st.write(f"↳ _{item['explanation']}_")
                        st.markdown("---")
            else:
                st.markdown(res_studio.get("text", "No explanation produced."))


# =====================================================================
# MODULE 4: AI CHATBOT (Legacy Assistant)
# =====================================================================
elif selected_module == "4. AI Chatbot":
    st.markdown(f'<div class="hero-title">{CHATBOT_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Ask questions about legacy code with strict factual grounding in source lines.</div>', unsafe_allow_html=True)

    if not is_api_key_configured():
        st.info("ℹ️ **API key not configured.** Add `GEMINI_API_KEY` to your `.env` file to chat with Legacy Assistant.")

    # Context scope
    active_code = st.session_state.get("result_code", "")
    active_lang = st.session_state.get("result_lang", "Python")
    repo_index: Optional[RepositoryIndex] = st.session_state.get("repo_index")

    col_ctx1, col_ctx2 = st.columns([2, 1])
    with col_ctx1:
        if active_code:
            st.success(f"Context Active: Single code snippet ({active_lang}, {len(active_code.splitlines())} lines)")
        else:
            st.info("Tip: Analyze a function in Code Analyzer or upload a repository to provide context.")
    with col_ctx2:
        if repo_index:
            st.success(f"Repository Indexed: {len(repo_index.files)} files, {len(repo_index.functions)} functions")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": f"Hello! I am **{CHATBOT_NAME}**. Ask me questions about the code currently analyzed or your uploaded repository. I will answer strictly based on the source code and cite specific line numbers."}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Quick question suggestions
    st.markdown("**Suggested Questions:**")
    sq1, sq2, sq3 = st.columns(3)
    user_prompt = None
    if sq1.button("What is the main purpose of this code?"):
        user_prompt = "What is the main purpose of this code?"
    if sq2.button("Are there any edge cases or risks?"):
        user_prompt = "What edge cases or potential risks exist in this code?"
    if sq3.button("What business rules are enforced?"):
        user_prompt = "What business rules or threshold constraints are enforced here?"

    chat_input = st.chat_input("Ask a question about the code...")
    if chat_input:
        user_prompt = chat_input

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            if not is_api_key_configured():
                fallback_msg = (
                    "**API key not configured.**\n\n"
                    "To enable interactive generative answers with Legacy Assistant, please set `GEMINI_API_KEY` in your `.env` file.\n\n"
                    "*(Rule-based note: If you have active code, you can explore the 7 explanation modes in Explanation Studio or check the step-by-step walkthrough in Code Analyzer.)*"
                )
                st.markdown(fallback_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": fallback_msg})
            else:
                with st.spinner("Analyzing code facts and formulating response..."):
                    context_snippets = []
                    if active_code:
                        context_snippets.append(f"CURRENT ANALYZER CODE ({active_lang}):\n{active_code}")

                    if repo_index:
                        retrieved = repo_index.retrieve_context_for_query(user_prompt, top_k=3)
                        for r in retrieved:
                            context_snippets.append(f"FILE: {r['file']} (Lines {r['line']}+):\n{r['snippet']}")

                    parsed_context = "\n\n".join(context_snippets) if context_snippets else "No source code loaded."

                    system_prompt = (
                        f"You are {CHATBOT_NAME}, an expert assistant for legacy codebases. "
                        "Answer user questions accurately and concisely. "
                        "Always cite specific line numbers and file paths from the provided context. "
                        "If the answer cannot be determined from the code, explicitly state: 'not found in the code'."
                    )

                    resp = call_gemini(
                        prompt=user_prompt,
                        code="",
                        parsed_facts=parsed_context,
                        model_name=get_active_model(),
                        system_instruction=system_prompt
                    )

                    if resp["success"]:
                        answer = resp["text"]
                    else:
                        answer = f"Error generating answer: {resp.get('error', 'Unknown error')}"

                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})


# =====================================================================
# MODULE 5: REPOSITORY INTELLIGENCE
# =====================================================================
elif selected_module == "5. Repository Intelligence":
    st.markdown('<div class="hero-title">Repository Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Upload a ZIP archive to safely extract, index, and explore full legacy repositories.</div>', unsafe_allow_html=True)

    repo_zip = st.file_uploader("Upload repository archive (.zip)", type=["zip"])

    if repo_zip:
        if st.button("Extract and Index Repository", type="primary"):
            with st.spinner("Safely extracting and indexing archive..."):
                ok, msg, dest = safe_extract_zip(repo_zip)
                if not ok:
                    st.error(msg)
                else:
                    st.success(msg)
                    idx = RepositoryIndex(dest)
                    idx.build()
                    st.session_state.repo_index = idx

    idx: Optional[RepositoryIndex] = st.session_state.get("repo_index")
    if not idx:
        st.info("Upload a ZIP file containing source code to view repository structure and symbol indexing.")
    else:
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Indexed Source Files", len(idx.files))
        c2.metric("Total Lines of Code", idx.total_loc)
        c3.metric("Functions / Methods", len(idx.functions))
        c4.metric("Classes / Structs", len(idx.classes))

        tab_tree, tab_symbols, tab_deps = st.tabs(["File Tree", "Symbol Search", "Dependencies & Calls"])

        with tab_tree:
            st.subheader("Repository Source Files")
            for f in idx.files:
                col_f1, col_f2 = st.columns([4, 1])
                with col_f1:
                    st.write(f"📄 **{f['rel_path']}** (`{f['language']}`, {f['loc']} LOC)")
                with col_f2:
                    if st.button("Analyze Code", key=f"btn_an_{f['rel_path']}"):
                        st.session_state.code_input = f["content"]
                        st.session_state.result_code = f["content"]
                        st.session_state.result_lang = f["language"]
                        st.session_state.nav_module = "2. Code Analyzer"
                        st.rerun()

        with tab_symbols:
            st.subheader("Symbol & Function Search")
            sym_query = st.text_input("Search function, class, or symbol name:", "")
            search_res = idx.search_symbols(sym_query)

            st.markdown(f"Found **{len(search_res['functions'])}** function(s) and **{len(search_res['classes'])}** class(es).")
            for fn in search_res["functions"][:12]:
                with st.expander(f"⚙️ {fn['name']} ({fn['file']} : Line {fn['line']})"):
                    st.caption(f"Language: {fn['language']} | Parameters: {', '.join(fn['params']) or 'none'}")
                    st.code(fn["snippet"], language=fn["language"].lower())

        with tab_deps:
            st.subheader("Dependencies & Imports")
            if not idx.dependencies:
                st.write("No external package imports detected.")
            else:
                for file_p, imps in list(idx.dependencies.items())[:15]:
                    with st.expander(f"📦 {file_p} ({len(imps)} imports)"):
                        for imp in imps:
                            st.write(f"- `{imp}`")


# =====================================================================
# MODULE 6: BUSINESS RULE DETECTIVE
# =====================================================================
elif selected_module == "6. Business Rule Detective":
    st.markdown('<div class="hero-title">Business Rule Detective</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Identify candidate business policies, constraints, and validation thresholds hidden in legacy code.</div>', unsafe_allow_html=True)

    active_code = st.session_state.get("result_code", "")
    active_lang = st.session_state.get("result_lang", "Python")

    if not active_code:
        st.info("Tip: Load or analyze code in the Code Analyzer first, or select a sample snippet below.")
        active_code = SAMPLES_BY_LANGUAGE["Python"]["Minimum balance penalty"]
        active_lang = "Python"

    st.subheader(f"Analyzing Code ({active_lang})")
    with st.expander("Show inspected source"):
        st.code(active_code, language=active_lang.lower())

    rules = detect_candidate_business_rules(active_code, active_lang)

    st.markdown(f"Discovered **{len(rules)}** candidate business rule(s):")

    if not rules:
        st.write("No distinct financial or threshold rules detected in this code.")
    else:
        for idx, rule in enumerate(rules, 1):
            with st.container():
                st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(f"### {idx}. {rule['title']}")
                st.markdown(f"**Category:** `{rule['category']}` | **Confidence:** `{rule['confidence']}` | **Reference:** {rule['line_reference']}")
                st.write(f"**Explanation:** {rule['explanation']}")
                st.caption(f"**Why Identified:** {rule['why_identified']}")

                st.code(rule["code_snippet"], language=active_lang.lower())

                col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
                with col_act1:
                    if st.button("Approve Rule", key=f"app_{rule['rule_id']}"):
                        ex.save_correction(
                            rule["code_snippet"],
                            "",
                            f"Verified Rule: {rule['title']} — {rule['explanation']}",
                            "Business Analyst",
                            status="Approved",
                            source="Business Rule Detective",
                            rule_type="Business Rule"
                        )
                        st.success("Rule approved and saved to verified knowledge base!")
                with col_act2:
                    if st.button("Reject Rule", key=f"rej_{rule['rule_id']}"):
                        ex.save_correction(
                            rule["code_snippet"],
                            "",
                            f"Rejected Rule: {rule['title']} — {rule['explanation']}",
                            "Business Analyst",
                            status="Rejected",
                            source="Business Rule Detective",
                            rule_type="Business Rule"
                        )
                        st.info("Rule marked as rejected and recorded.")
                st.markdown('</div>', unsafe_allow_html=True)


# =====================================================================
# MODULE 7: CODE IMPROVEMENT
# =====================================================================
elif selected_module == "7. Code Improvement":
    st.markdown('<div class="hero-title">Code Improvement</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Detect potential risks, inspect modernization suggestions, and compare code revisions.</div>', unsafe_allow_html=True)

    st.info(
        "ℹ️ **Engine Capabilities & Scope:**\n\n"
        "- **Python (AST Analysis)**: Detects mutable default arguments, division by zero without guards, bare `except:`, magic numbers, and redundant boolean comparisons. Proposes Python 3 f-strings and PEP 484 type annotations.\n"
        "- **Java, JavaScript, C++ (Structural & Regex Heuristics)**: Detects hardcoded magic numbers, redundant boolean comparisons, and structural diffs. Deep AST semantics are Python-only."
    )

    active_code = st.session_state.get("result_code", "") or SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]
    active_lang = st.session_state.get("result_lang", "Python")

    tab_risks, tab_modern, tab_diff = st.tabs(["Bug & Risk Scanner", "Modernization Suggestions", "Code Comparison (Diff)"])

    with tab_risks:
        st.subheader("Potential Bug & Risk Detection")
        risks = detect_code_risks(active_code, active_lang)
        st.caption("Distinguishes potential logic concerns from verified bugs using static code inspection.")

        if not risks:
            st.success("No high-severity static code risks detected in the active code.")
        else:
            for r in risks:
                with st.container():
                    st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                    st.markdown(f"**[{r['severity']} Risk] {r['category']}** (Line {r['line']})")
                    st.write(r["description"])
                    if r.get("code_snippet"):
                        st.code(r["code_snippet"], language=active_lang.lower())
                    st.info(f"💡 **Recommendation:** {r['recommendation']}")
                    st.markdown('</div>', unsafe_allow_html=True)

    with tab_modern:
        st.subheader("Modernization Suggestions")
        suggs = generate_modernization_suggestions(active_code, active_lang)

        if not suggs:
            st.info("Code already adheres to standard modern idioms.")
        else:
            for s in suggs:
                with st.expander(f"✨ {s['title']} (Line {s['line']})"):
                    st.write(s["explanation"])
                    c_old, c_new = st.columns(2)
                    with c_old:
                        st.markdown("**Original:**")
                        st.code(s["original"], language=active_lang.lower())
                    with c_new:
                        st.markdown("**Suggested:**")
                        st.code(s["suggested"], language=active_lang.lower())
                    st.caption(f"**Benefit:** {s['benefit']} | **Compatibility:** {s['compatibility_concerns']}")

    with tab_diff:
        st.subheader("Code Comparison & Diff Viewer")
        st.caption("Compare original legacy code against a proposed modernization revision.")

        c_d1, c_d2 = st.columns(2)
        with c_d1:
            diff_old = st.text_area("Original Code", value=active_code, height=200, key="diff_orig")
        with c_d2:
            default_mod = active_code.replace("round(si, 2)", "float(round(si, 2))") if "calc_si" in active_code else active_code
            diff_new = st.text_area("Proposed Modernized Code", value=default_mod, height=200, key="diff_mod")

        diff_res = compute_code_diff(diff_old, diff_new)
        m_diff1, m_diff2 = st.columns(2)
        m_diff1.metric("Lines Added", diff_res["added_lines"])
        m_diff2.metric("Lines Removed", diff_res["removed_lines"])

        st.markdown("#### Unified Diff")
        st.code(diff_res["unified_diff"], language="diff")
        st.warning(diff_res["behavioral_note"])


# =====================================================================
# MODULE 8: KNOWLEDGE BASE & MODEL REPORT
# =====================================================================
elif selected_module == "8. Knowledge Base & Model Report":
    st.markdown('<div class="hero-title">Knowledge Base & Model Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-tagline">Verified human corrections memory, review queues, and empirical AI/ML evaluations.</div>', unsafe_allow_html=True)

    tab_queue, tab_verified, tab_report, tab_about = st.tabs([
        "Review Queue", "Verified Knowledge", "Model Report", "How It Works"
    ])

    with tab_queue:
        st.subheader("Review Queue")
        st.caption("Session explanations prioritized by risk: lowest confidence explanations appear first so reviewers can fix the riskiest ones first.")

        queue = st.session_state.get("session_history", [])
        if not queue:
            st.write("No explanations generated in this session yet.")
        else:
            sorted_queue = sorted(
                queue,
                key=lambda x: (
                    x["result"].get("confidence") if x["result"].get("confidence") is not None else 1.0
                )
            )

            for item in sorted_queue:
                r = item["result"]
                conf = r.get("confidence")
                lvl = r.get("level", "Verified")
                lang = item.get("language", "Python")
                with st.container():
                    st.markdown(f"**Explanation #{item['id']} ({lang})** — Status: **{lvl}** ({f'{conf:.0%}' if conf is not None else 'Human Verified / LLM'})")
                    st.write(f"_{r['explanation']}_")
                    with st.expander("Show code"):
                        st.code(item["code"], language=lang.lower())
                    st.markdown("---")

    with tab_verified:
        st.subheader(f"Verified Knowledge Base ({ex.store.count()} saved)")
        st.caption("Corrections and candidate business rules saved in SQLite. Exact matches or >=90% similarity hits are reused automatically.")

        # Search and Filtering Controls
        c_search, c_stat, c_type = st.columns([2, 1, 1])
        with c_search:
            kb_query = st.text_input("🔍 Search entries (code, explanation, reviewer)", key="kb_query")
        with c_stat:
            kb_status = st.selectbox("Status Filter", ["All", "Approved", "Pending Review", "Rejected"], key="kb_status")
        with c_type:
            kb_type = st.selectbox("Category Filter", ["All", "Explanation Correction", "Business Rule"], key="kb_type")

        all_notes = ex.store.search(kb_query, kb_status, kb_type)

        if not all_notes:
            st.info("No matching verified knowledge records found.")
        else:
            for idx, n in enumerate(all_notes):
                c_hash = n["code_hash"]
                stat = n.get("status", "Approved")
                badge_class = "badge-verified" if stat == "Approved" else ("badge-rule" if stat == "Pending Review" else "badge-model")
                rule_type = n.get("rule_type", "Explanation Correction")
                source = n.get("source", "Human Reviewer")
                reviewer = n.get("reviewer") or "Anonymous Reviewer"
                created = n.get("created_at") or "Unknown"

                with st.container():
                    st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                    st.markdown(
                        f'<span class="{badge_class}">{stat}</span> '
                        f'<span class="badge-rule">{rule_type}</span> '
                        f'<span class="badge-model">Source: {source}</span>',
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**Verified Explanation:** {n['corrected']}")
                    if n.get("original"):
                        st.caption(f"**Original Model Text:** _{n['original']}_")
                    st.caption(f"Reviewed by **{reviewer}** on {created}")

                    with st.expander("Show Code Snippet"):
                        st.code(n["code"], language="python")

                    # Edit & Action controls
                    col_e1, col_e2, col_e3, col_e4 = st.columns([1, 1, 1, 2])
                    with col_e1:
                        if stat != "Approved":
                            if st.button("✅ Approve", key=f"app_kb_{c_hash}_{idx}"):
                                ex.store.update_status(c_hash, "Approved", reviewer="Reviewer")
                                st.rerun()
                    with col_e2:
                        if stat != "Rejected":
                            if st.button("❌ Reject", key=f"rej_kb_{c_hash}_{idx}"):
                                ex.store.update_status(c_hash, "Rejected", reviewer="Reviewer")
                                st.rerun()
                    with col_e3:
                        if st.button("🗑️ Delete", key=f"del_kb_{c_hash}_{idx}"):
                            ex.store.delete(c_hash)
                            st.rerun()

                    with st.expander("✏️ Edit Entry"):
                        edit_text = st.text_area("Corrected Explanation", value=n["corrected"], key=f"edit_txt_{c_hash}_{idx}")
                        edit_rev = st.text_input("Reviewer Name", value=reviewer, key=f"edit_rev_{c_hash}_{idx}")
                        edit_st = st.selectbox("Status", ["Approved", "Pending Review", "Rejected"],
                                               index=["Approved", "Pending Review", "Rejected"].index(stat) if stat in ["Approved", "Pending Review", "Rejected"] else 0,
                                               key=f"edit_st_{c_hash}_{idx}")
                        if st.button("Save Changes", key=f"btn_save_{c_hash}_{idx}"):
                            ex.store.edit_correction(c_hash, edit_text, edit_st, edit_rev)
                            st.success("Changes saved successfully!")
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

    with tab_report:
        st.subheader("Model Evaluation Report")
        st.caption("Empirical evaluation metrics and dataset integrity records for the fine-tuned Python model.")

        # Section 1: Dataset & Corpus Integrity
        st.markdown("### 1. Dataset & Corpus Integrity")
        st.markdown(
            "The Python evaluation model is trained and evaluated strictly on the official **CodeSearchNet** dataset (`code-search-net/code_search_net`). "
            "To prevent data leakage, splits were built with **strict zero repository overlap**."
        )
        d_c1, d_c2, d_c3, d_c4 = st.columns(4)
        d_c1.metric("Train Split", "20,000", "5,591 distinct repos")
        d_c2.metric("Validation Split", "1,000", "277 distinct repos")
        d_c3.metric("Test Split", "1,000", "286 distinct repos")
        d_c4.metric("Repo Overlap", "0", "Strict disjoint splits")

        st.markdown("---")

        # Section 2: Model Training History & Loss Curves
        train_file = os.path.join(MODEL_DIR, "training_log.json")
        st.markdown("### 2. Model Training History")
        if os.path.exists(train_file):
            with open(train_file) as f:
                tr = json.load(f)
            st.caption(f"**Architecture:** `codet5-small` (60M parameters) | **Hardware:** Apple Silicon (`{tr.get('device', 'cpu')}`) | **Training Duration:** {tr.get('minutes', 0)} min | **Best Val Loss:** {tr.get('best_val_loss')}")

            epochs_log = [entry for entry in tr.get("log", []) if "epoch" in entry]
            if epochs_log:
                col_t_table, col_t_chart = st.columns([1, 2])
                with col_t_table:
                    st.markdown("#### Epoch Loss Progression")
                    st.table([
                        {
                            "Epoch": e["epoch"],
                            "Train Loss": f"{e.get('train_loss', 0):.4f}",
                            "Val Loss": f"{e.get('val_loss', 0):.4f}"
                        }
                        for e in epochs_log
                    ])
                with col_t_chart:
                    st.markdown("#### Convergence Curve")
                    chart_data = {
                        "Epoch": [e["epoch"] for e in epochs_log],
                        "Train Loss": [e.get("train_loss") for e in epochs_log],
                        "Val Loss": [e.get("val_loss") for e in epochs_log],
                    }
                    st.line_chart(data=chart_data, x="Epoch", y=["Train Loss", "Val Loss"])
        else:
            st.info("Training log not found.")

        st.markdown("---")

        # Section 3: Test Benchmark Evaluation
        st.markdown("### 3. Test Benchmark Results (1,000 Held-Out Examples)")
        eval_file = "results/eval_results.json"
        if os.path.exists(eval_file):
            with open(eval_file) as f:
                ev = json.load(f)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                "Test BLEU",
                f"{ev.get('bleu', 0):.2f}",
                delta=f"{ev.get('bleu', 0) - ev.get('baseline_name_only_bleu', 0):+.2f} vs name-only baseline"
            )
            m2.metric(
                "Test ROUGE-L",
                f"{ev.get('rougeL', 0):.4f}",
                delta=f"{ev.get('rougeL', 0) - ev.get('baseline_name_only_rougeL', 0):+.4f} vs name-only baseline"
            )
            m3.metric("Avg Confidence", f"{ev.get('avg_confidence', 0):.1%}")
            m4.metric("Conf vs ROUGE-L Corr", f"{ev.get('confidence_vs_rougeL_correlation', 0):+.3f}")

            st.markdown("---")
            st.markdown("### 4. Confidence Calibration Buckets")
            st.caption("Validates confidence reliability: higher confidence buckets yield substantially higher explanation accuracy.")
            cl = ev.get("confidence_levels", {})
            b_data = []
            for b_name in ["High", "Medium", "Low"]:
                b_info = cl.get(b_name, {})
                b_data.append({
                    "Confidence Bucket": b_name,
                    "Cutoff Threshold": f">= {cl.get('High >=')}" if b_name == "High" else (f">= {cl.get('Medium >=')}" if b_name == "Medium" else f"< {cl.get('Medium >=')}"),
                    "Examples": b_info.get("count", 0),
                    "Share": f"{b_info.get('percentage', 0)}%",
                    "Avg ROUGE-L": f"{b_info.get('avg_rougeL', 0):.4f}",
                    "Avg Confidence": f"{b_info.get('avg_confidence', 0):.1%}" if b_info.get("avg_confidence") else "N/A"
                })
            st.table(b_data)
        else:
            st.info("Evaluation results not found.")

        st.markdown("---")

        # Section 5: Clear Separation of Models & Datasets
        st.markdown("### 5. Separation of Models & Evaluation Honesty")
        st.markdown("""
        | Model Engine | Scope & Language | Training / Foundation | Evaluation Status |
        |---|---|---|---|
        | **CodeT5-small (fine-tuned)** | Python one-sentence summaries | 20,000 CodeSearchNet Python functions | **Evaluated on 1,000 held-out test split (BLEU 5.05, ROUGE-L 0.3547)** |
        | **Python AST Engine** | Python walkthrough & static risks | Rule-based Python AST parsing | Deterministic syntax rules (zero AI hallucination) |
        | **Gemini API** | Java, JavaScript, C++, & Deep Studio | Foundation LLM (multilingual) | *LLM-based, zero-shot/few-shot, not separately benchmark-evaluated* |
        | **Structural Syntax Parsers** | Java, JavaScript, C++ flowcharts & metrics | Rule-based token & grammar analysis | Deterministic syntax rules |
        """)

    with tab_about:
        st.subheader("How It Works")
        st.markdown(r"""
        This platform decodes legacy code across multiple languages using a multi-tiered architecture:

        1. **Fine-Tuned CodeT5 for Python:**
           - Trained on official CodeSearchNet Python splits (20,000 train, 1,000 val, 1,000 test) with zero repository overlap.
           - Provides one-sentence functional summaries and geometric-mean confidence scoring.
        2. **Rule-Based Structural Analysis:**
           - AST parsing for Python and structural parsing for Java, JavaScript, and C++.
           - Produces line-by-line explanations, Mermaid flowcharts, and "At a glance" metrics directly from source code without AI hallucination.
        3. **Gemini LLM Integration:**
           - Powers in-depth explanations, technical evaluations, business rule hypotheses, and documentation generation.
           - Uses strict prompt boundaries and line-numbered source references.
        4. **Human Reviewer Correction Memory:**
           - SQLite-backed store with exact SHA-256 and fuzzy matching ($\ge 0.90$ similarity) prioritizing human knowledge over model suggestions.

        ---
        ### Note on Scope
        *Important Honest Scope:* It explains a whole **FUNCTION** in one sentence for its core AI summary. It is **not a line-by-line model**. Java, JavaScript, and C++ pipelines are LLM-based and not separately benchmark-evaluated.
        """)
