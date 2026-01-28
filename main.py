import json

from fastapi import FastAPI, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel

# ---------------------------
# Layer 2: Signal Detection
# ---------------------------


def detect_signals(query: str, response: str) -> list[str]:
    signals = []

    q = query.lower()
    r = response.lower()

    # Future claims
    if "will" in q and "who will win" in q and "2026" in q:
        signals.append("future_claim")

    # Future claims
    if "will" in r and "2026" in r:
        signals.append("future_claim")

    # Medical domain
    medical_keywords = ["cancer", "treatment", "diagnosis", "medicine"]
    if any(k in q for k in medical_keywords):
        signals.append("medical_domain")

        if "consult" not in r:
            signals.append("missing_disclaimer")

    # Toxicity
    toxic_keywords = ["hate", "kill", "stupid", "attack", "violence"]
    if any(k in q for k in toxic_keywords) or any(k in r for k in toxic_keywords):
        signals.append("toxic_tone")

    # Hallucination (Heuristic)
    if any(
        phrase in r
        for phrase in ["i think", "maybe", "hypothetically", "i am not sure but"]
    ):
        signals.append("potential_hallucination")

    return signals


# ---------------------------
# Layer 3: Policy Memory
# ---------------------------


def load_policy():
    try:
        with open("policy_config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="policy_config.json not found")


def should_escalate(intent: str, signals: list[str]) -> tuple[bool, float]:
    policy = load_policy()

    risk = sum(policy["signal_weights"].get(signal, 0) for signal in signals)

    threshold = policy["thresholds"].get(intent, 1.0)
    return risk >= threshold, round(risk, 2)


# ---------------------------
# Layer 1: LLM Call
# ---------------------------


def call_llm(api_key: str, query: str) -> str:
    llm = ChatGroq(api_key=api_key, model="llama-3.3-70b-versatile")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a safe assistant. Reply to user query briefly!",
            ),
            ("human", "{query}"),
        ]
    )

    chain = prompt | llm
    return chain.invoke({"query": query}).content


# ---------------------------
# FastAPI App
# ---------------------------

app = FastAPI(title="HITL Anomaly Guard API")


class QueryRequest(BaseModel):
    prompt: str
    api_key: str


class FeedbackRequest(BaseModel):
    query: str
    response: str
    human_decision: str
    notes: str
    signal: str = "general"


@app.post("/ask")
async def ask_llm(req: QueryRequest):
    response = call_llm(req.api_key, req.prompt)

    prompt_lower = req.prompt.lower()
    if any(k in prompt_lower for k in ["cancer", "treatment", "diagnosis", "medicine"]):
        intent = "medical"
    elif any(k in prompt_lower for k in ["2026", "future", "predict", "will happen"]):
        intent = "future"
    elif any(k in prompt_lower for k in ["hate", "kill", "stupid", "attack"]):
        intent = "toxicity"
    elif any(k in prompt_lower for k in ["fact check", "is it true", "real or fake"]):
        intent = "hallucination"
    else:
        intent = "general"

    signals = detect_signals(req.prompt, response)
    escalate, risk = should_escalate(intent, signals)

    result = {
        "query": req.prompt,
        "response": response,
        "intent": intent,
        "signals": signals,
        "risk_score": risk,
    }

    if escalate:
        return {"status": "flagged", "data": result}

    return {"status": "approved", "data": result}


@app.post("/feedback")
async def save_feedback(req: FeedbackRequest):
    new_feedback = {
        "query": req.query,
        "response": req.response,
        "human_decision": req.human_decision,
        "notes": req.notes,
        "signal": req.signal,
    }

    try:
        try:
            with open("human_feedback.json", "r") as f:
                feedbacks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            feedbacks = []

        feedbacks.append(new_feedback)

        with open("human_feedback.json", "w") as f:
            json.dump(feedbacks, f, indent=4)

        return {"message": "Feedback recorded for human review."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save feedback: {str(e)}"
        )


# ---------------------------
# Uvicorn entrypoint
# ---------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
