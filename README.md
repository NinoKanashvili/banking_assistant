# AI Banking Assistant

An AI-powered banking assistant built with **Python, FastAPI, LangGraph, Ollama, SQLite, and Streamlit**.

The application allows users to interact with fictional banking data through natural language. It uses a locally running language model to select banking tools and generate responses.

## Features

- Conversational AI interface
- Bank balance inquiries
- Transaction history retrieval
- Expense calculations with optional category filtering
- LangGraph-based tool calling
- Conversation context managed using thread IDs
- Separate conversation histories for demo users
- SQLite-based banking data and chat history
- Demo token authentication
- Streamlit web interface
- Automated tests with pytest

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| FastAPI | REST API |
| LangGraph | AI workflow orchestration and conversation state |
| Ollama (Llama 3.2 3B) | Local language model |
| SQLite | Banking data and chat history |
| Streamlit | Web interface |
| HTTPX | HTTP requests |
| Pytest | Automated testing |

## Architecture

The application follows this workflow:

1. The user submits a message through the Streamlit interface.
2. Streamlit sends an authenticated request to the FastAPI backend.
3. FastAPI identifies the demo user and conversation thread.
4. LangGraph retrieves the conversation state.
5. The AI assistant determines whether a banking tool is needed.
6. The selected tool queries the SQLite banking database.
7. The assistant generates a response.
8. The response is returned to Streamlit and displayed to the user.

## Banking Tools

**`get_balance(user_id)`**

Retrieves the user's account balance.

**`get_transactions(user_id)`**

Returns the user's transactions, ordered by date.

**`calculate_expenses(user_id, category=None)`**

Calculates total expenses, optionally filtered by category.

The assistant also includes a fallback mechanism for unsupported banking requests.

## API Endpoints

### GET `/health`

Checks whether the API is running.

Example response:

```json
{
  "status": "ok"
}
```

### POST `/chat`

Processes a banking-related user message.

Requires a demo Bearer token.

Example request:

```json
{
  "message": "What is my balance?",
  "thread_id": "conversation-1"
}
```

Example response:

```json
{
  "reply": "Your balance is 1500 GEL."
}
```

## Authentication

The application includes three fictional demo users, authenticated using predefined Bearer tokens.

This authentication mechanism is intended for demonstration purposes only and is not suitable for production use.

## Conversation Memory

LangGraph uses `InMemorySaver` to manage conversation state.

Each conversation is identified using a combination of the user ID and thread ID, allowing multiple independent conversations.

The Streamlit interface stores conversation messages in SQLite so users can reopen previous chats.

**Limitation:** LangGraph conversation state is stored in memory and is lost when the backend restarts. Previously saved messages remain visible in Streamlit, but they are not automatically restored to the AI's context.

## Running the Project

### Prerequisites

- Python
- Ollama
- Llama 3.2 3B model

### 1. Clone the repository

```bash
git clone <repository-url>
cd ai-banking-assistant
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare Ollama

Install Ollama and download the model:

```bash
ollama pull llama3.2:3b
```

Ensure the Ollama service is running.

### 5. Start FastAPI

```bash
uvicorn main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

### 6. Start Streamlit

Open another terminal, activate the virtual environment, and run:

```bash
streamlit run streamlit/streamlit_app.py
```

Open the local URL displayed by Streamlit.

**Note:** The application requires a properly initialized SQLite banking database containing the expected accounts and transactions tables.

## Testing

The project includes automated tests for banking operations and API functionality.

Run all tests:

```bash
python -m pytest -v
```

The current test suite includes:

- 9 banking tool tests
- 6 API tests

The API tests use mocking to avoid making real language model calls.

## Known Limitations

- The local language model may occasionally select an inappropriate tool or generate an inaccurate response.
- LangGraph conversation memory is not persistent across backend restarts.
- Authentication uses predefined demo tokens rather than a production authentication system.
- The application uses fictional banking data and does not connect to real banking services.

## Disclaimer

This project is developed for educational purposes only.

It does not access real bank accounts, process actual financial transactions, or provide production banking services.