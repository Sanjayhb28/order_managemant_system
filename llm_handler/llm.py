from typing import TypedDict, Annotated, Sequence
import operator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from llm_handler.tools import get_menu, get_item_details, place_order
from dotenv import load_dotenv


load_dotenv()


# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


# LangGraph State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_info: dict


# Agent Nodes
def should_continue(state: AgentState):
    """Determine if we should continue or end"""
    messages = state["messages"]
    # print(messages)
    last_message = messages[-1]

    # If there are no tool calls, end
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        # clear_session(messages[1].content)  # Assuming the second message is from the user
        return "end"
    return "continue"


def call_model(state: AgentState):
    """Call the LLM with tools"""
    messages = state["messages"]

    # Add system message if not present
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        system_message = SystemMessage(content="""You are a helpful hotel assistant chatbot for WhatsApp.
        Your role is to:
        1. Help customers view the menu
        2. Answer questions about menu items
        3. Take orders and save them to the system

        Be friendly, concise, and helpful. When taking orders, make sure to collect:
        - Customer name
        - Room number
        - Items and quantities
        - Any special instructions

        Use the available tools to fetch menu information and place orders.""")
        messages = [system_message] + messages

    response = llm.bind_tools([get_menu, get_item_details, place_order]).invoke(messages)
    return {"messages": [response]}


def call_tools(state: AgentState):
    """Execute tool calls"""
    messages = state["messages"]
    last_message = messages[-1]

    tool_mapping = {
        "get_menu": get_menu,
        "get_item_details": get_item_details,
        "place_order": place_order
    }

    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool = tool_mapping[tool_call["name"]]
        result = tool.invoke(tool_call["args"])
        tool_messages.append({
            "role": "tool",
            "content": result,
            "tool_call_id": tool_call["id"]
        })

    return {"messages": tool_messages}


# Build LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)

workflow.add_edge("tools", "agent")

graph = workflow.compile()
