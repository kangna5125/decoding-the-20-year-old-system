# Decoding the 20 Year Old System
*Decode. Understand. Modernize. Preserve.*

An AI platform developed for the university course **Intelligent Model Design using AI** to help software engineers, reviewers, and maintainers comprehend legacy, undocumented, and complex multi-language software systems. When software runs for decades, the original developers leave, documentation becomes obsolete or lost, and modifying the code carries severe risks. This tool bridges the comprehension gap by analyzing legacy functions, breaking down control flow, recording human corrections, and extracting business rules directly from the source code.

The system performs 4 core functions:
1. **One-Sentence Plain-English Explanation with Confidence Score:** Reads an entire legacy function, explains what it does in a single plain-English sentence using a fine-tuned neural model, and calculates a geometric-mean confidence score so the reviewer knows how much to trust the generated summary.
2. **Rule-Based Step-by-Step Walkthrough:** Walks through the function body in execution order with nested steps indented and numbered, generated deterministically from the abstract syntax tree (`ast`) with zero AI hallucination.
3. **Reviewer Correction Memory (Saved & Reused):** Enables a human reviewer to inspect and correct any explanation or candidate business rule. The correction is saved into a persistent SQLite store (`corrections.db`) and automatically reused whenever identical or similar ($\ge 90\%$) code appears in the future.
4. **Repository Intelligence & AI Assistant:** Analyzes multi-file software archives (safe ZIP uploads) across multiple languages, builds an interactive source code tree with symbol indexing, and provides a context-grounded conversational assistant ("Legacy Assistant") to answer questions about the codebase.

---

## What Is Inside the Project Folder

```
code_explainer/
├── app.py                      # Main Streamlit web application entry point (8 modules)
├── common.py                   # Shared utilities (AST docstring stripping, tokenizers, device setup)
├── config.py                   # Global configuration, language support, and environment paths
├── explainer.py                # Core Python CodeExplainer engine (CodeT5 model inference + beam confidence)
├── explanation_engine.py       # Explanation Studio with 7 specialized analysis perspectives
├── languages.py                # Multi-language detection and deterministic structural parsers (Python, Java, JS, C++)
├── business_rules.py           # Candidate business rule and financial threshold detection engine
├── code_improvement.py         # Static risk detection, modernization suggestions, and code diff viewer
├── repository_service.py       # Safe ZIP archive extraction, symbol indexing, and context retriever
├── visualizer.py               # Deterministic Mermaid flowchart generator from code structure
├── walkthrough.py              # Rule-based Python AST step-by-step walkthrough generator
├── corrections.py              # SQLite human correction memory (exact SHA-256 + fuzzy difflib matching)
├── llm_service.py              # Gemini API integration, automatic model discovery, and rate-limit fallbacks
├── prepare_data.py             # CodeSearchNet dataset cleaner, deduplicator, and split builder
├── train.py                    # CodeT5 fine-tuning pipeline with validation loss checkpointing
├── evaluate.py                 # Empirical evaluation script (BLEU, ROUGE-L, confidence calibration)
├── samples.py                  # Curated legacy code examples across Python, Java, JavaScript, and C++
├── requirements.txt            # Python package dependencies with tested version baselines
├── .env.example                # Template configuration file for GEMINI_API_KEY
├── .gitignore                  # Git exclusion rules (.env, .venv, corrections.db, __pycache__, etc.)
├── README.md                   # Complete system documentation and onboarding guide
├── data/                       # CodeSearchNet dataset splits (train.jsonl, val.jsonl, test.jsonl)
├── models/                     # Trained neural checkpoints
│   └── codet5-small-csn/       # Fine-tuned CodeT5-small model, tokenizer, and training history
├── results/                    # Official evaluation reports and benchmark metrics
│   ├── eval_results.json       # Exact empirical test metrics (BLEU, ROUGE-L, calibration buckets)
│   └── samples.md              # Qualitative sample predictions and comparisons
└── tests/                      # Automated test suite (43 unit, integration, and headless app tests)
```

---

## Requirements

