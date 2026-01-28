# 🛡️ Human-in-the-Loop AI Anomaly Guard

## Introduction

This project demonstrates a **Human-in-the-Loop (HITL)** anomaly detection system for AI-generated responses. Instead of blindly trusting AI outputs or relying on another AI to judge them, the system enforces deterministic escalation logic to decide when a human must review an AI response.

The focus is on **control, explainability, and trust**, not on retraining or prompt tricks.

---

## 🎯 Project Scope

This implementation focuses on:

- **Detecting** anomalous or risky AI responses after generation.
- **Flagging** high-risk outputs for human review.
- **Demonstrating** how AI autonomy can be governed using simple, auditable rules.

> **Note:** The project intentionally does not include automated policy learning or model retraining. Human feedback collection is designed but policy updates are manual, which aligns with robust safety-first system design.

---

## ❓ Problem Statement

AI systems can produce hallucinated, unsafe, or policy-violating outputs. Reviewing every AI response manually is not scalable, while fully automated moderation lacks accountability and trust.

The challenge is to decide **when a human should intervene** — not to replace humans or add another opaque AI judge.

---

## 💡 Proposed Solution

We implement a REST API that flags anomalous AI responses using:

1. **Intent Classification**: Identifying the context of the user query (e.g., Medical, Future, Toxicity).
2. **Explicit Risk Signals**: Detecting specific patterns in responses (e.g., missing disclaimers, confident claims about the future).
3. **Policy-Driven Escalation**: Using a weighted scoring system to decide if the risk exceeds a defined threshold.

Only responses that exceed a defined risk threshold are escalated to a human reviewer. Safe responses are automatically approved.

---

## ✨ Key Features

- **Post-generation anomaly detection**: Analyzes the actual output, not just the prompt.
- **Deterministic escalation logic**: Decisions are based on a configurable `policy_config.json`.
- **HITL Integration**: A Streamlit UI allows humans to verify flagged responses.
- **Transparency**: Every decision is explainable and auditable.

---

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python
- **LLM Provider**: Groq (LLaMA 3.3 70B)
- **Frontend**: Streamlit
- **Config & Policy**: JSON

---

## 🚀 Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/rayan-rt/UCS_hackathon.git
cd UCS_hackathon

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_api_key_here
```

### 3. Running the Project

You need to run both the backend server and the frontend client.

**Terminal 1 (Backend):**

```bash
python main.py
```

**Terminal 2 (Frontend):**

```bash
streamlit run client.py
```

---

## 🛡️ Example Policy Logic

The system uses weights to calculate risk. For example:

- **Intent**: `medical` (Threshold: `0.5`)
- **Signal**: `missing_disclaimer` (Weight: `0.7`)
- **Action**: Result (`0.7`) > Threshold (`0.5`) → **FLAGGED FOR REVIEW**
