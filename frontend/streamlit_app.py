"""
Streamlit Chatbot Interface for Weather Advisory Support Bot.
"""
import os
import uuid
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").strip().rstrip("/")

# Page Configuration
st.set_page_config(
    page_title="Weather Advisory Support Bot",
    page_icon="🌤️",
    layout="centered",
)

st.title("🌤️ Weather Advisory Support Bot")
st.markdown(
    "Ask whether an outdoor activity is appropriate based on live weather conditions and configured safety SOPs."
)

# Initialize Streamlit Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Controls
with st.sidebar:
    st.header("Session Management")
    st.write(f"**Session ID:** `{st.session_state.session_id[:8]}...`")

    if st.button("New Chat", type="secondary", use_container_width=True):
        current_session_id = st.session_state.session_id
        # Call backend reset endpoint
        try:
            requests.post(f"{BACKEND_URL}/session/{current_session_id}/reset", timeout=3)
        except Exception:
            pass  # Fail gracefully if backend is offline

        # Reset session ID and message history
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        "**System Information**\n"
        "- **Weather Data**: Open-Meteo API\n"
        "- **Policy Engine**: 100% Deterministic\n"
        "- **Orchestration**: LangGraph Workflow\n"
    )

# Helper function to render metadata
def render_metadata(meta: dict):
    selected_sop = meta.get("selected_sop")
    evaluated_sop = meta.get("evaluated_sop")
    weather = meta.get("weather")
    error = meta.get("error")

    if error:
        st.warning(f"⚠️ **Notice**: {error}")
    elif selected_sop:
        sop_id = selected_sop.get("id", "N/A")
        sop_name = selected_sop.get("name", "N/A")
        severity = str(selected_sop.get("severity", "N/A")).upper()

        with st.expander(f"📋 **Matched Hazard Policy**: {sop_id} — {sop_name} ({severity})"):
            st.markdown(f"**Category:** `{selected_sop.get('category', 'N/A')}`")
            st.markdown(f"**Configured Advice:** {selected_sop.get('advice', 'N/A')}")
            
            if weather:
                st.markdown("**Live Weather Facts:**")
                cols = st.columns(3)
                cols[0].metric("Temperature", f"{weather.get('temperature_2m')} °C")
                cols[1].metric("Wind Speed", f"{weather.get('wind_speed_10m')} km/h")
                cols[2].metric("Precipitation Prob", f"{weather.get('precipitation_probability')} %")
    elif evaluated_sop:
        sop_id = evaluated_sop.get("id", "N/A")
        sop_name = evaluated_sop.get("name", "N/A")
        severity = str(evaluated_sop.get("severity", "N/A")).upper()

        with st.expander(f"📋 **Evaluated Policy (Safe Parameters)**: {sop_id} — {sop_name} ({severity})"):
            st.markdown(f"**Category:** `{evaluated_sop.get('category', 'N/A')}`")
            st.markdown(f"**Configured Policy Advice:** {evaluated_sop.get('advice', 'N/A')}")
            st.markdown("✅ *Current weather conditions do not breach warning thresholds.*")

            if weather:
                st.markdown("**Live Weather Facts:**")
                cols = st.columns(3)
                cols[0].metric("Temperature", f"{weather.get('temperature_2m')} °C")
                cols[1].metric("Wind Speed", f"{weather.get('wind_speed_10m')} km/h")
                cols[2].metric("Precipitation Prob", f"{weather.get('precipitation_probability')} %")
    else:
        st.info("ℹ️ **No applicable SOP policy found for this activity/weather.**")


# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Render metadata / SOP Traceability for assistant messages
        if msg["role"] == "assistant" and "metadata" in msg:
            render_metadata(msg["metadata"])

# Chat Input & Form Submission
user_input = st.chat_input("Ask about outdoor activity safety (e.g., Can I cycle in Bhopal today?)")

if user_input:
    # 1. Add user message to UI state
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Call Backend API
    with st.chat_message("assistant"):
        with st.spinner("Checking live weather and applicable SOP..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "session_id": st.session_state.session_id,
                        "message": user_input,
                    },
                    timeout=30,
                )
            except requests.exceptions.ConnectionError:
                st.error("Unable to connect to the Weather Advisory backend. Please make sure FastAPI is running.")
                st.stop()
            except Exception as exc:
                st.error(f"Error communicating with backend service: {exc}")
                st.stop()

        if response.status_code == 200:
            data = response.json()
            bot_reply = data.get("response", "No response received.")
            st.markdown(bot_reply)

            selected_sop = data.get("selected_sop")
            evaluated_sop = data.get("evaluated_sop")
            weather = data.get("weather")
            error = data.get("error")

            meta_dict = {
                "selected_sop": selected_sop,
                "evaluated_sop": evaluated_sop,
                "weather": weather,
                "error": error,
            }
            render_metadata(meta_dict)

            # Save assistant message with metadata
            st.session_state.messages.append({
                "role": "assistant",
                "content": bot_reply,
                "metadata": meta_dict,
            })
        else:
            st.error(f"Backend returned error status {response.status_code}: {response.text}")