- **Python Version:** Built and tested with **Python 3.14.5**. Recommended compatibility range: **Python 3.10 to 3.14**.
- **Hardware (No GPU Needed):** A dedicated graphics card is **not required**.
  - **macOS:** Automatically leverages macOS GPU acceleration via Metal Performance Shaders (`mps`).
  - **Windows & Linux:** Automatically runs on standard laptop CPU cores.
- **Disk Space:** Approximately 2 GB for dependencies, datasets, and the local fine-tuned model checkpoint.

---

## Step-by-Step Setup

### Setup for macOS

Open Terminal, navigate to the project directory, and run:

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Upgrade pip to the latest version
pip install --upgrade pip

# 4. Install all dependencies from requirements.txt
pip install -r requirements.txt
```

### Setup for Windows

Open PowerShell or Command Prompt, navigate to the project directory, and run:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
.venv\Scripts\activate

# 3. Upgrade pip to the latest version
python -m pip install --upgrade pip

# 4. Install all dependencies from requirements.txt
pip install -r requirements.txt
```

---

## Gemini API Key Setup

The core Python summarization, confidence scoring, rule-based walkthroughs, static risk detection, diff viewer, and human correction memory run **100% locally and offline without an API key**. 

The conversational chatbot ("Legacy Assistant"), multi-language (Java, JavaScript, C++) analysis, and deep multi-perspective explanations utilize the Gemini API.

1. Copy the template configuration file:
   ```bash
   cp .env.example .env
   ```
