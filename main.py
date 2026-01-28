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
    if "who won" in q and "2026" in q:
        signals.append("future_claim")

    # Medical domain
    medical_keywords = ["cancer", "treatment", "diagnosis", "medicine"]
    if any(k in q for k in medical_keywords):
        signals.append("medical_domain")

        if "consult a professional" not in r:
            signals.append("missing_disclaimer")

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


def get_learned_lessons():
    try:
        with open("human_feedback.json", "r") as f:
            feedbacks = json.load(f)
            # Only use corrections to teach the model what NOT to do
            lessons = [
                f"User: {fb['query']}\nAvoid this mistake: {fb['notes']}"
                for fb in feedbacks
                if fb["human_decision"] == "incorrect"
            ]
            return "\n".join(lessons[-3:])  # Only last 3 to save tokens
    except FileNotFoundError:
        return ""


# ---------------------------
# Layer 1: LLM Call
# ---------------------------


def call_llm(api_key: str, query: str) -> str:
    # lessons = get_learned_lessons()

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
    # Optional: if you want to keep the 'signal' logic
    signal: str = "general"


@app.post("/ask")
async def ask_llm(req: QueryRequest):
    response = call_llm(req.api_key, req.prompt)

    intent = (
        "medical"
        if any(k in req.prompt.lower() for k in ["cancer", "treatment", "diagnosis"])
        else "general"
    )

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
async def update_policy(req: FeedbackRequest):
    policy = load_policy()

    # Logic: If human says it's safe, reduce the risk weight of that signal
    if req.human_decision == "correct" and req.signal in policy["signal_weights"]:
        policy["signal_weights"][req.signal] *= 0.5  # "Learning" to be less strict

    with open("policy_config.json", "w") as f:
        json.dump(policy, f)

    return {"message": "System performance improved based on feedback."}


# ---------------------------
# Uvicorn entrypoint
# ---------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
