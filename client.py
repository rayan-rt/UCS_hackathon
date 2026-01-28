import requests
import streamlit as st

st.title("🛡️ HITL Anomaly Guard")

with st.sidebar:
    groq_key = st.text_input("Groq API Key", type="password")
    backend_url = "http://localhost:8000"

# 1. Initialize the state at the top of your script
if "show_feedback_form" not in st.session_state:
    st.session_state.show_feedback_form = False

user_input = st.text_input("Ask the AI anything:")

if st.button("Send") and user_input:
    if not groq_key:
        st.error("Please provide an API key!")
    else:
        try:
            res = requests.post(
                f"{backend_url}/ask", json={"prompt": user_input, "api_key": groq_key}
            )
            res.raise_for_status()
            res = res.json()

            if res["status"] == "flagged":
                st.warning("⚠️ ANOMALY DETECTED")
                st.write("**Signals:**", res["data"]["signals"])
                st.write("**Risk score:**", res["data"]["risk_score"])
                st.write("**AI Response:**")
                st.write(res["data"]["response"])
                st.info("Human review required")
            else:
                st.success("✅ AI Response Verified")
                st.write(res["data"]["response"])
        except Exception as e:
            st.error(f"Error: {e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Correct"):
            # Log successful interaction
            st.session_state.show_feedback_form = False
    with col2:
        if st.button("👎 Incorrect"):
            st.session_state.show_feedback_form = True

    if st.session_state.show_feedback_form:
        with st.container():
            st.info("Human Review: Please explain the issue.")
            # Use a key to ensure this input's value is tracked
            reason = st.text_input("What went wrong?", key="feedback_reason")

            if st.button("Submit Feedback"):
                if reason:
                    # Send feedback to FastAPI
                    requests.post(
                        f"{backend_url}/feedback",
                        json={
                            "query": user_input,
                            "response": res["data"]["response"],
                            "human_decision": "incorrect",
                            "notes": reason,
                            "signal": res["data"]["signals"][0]
                            if res["data"]["signals"]
                            else "general",
                        },
                    )
                    st.success("Feedback recorded! Engineers will review this case.")
                    # 4. Reset the form state after successful submission
                    st.session_state.show_feedback_form = False
                    st.rerun()  # Refresh to clear the UI