2. Obtain a free API key from Google AI Studio (`https://aistudio.google.com/`).
3. Open `.env` in any text editor and paste your key after `GEMINI_API_KEY=`:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```
   *(Ensure there are no spaces around the `=` sign).*
4. **Security Notice:** Never commit, log, or share your `.env` file. It is included in `.gitignore` by default.
5. If the application is running, restart it after updating `.env`. Open **Dashboard > Settings** and click **Test connection** to verify connectivity.
6. **Behavior Without an API Key:** If no key is set, the application continues to run without crashing. Cloud-dependent features cleanly display:
   ```
   API key not configured. Add GEMINI_API_KEY to your .env file to enable Gemini features.
   ```
   and gracefully fall back to deterministic AST and syntax facts.

---

## How to Run the Application

With your virtual environment activated:

```bash
streamlit run app.py
```

Streamlit will launch local web server. Open your web browser and navigate to:
```
http://localhost:8501
```

---

## The Trained Model

The application expects the fine-tuned neural model to be present at `models/codet5-small-csn/`. This checkpoint is a fine-tuned `codet5-small` model trained specifically on docstring-stripped Python functions from CodeSearchNet.

### What to Do If the Model Is Missing

If `models/codet5-small-csn` is missing or you wish to retrain from scratch:

1. **Prepare the clean dataset splits:**
   ```bash
   python prepare_data.py --train_size 20000 --val_size 1000 --test_size 1000
   ```
   *(If parquet files exist in `~/Downloads/csn_python`, add `--local_dir ~/Downloads/csn_python`; otherwise it will download directly from Hugging Face).*

2. **Fine-tune the neural model:**
   ```bash
   python train.py --epochs 4 --batch_size 8 --lr 5e-5
   ```
   - **Training Duration:** ~50 minutes on macOS Metal GPU (`mps`) or modern GPU (~2 to 3 hours on standard multi-core CPU).
   - The training script saves the best checkpoint based on validation loss to `models/codet5-small-csn/`.

3. **Evaluate the trained model:**
   ```bash
   python evaluate.py --n 1000
   ```
   This generates the benchmark evaluation file `results/eval_results.json`.

---

## Guide to the Eight Modules & Quick First Test

### The Eight Modules

1. **Dashboard:** Overall system health, supported language capability matrix, real usage metrics, and Settings area with automatic model selection and connection testing.
2. **Code Analyzer:** Main code analysis studio. Accepts direct code pasting or file uploads across Python, Java, JavaScript, and C++. Provides one-sentence AI summaries, confidence scoring, deterministic AST walkthroughs, structural metrics, and human review memory.
3. **Explanation Studio:** Deep multi-perspective analysis featuring 7 explanation modes:
   - *Quick Explanation:* One-line functional summary (CodeT5 for Python; Gemini for Java/JS/C++).
   - *Detailed Explanation:* Full algorithmic logic narrative.
   - *Line-by-Line Explanation:* Rule-based step breakdown tied directly to source line numbers.
   - *Technical Explanation:* Algorithmic time/space complexity, data structures, and edge cases.
   - *Business Explanation:* Identification of candidate business rules and operational constraints.
   - *Execution Flow:* Interactive Mermaid flowchart visualizing code paths, branches, loops, and exits.
   - *Documentation Generator:* Production-grade docstrings/Javadoc/JSDoc/Doxygen stubs.
4. **AI Chatbot (Legacy Assistant):** Interactive conversational assistant strictly grounded in active code facts or uploaded repository symbols with line citations.
5. **Repository Intelligence:** Safe ZIP archive inspection and extraction, repository source tree viewer, language distribution analysis, dependency mapping, and symbol search.
6. **Business Rule Detective:** Automated scanning for candidate business rules, financial formulas (interest, penalties, check digits), and thresholds, with Approve/Reject reviewer actions.
7. **Code Improvement:** Static risk scanner (detects mutable defaults, division by zero, bare excepts, magic numbers), modernization suggestions (f-strings, type annotations), and unified code comparison (diff).
8. **Knowledge Base & Model Report:** Review queue prioritized by confidence, browsable and editable verified knowledge store (`corrections.db`), and empirical evaluation report with loss charts and calibration tables.

### Quick First Test

1. Navigate to **2. Code Analyzer** in the sidebar.
2. Under **Preset Samples**, select **Simple interest** (or paste any Python function):
   ```python
   def calc_si(p, r, t):
       si = (p * r * t) / 100.0
       return round(si, 2)
   ```
3. Click **"Explain Function"**.
4. Observe the results:
   - **AI Summary:** One plain-English sentence summarizing the function.
   - **Confidence Score:** Gauge display (e.g., `84% High`).
   - **Step-by-Step Walkthrough:** Rule-based sequence extracted directly from the AST.
   - **At a Glance:** Metrics showing inputs, decisions, loops, and calls.
   - **Human Review Box:** An editable text area allowing you to refine the explanation and click **"Save correction"**. Once saved, re-analyzing the same code immediately displays the green **"Verified by reviewer"** badge.

---

## How to Run the Tests

Execute the automated test suite using `pytest`:

```bash
pytest -v
```

### Test Suite Guarantees:
- **43 automated tests** cover unit logic, AST walking, syntax parsers, safe ZIP extraction, business rules, diffing, model selection fallbacks, and headless Streamlit execution.
- All tests run completely offline and finish in **under 5 seconds**.
- All tests execute strictly against isolated temporary databases (`tmp_path`), guaranteeing that the production database `corrections.db` remains untouched at **0 rows**.

---

## Dataset and Model Details

### Dataset: CodeSearchNet (Python Subset)
- **Source:** Official CodeSearchNet Python corpus hosted on Hugging Face (`code-search-net/code_search_net`).
- **Clean Disjoint Splits:**
  - **Train:** 20,000 functions across 5,591 distinct repositories.
  - **Validation:** 1,000 functions across 277 distinct repositories.
  - **Test:** 1,000 functions across 286 distinct repositories.
  - **Repository Overlap:** **Strictly 0** between any two splits (zero data contamination).
- **Integrity Processing:** Function docstrings are stripped using Python's `ast` parser before tokenization. Targets are extracted from the first sentence of clean docstrings (3–40 English words, stripped of URLs, TODOs, decorators, and doctests).

### Model Architecture & Training
- **Base Architecture:** `codet5-small` (60M parameters).
- **Hardware:** macOS Metal GPU acceleration (`mps`). Total training time: **49.7 minutes**.
- **Optimization:** AdamW optimizer (`lr=5e-5`, linear warmup), batch size 8, max source length 256, max target length 48.
- **Training Progression:**
  - Epoch 1: Train Loss `3.3029` | Val Loss `3.0960`
  - Epoch 2: Train Loss `2.8772` | Val Loss `3.0605`
  - Epoch 3: Train Loss `2.7110` | Val Loss `3.0573` *(Best validation checkpoint)*
  - Epoch 4: Train Loss `2.5994` | Val Loss `3.0672`

### Real Evaluation Results (Held-Out Test Set, 1,000 Examples)

From `results/eval_results.json`:

| Metric | Fine-Tuned Model | Baseline (Name-Only) | Improvement |
|---|---|---|---|
| **BLEU** | **5.05** | 0.07 | +4.98 (72x higher) |
| **ROUGE-L** | **0.3547** | 0.2515 | +0.1032 |
| **Average Confidence** | **52.05%** | N/A | — |
| **Confidence vs ROUGE-L Correlation** | **+0.301** | N/A | Statistically significant positive correlation |

### Confidence Calibration Buckets

| Confidence Bucket | Threshold | Example Count | Share | Avg ROUGE-L | Avg Confidence | Interpretation |
|---|---|---|---|---|---|---|
| **High** | $\ge 0.60$ | 196 | 19.6% | **0.4481** | 65.59% | Strong fidelity; highly reliable |
| **Medium** | $0.35 - 0.60$ | 786 | 78.6% | **0.3348** | 49.13% | Accurate functional summary |
| **Low** | $< 0.35$ | 18 | 1.8% | **0.2065** | 32.23% | Flagged as *Needs human review* |

---

## Troubleshooting

1. **`streamlit: command not found`:**
   - **Cause:** The virtual environment is not activated or Streamlit was installed outside the active environment.
   - **Fix:** Activate your virtual environment first (`source .venv/bin/activate` on macOS or `.venv\Scripts\activate` on Windows), then verify with `which streamlit` or `where streamlit`.

2. **API key not detected:**
   - **Cause:** `.env` file is named incorrectly (e.g., `.env.txt`) or contains formatting errors.
   - **Fix:** Ensure the file is named exactly `.env` in the root project directory. Check that the variable name is uppercase with no spaces: `GEMINI_API_KEY=your_key`. Restart the Streamlit application and check Dashboard > Settings.

3. **Slow first load on CPU:**
   - **Cause:** PyTorch and Transformers initialize weights and tokenizers in system memory upon the first invocation.
   - **Fix:** This is normal and occurs only once per session (taking ~5–10 seconds on standard laptops). Subsequent evaluations run significantly faster due to cached weights.

4. **Truncated input warning:**
   - **Cause:** The input function exceeds the model's maximum sequence length of 256 tokens.
   - **Fix:** The model automatically truncates tokens beyond the 256 limit while preserving the start of the function body. A badge appears in the UI notifying the reviewer that input truncation occurred.

---

## Honest Limitations

1. **Scope of Neural Explanation:** The neural model explains a whole **FUNCTION** in one sentence. It is **not a line-by-line model**. All line-by-line explanations and walkthroughs are generated using deterministic AST rules.
2. **Language Scope for Benchmarks:** Formal empirical benchmark evaluation (BLEU / ROUGE-L) applies strictly to **Python**. Java, JavaScript, and C++ pipelines rely on LLM zero-shot inference and structural syntax parsing and are not separately evaluated against a benchmark dataset.
3. **Static Analysis Bounds:** The bug and risk scanner performs static AST and pattern inspections; it does not execute code, prove formal correctness, or detect dynamic runtime concurrency bugs.
4. **Cloud API Privacy:** When LLM-based modes (detailed explanation, chatbot, non-Python code) are invoked, code snippets are transmitted to the Gemini API. Avoid pasting confidential keys, passwords, or proprietary source code.

---

## For AI Coding Assistants

If you are an AI coding assistant (or automated agent) tasked with running this project end-to-end, execute the following commands in order:

```bash
# 1. Verify working directory
cd /path/to/code_explainer

# 2. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run automated test suite (must report 43 passed)
pytest -v

# 5. Verify corrections database cleanliness (must output 0)
python3 -c "import sqlite3; con = sqlite3.connect('corrections.db'); print('Corrections count:', con.cursor().execute('SELECT COUNT(*) FROM corrections').fetchone()[0])"

# 6. Verify headless app execution (must output success)
python3 -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app.py', default_timeout=30).run(); assert not at.exception; print('App initialized successfully!')"

# 7. Start application for the user
streamlit run app.py
```
