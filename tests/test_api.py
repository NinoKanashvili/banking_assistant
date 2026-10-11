
from unittest.mock import patch
from fastapi.testclient import TestClient
from langgraph.errors import GraphRecursionError

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_without_token():
    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "thread_id": "test1"
        }
    )

    assert response.status_code in [401, 403]


def test_chat_invalid_token():
    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "thread_id": "test1"
        },
        headers={
            "Authorization": "Bearer wrong_token"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@patch("main.banking_graph")
def test_chat_success(mock_graph):
    mock_graph.get_state.return_value.values = {}

    mock_graph.invoke.return_value = {
        "reply": "Your balance is 1500 GEL"
    }

    response = client.post(
        "/chat",
        json={
            "message": "What is my balance?",
            "thread_id": "test1"
        },
        headers={
            "Authorization": "Bearer demo_token_1"
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Your balance is 1500 GEL"
    }

    state = mock_graph.invoke.call_args.args[0]
    config = mock_graph.invoke.call_args.kwargs["config"]

    assert state["user_id"] == 1
    assert state["user_message"] == "What is my balance?"
    assert config["configurable"]["thread_id"] == "1_test1"
    assert config["recursion_limit"] == 10


@patch("main.banking_graph")
def test_chat_with_previous_messages(mock_graph):
    mock_graph.get_state.return_value.values = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
    }

    mock_graph.invoke.return_value = {
        "reply": "How can I help?"
    }

    response = client.post(
        "/chat",
        json={
            "message": "What is my balance?",
            "thread_id": "test2"
        },
        headers={
            "Authorization": "Bearer demo_token_2"
        }
    )

    assert response.status_code == 200

    state = mock_graph.invoke.call_args.args[0]

    assert len(state["messages"]) == 3
    assert state["messages"][0]["content"] == "Hello"
    assert state["messages"][1]["content"] == "Hi!"
    assert state["messages"][2] == {
        "role": "user",
        "content": "What is my balance?"
    }

    assert state["user_id"] == 2


@patch("main.banking_graph")
def test_chat_recursion_error(mock_graph):
    mock_graph.get_state.return_value.values = {}

    mock_graph.invoke.side_effect = GraphRecursionError(
        "Recursion limit reached"
    )

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "thread_id": "test3"
        },
        headers={
            "Authorization": "Bearer demo_token_3"
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Sorry, I couldn't complete that request."
    }
