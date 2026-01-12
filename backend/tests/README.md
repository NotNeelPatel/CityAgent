# Google ADK Agent Evaluation Guide

To run in backend do `pytest tests/` to run all tests. What follows is how this all works. 

## 🏗 Core Architecture

The evaluation system is built on three pillars:
### 1. AgentEvaluator (The Engine)
A Python utility that automates the testing process. It:
- Initializes the agent
- Manages a **User Simulator** to mimic human interaction
- Orchestrates multiple test runs to account for **LLM non-determinism**

### 2. EvalSet (`*.test.json`)
Our **Golden Dataset**.  
These files contain:
- User queries
- Expected tool trajectories
- Ideal reference responses

### 3. EvalConfig (`test_config.json`)
The **grading rubric**.  
Defines:
- Metrics to be measured
- Minimum thresholds required for a **Pass**


The `AgentEvaluator` follows a **convention-over-configuration** model.

- Recursively scans for `*.test.json` files
- Automatically applies the `test_config.json` found in the same directory

---

## Evaluation Metrics & Thresholds

We measure success across several dimensions. Thresholds range from 0.0 (fail) to 1.0 (perfect).

| Metric | Description |
|--------|-------------|
| **Tool Trajectory** | Validates if the agent called the correct tools in the right sequence with the right arguments. |
| **Response Match** | Uses ROUGE-1 or similar text-matching to compare the agent's answer to a reference. | 
| **Response Evaluation(haven't used this but might)** | An LLM-based "Critic" that judges the semantic quality and accuracy of the response. | 


## Documentation used 
https://codelabs.developers.google.com/adk-eval/instructions#0
https://google.github.io/adk-docs/evaluate/


