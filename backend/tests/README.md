# CityAgent Testing & Evaluation Infrastructure

This directory contains the complete test and evaluation suite for **CityAgent**, a multi-agent Retrieval-Augmented Generation (RAG) system for municipal asset management.

The suite combines **fast, offline $0-cost deterministic tests** (unit tools, auth, vectorization, local fixtures) and **Google ADK Agent Evaluation suites** (LLM reasoning, tool trajectories, ROUGE-1 response matching).

---

## Directory & Test Suite Structure

```
backend/tests/
├── conftest.py                          # Fixtures, event loop setup, and automatic logfile summary hook
├── test_harness.py                      # Deterministic offline mock runner & live ADK evaluation harness
├── offline_tool_tests/                  # Pure Python unit tests for spreadsheet & PDF tools ($0 cost)
│   └── test_spreadsheet_tools.py
├── vectorize_tests/                     # Vectorization pipeline tests (chunking, headers, PGVector)
│   ├── test_vectorize_pipeline.py
│   └── fixtures/sample_roads.csv
├── auth_tests/                          # FastAPI authentication & authorization middleware tests
│   └── test_auth.py
├── metamorphic_tests/                   # Metamorphic Relations (MR1-MR7)
│   ├── test_metamorphic.py
│   ├── metamorphic_evalset.json
│   └── test_config.json
├── hallucination_tests/                 # Hallucination & Grounding Guardrails (HG1-HG4)
│   ├── test_hallucination.py
│   ├── hallucination_evalset.json
│   └── test_config.json
├── numeric_precision_tests/             # Numeric Precision & Aggregations (NP1-NP3)
│   ├── test_numeric_precision.py
│   ├── numeric_precision_evalset.json
│   └── test_config.json
├── baseline_comparison_tests/           # RAG vs. Un-augmented LLM Baseline Comparison (BC1-BC4)
│   ├── test_baseline_comparison.py
│   ├── baseline_comparison_evalset.json
│   └── test_config.json
├── orchestrator_tests/                  # Orchestrator scoping & intent expansion (OC1-OC5)
│   ├── test_orchestrator.py
│   ├── orches_evalset.json
│   └── test_config.json
├── reasoner_tests/                      # Reasoner evidence synthesis & guardrails (RH1-RH4)
│   ├── test_reasoner.py
│   ├── reasoner_evalset.json
│   └── test_config.json
└── root_tests/                          # Full multi-agent pipeline flow
    ├── root_test.py
    ├── root_evalset.json
    └── test_config.json
```

---

## Test Modes & Running Instructions

### Mode 1: Fast $0-Cost Offline Suite (Default)
By default, running `pytest tests/` executes **100 individual parameterized tests** offline against local fixtures. It makes **zero network calls** to cloud APIs and runs in ~1–2 seconds at **$0.00 CAD cost**.

```bash
# Run all 100 offline tests
pytest tests/ --disable-warnings

# Run a specific offline module
pytest tests/metamorphic_tests/ --disable-warnings
pytest tests/numeric_precision_tests/ --disable-warnings
pytest tests/offline_tool_tests/ --disable-warnings
```

### Mode 2: Live LLM Agent Evaluation (`LIVE_LLM=1`)
To evaluate live agent reasoning, tool selection trajectories, and response quality against live LLM APIs:

```bash
# Run live ADK evaluation against configured LLM provider (Azure / OpenAI / Gemini)
LIVE_LLM=1 pytest tests/ --disable-warnings

# Run a specific live suite
LIVE_LLM=1 pytest tests/baseline_comparison_tests/ --disable-warnings
LIVE_LLM=1 pytest tests/hallucination_tests/ --disable-warnings
```

### Mode 3: Zero-Cost Live LLM Evaluation (Ollama Local Model)
To run live multi-agent evaluations without incurring cloud API costs:

1. Ensure [Ollama](https://ollama.com) is running locally.
2. In `backend/.env`, set:
   ```env
   AI_API_PROVIDER=OLLAMA
   OLLAMA_API_BASE=http://localhost:11434
   ```
3. Run the live suite:
   ```bash
   LIVE_LLM=1 pytest tests/ --disable-warnings
   ```

---

## Logfiles & Error Summaries

Tests write execution logs to `backend/test_run.log` automatically via [pytest.ini](file:///home/neel/github/CityAgent/backend/pytest.ini).

A custom terminal summary hook in [conftest.py](file:///home/neel/github/CityAgent/backend/tests/conftest.py) appends a formatted **`TEST FAILURES & ERRORS SUMMARY`** section at the very end of the logfile whenever any test fails or errors out.

To specify a custom logfile name:
```bash
pytest tests/ --log-file=custom_test_run.log -v
```

---

## Evaluation Categories

| Category | Description | Key Focus |
|----------|-------------|-----------|
| **Metamorphic (MR1–MR7)** | Semantic query transformations | Street suffix invariance (`CR` $\leftrightarrow$ `CRESCENT`), acronyms (`PQI`), word-order changes, noise injection, prompt injection defense |
| **Hallucination (HG1–HG4)** | Grounding & refusal guardrails | Refusal on missing wards (`Ward 99`) and non-existent streets, exact numeric spot checks |
| **Numeric Precision (NP1–NP3)** | Deterministic computations | Exact mean, min, max, range filter calculations, schema inspection protocol enforcement |
| **Baseline Comparison (BC1–BC4)** | RAG vs. Vanilla LLM | Head-to-head proof that RAG retrieval outperforms generic chatbot answers |
| **Orchestrator (OC1–OC5)** | Query routing & intent expansion | Translating intent to keywords, out-of-scope refusal |
| **Reasoner (RH1–RH4)** | Context-bounded synthesis | Adherence to retrieved context, source citation array validation |

---

## ADK Evaluation Architecture

The ADK evaluation framework operates on three components:

1. **`AgentEvaluator`**: Harness that automates test execution, manages a User Simulator, and calculates metrics.
2. **EvalSet (`*.test.json`)**: Golden dataset containing user queries, expected tool trajectories, and ideal reference responses.
3. **EvalConfig (`test_config.json`)**: Grading rubric defining thresholds:
   - `tool_trajectory_avg_score`: Validates tool selection sequence.
   - `response_match_score`: Measures lexical (ROUGE-1) similarity against reference answers.

---

## References & Documentation
- Google ADK Evaluation Guide: https://google.github.io/adk-docs/evaluate/
- CityAgent Architectural Paper: [report.pdf](file:///home/neel/github/CityAgent/report.pdf)
