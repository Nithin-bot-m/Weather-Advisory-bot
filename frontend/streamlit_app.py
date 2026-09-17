import streamlit as st

st.set_page_config(
    page_title="Weather Advisory Support Bot",
    page_icon="🌤️",
    layout="centered",
)

st.title("🌤️ Weather Advisory Support Bot")
st.caption("Step 1 Scaffold — Foundation & Environment Setup")

st.markdown("""
Welcome to the Weather Advisory Support Bot setup!
> **Note:** Chatbot workflow and SOP engine will be connected in the next implementation step.
""")

# Display placeholder chat UI
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your Weather Advisory Support Bot (Setup Mode). Chatbot functionality will be live in Step 2."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type a message (e.g. Weather in Bhopal)...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    response = f"Echo (Setup Mode): Step 1 completed. You said: '{user_input}'"
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
