from fastapi import FastAPI
from pydantic import BaseModel
from graph import banking_graph
from langgraph.errors import GraphRecursionError

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException

app = FastAPI()

security = HTTPBearer()

demo_tokens = {
    "demo_token_1": 1,
    "demo_token_2": 2,
    "demo_token_3": 3
}


class ChatRequest(BaseModel):
    message: str
    thread_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    if token not in demo_tokens:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user_id = demo_tokens[token]

    config = {
        "configurable": {
            "thread_id": f"{user_id}_{request.thread_id}"
        },
        "recursion_limit": 10
    }

    previous_state = banking_graph.get_state(config)
    previous_messages = previous_state.values.get("messages", [])

    state = {
        "user_message": request.message,
        "user_id": user_id,
        "tool_calls": [],
        "reply": "",
        "messages": previous_messages + [
             {"role": "user", "content": request.message}
        ]
    }
    try:
        result = banking_graph.invoke(
            state,
            config=config
        )
    except GraphRecursionError:
        return {"reply": "Sorry, I couldn't complete that request."}

    return {"reply": result["reply"]}


