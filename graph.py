"""
Banking assistant built as a LangGraph agent.

Flow:
    START -> assistant -> (tool calls?) -> tools -> assistant -> ... -> END

The "assistant" node asks a local LLM (Ollama) what to do next.
If the model requests tools, the "tools" node runs them and feeds the
results back to the model, which then writes the final answer.
This assistant -> tools -> assistant loop is what makes it an agent.
"""

import json
from typing import TypedDict

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from banking_tools import get_balance, get_transactions, calculate_expenses

# How many recent messages are sent to the model on each call.
# Small local models get confused by long histories, so we send a window
# instead of the full conversation (the full history stays in the state).
MAX_HISTORY = 12


class BankingState(TypedDict):
    """Shared state that every node in the graph reads and updates."""

    user_message: str   # latest message from the user
    user_id: int        # comes from authentication, NEVER from the model
    tool_calls: list    # tool calls requested by the model in the current step
    reply: str          # final text answer returned to the API
    messages: list      # full conversation history (user / assistant / tool)


def assistant_node(state: BankingState):
    """
    Ask the LLM what to do next.

    Returns either:
      - tool calls (the graph then routes to the "tools" node), or
      - a final text reply (the graph then ends).
    """

    # The prompt sorts every message into one of four cases so that a small
    # model knows when to call a tool and when to answer in plain text.
    SYSTEM_PROMPT = """You are a banking assistant for a bank in Georgia.

        Every user message falls into exactly one of four cases:

        CASE A: Banking question that get_balance, get_transactions or
        calculate_expenses can answer.
        -> Call that tool, then answer using its result.

        CASE B: Banking question or action that those tools CANNOT handle
        (money transfers, payments, cards, loans, fees, interest rates,
        opening accounts, etc.).
        -> Call unsupported_banking_request, then answer using its result.

        CASE C: Greetings, thanks, goodbyes, polite conversation.
        -> Do NOT call any tool. Reply briefly and politely.
        -> Never mention balances or transactions unless asked.

        CASE D: Anything not related to banking.
        -> Do NOT call any tool. Reply: "I can only help with banking questions."

        Rules:
        1. After receiving tool results, use them to answer the user.
        2. Do not repeat a tool call if its result is already available.
        3. Never invent tools, transactions, balances, or capabilities.
        4. All monetary amounts are in GEL, never USD.
        5. Reply in the same language the user writes in.
        6. Never do arithmetic or comparisons yourself.
        7. The account balance must come ONLY from get_balance.
        8. If a tool returns an error, say the information is unavailable. Never guess.
        9. Classify ONLY the CURRENT user message. Ignore earlier banking
        requests unless the user repeats them.

        Examples:
        User: "hello" -> CASE C, no tool, reply: "Hello! How can I help you with your banking?"
        User: "thanks" -> CASE C, no tool, reply: "You're welcome!"
        User: "What is my balance?" -> CASE A, call get_balance
        User: "Show my transactions" -> CASE A, call get_transactions
        User: "How much did I spend on food?" -> CASE A, call calculate_expenses
        User: "How can I send money?" -> CASE B, call unsupported_banking_request
        User: "Can you block my card?" -> CASE B, call unsupported_banking_request
        User: "What is a car?" -> CASE D, reply: "I can only help with banking questions."
        User: "Who won the football match?" -> CASE D, reply: "I can only help with banking questions."
        """

    # Send only the most recent messages to the model.
    history = state["messages"][-MAX_HISTORY:]

    # The window must start with a user message. Cutting in the middle of a
    # tool exchange would leave a "tool" message without its matching call.
    for i, m in enumerate(history):
        if m.get("role") == "user":
            history = history[i:]
            break

    try:
        response = httpx.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.2:3b",
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    *history
                ],
                # Tool schemas. The model only sees these descriptions, so
                # they say clearly WHEN to use each tool and when NOT to.
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_balance",
                            "description": "Returns the user's account balance. Call ONLY if the user message contains words like 'balance', 'how much money do I have', or 'my account'. Never call for greetings or small talk.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_transactions",
                            "description": "Returns a LIST of the user's individual transactions (amount, type, category, date). Use when the user wants to SEE, LIST or SHOW their transactions or history. Do NOT use to calculate totals.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "calculate_expenses",
                            "description": "Calculates a TOTAL amount spent. Use when the user asks HOW MUCH they spent, in total or in a specific category. Do NOT use to list transactions.",

                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "category": {
                                        "type": "string",
                                        "description":  "Spending category. Provide ONLY if the user mentions a specific category. Omit it for total spending."
                                    }
                                },
                                "required": []
                            }
                        }
                    },
                    # Routing helper: lets the model signal "this is a banking
                    # request I cannot handle" instead of improvising an answer.
                    {
                        "type": "function",
                        "function": {
                            "name": "unsupported_banking_request",
                            "description": "Call this ONLY when the user asks a BANKING question or wants a banking action that the other tools cannot do: money transfers, payments, cards, loans, fees, interest rates, opening accounts. NEVER call for greetings, thanks, small talk, or non-banking topics.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    },
                ],
                # temperature 0 = more deterministic tool selection and answers
                "options": {"temperature": 0},
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        message = response.json()["message"]

    # Each failure mode gets its own user-friendly message instead of a 500.
    except httpx.TimeoutException:
        reply = "The AI service took too long to respond."

    except httpx.RequestError:
        reply = "Cannot connect to the AI service."

    except httpx.HTTPStatusError:
        reply = "The AI service returned an error."

    except (ValueError, KeyError, TypeError):
        reply = "The AI service returned an invalid response."

    else:
        # Request succeeded: save the model's message in the history.
        tool_calls = message.get("tool_calls", [])

        updated_messages = state["messages"] + [message]

        # The model wants to use tools -> route to the "tools" node.
        if tool_calls:
            return {
                "tool_calls": tool_calls,
                "messages": updated_messages
            }
        
        # No tool calls -> this is the final answer.
        return {
            "tool_calls": [],
            "messages": updated_messages,
            "reply": message.get("content", "")
        }

    # Only reached when the Ollama request failed (see except blocks above).
    return {"reply": reply, "tool_calls": []}



def tools_node(state: BankingState):
    """
    Execute every tool the model requested and add the results to the
    history as "tool" messages. The graph then returns to the assistant,
    which reads these results and writes the final answer.
    """
    tool_messages = []

    for tool in state["tool_calls"]:
        function_name = tool["function"]["name"]
       
        # Ollama may return null arguments for tools without parameters.
        arguments = tool["function"].get("arguments") or {}
        try:
            # user_id always comes from the authenticated state,
            # never from arguments chosen by the model.
            if function_name == "get_balance":
                result = {
                    "balance": get_balance(state["user_id"]),
                    "currency": "GEL"
                }
            
            elif function_name == "get_transactions":
                result = {
                    "transactions": get_transactions(state["user_id"]),
                    "currency": "GEL"
                }

            elif function_name == "calculate_expenses":
                category = arguments.get("category")

                result = {
                    "total_expenses": calculate_expenses(
                        state["user_id"],
                        category
                    ),
                    "category": category,
                    "currency": "GEL"
                }
            elif function_name == "unsupported_banking_request":
                # Instruction for the model, not data: it will phrase the
                # answer itself, in the user's language.
                result = (
                    "This action is not supported by the assistant. "
                    "Tell the user briefly that you cannot do this yourself and "
                    "suggest using the bank's mobile app, a branch, or customer support."
                )

            else:
                # The model invented a tool that does not exist.
                result = {"error": "Unknown tool"}

        except Exception as e:
            # One failing tool must not crash the whole request.
            # Details go to the log only; the model gets a generic message.
            print(f"Tool error ({function_name}): {e}")
            result = {"error": "The banking service is temporarily unavailable."}
        
        # JSON with an explicit currency is easier for the model to read
        # correctly than a raw Python value.
        tool_messages.append({
            "role": "tool",
            "tool_name": function_name,
            "content": json.dumps(result, ensure_ascii=False, default=str)
        })

    return {
        "messages": state["messages"] + tool_messages
    }

def route_after_assistant(state: BankingState):
    """Decide the next step: run tools if the model asked for them, else finish."""
    if state["tool_calls"]:
        return "tools"

    return END


# ---- Graph definition ----
graph = StateGraph(BankingState)
graph.add_node("assistant", assistant_node)
graph.add_node("tools", tools_node)

graph.add_edge(START, "assistant")
graph.add_conditional_edges("assistant", route_after_assistant)
# After tools run, go back to the assistant so the model can see the
# results. This edge creates the agent loop.
graph.add_edge("tools", "assistant")


# The checkpointer stores state per thread_id (conversation memory).
# InMemorySaver is lost on restart; use a database-backed one in production.
checkpointer = InMemorySaver()
banking_graph = graph.compile(checkpointer=checkpointer)