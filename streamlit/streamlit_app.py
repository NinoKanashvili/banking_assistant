
import streamlit as st
import httpx
import uuid

from streamlit_storage import (
    init_db,
    create_conversation,
    get_conversations,
    save_message,
    get_messages
)

API_URL = "http://127.0.0.1:8000/chat"

USER_TOKENS = {
    "User 1": "demo_token_1",
    "User 2": "demo_token_2",
    "User 3": "demo_token_3"
}

USER_IDS = {
    "User 1": 1,
    "User 2": 2,
    "User 3": 3
}

st.set_page_config(
    page_title="AI Banking Assistant",
    page_icon="🏦",
    layout="centered"
)

init_db()

if "active_chats" not in st.session_state:
    st.session_state.active_chats = {}

# Sidebar
with st.sidebar:
    st.title("🏦 Banking Assistant")

    selected_user = st.selectbox(
        "Select demo user",
        list(USER_TOKENS.keys())
    )

    user_id = USER_IDS[selected_user]
    token = USER_TOKENS[selected_user]

    st.divider()

    if st.button(
        "➕ New Conversation",
        use_container_width=True
    ):
        st.session_state.active_chats[selected_user] = None
        st.rerun()

    st.subheader("Previous chats")

    conversations = get_conversations(user_id)

    for conversation in conversations:
        if st.button(
            conversation["title"],
            key=conversation["thread_id"],
            use_container_width=True
        ):
            st.session_state.active_chats[selected_user] = (
                conversation["thread_id"]
            )
            st.rerun()

    st.divider()

    st.caption(
        "Demo application using fictional banking data."
    )

# Current conversation
thread_id = st.session_state.active_chats.get(selected_user)

st.title("AI Banking Assistant")
st.caption(f"Currently chatting as {selected_user}")

st.write(
    "Ask about your balance, transactions, or expenses."
)

# Display previous messages
if thread_id:
    messages = get_messages(thread_id)

    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Chat input
prompt = st.chat_input("Ask a banking question...")

if prompt:

    # Create a conversation when first message is sent
    if thread_id is None:
        thread_id = str(uuid.uuid4())

        title = prompt[:35]
        if len(prompt) > 35:
            title += "..."

        create_conversation(
            thread_id,
            user_id,
            title
        )

        st.session_state.active_chats[selected_user] = thread_id

    save_message(thread_id, "user", prompt)

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = httpx.post(
                    API_URL,
                    json={
                        "message": prompt,
                        "thread_id": thread_id
                    },
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                    timeout=120
                )

                response.raise_for_status()

                reply = response.json()["reply"]

            except httpx.TimeoutException:
                reply = "The request took too long. Please try again."

            except httpx.HTTPStatusError:
                reply = "The banking service returned an error."

            except httpx.RequestError:
                reply = "Cannot connect to the banking service."

            except (ValueError, KeyError, TypeError):
                reply = "The banking service returned an invalid response."

        st.write(reply)

    save_message(thread_id, "assistant", reply)

    st.rerun()
