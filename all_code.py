"""
WhatsApp Hotel Chatbot with LangGraph, LangChain, and Google Sheets Integration
Handles menu queries and order placement for a small hotel business.
"""

import os
from typing import TypedDict, Annotated, Sequence
from datetime import datetime
import operator

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import json

# Initialize FastAPI
app = FastAPI(title="Hotel WhatsApp Chatbot")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
GOOGLE_SHEETS_CREDS_FILE = "credentials.json"  # Path to your Google service account JSON
MENU_SHEET_NAME = "Hotel Menu"  # Name of your Google Sheet for menu
ORDERS_SHEET_NAME = "Hotel Orders"  # Name of your Google Sheet for orders
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Initialize Google Sheets
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDS_FILE, scope)
    client = gspread.authorize(creds)
except:
    print("Warning: Google Sheets credentials not found. Please add credentials.json")
    client = None

# Initialize LLM
llm = GoogleGenerativeAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

# Session storage (in production, use Redis or database)
user_sessions = {}


# Google Sheets Helper Functions
def get_menu_from_sheet():
    """Retrieve menu from Google Sheets"""
    if not client:
        return "Unable to fetch menu. Please contact support."

    try:
        sheet = client.open(MENU_SHEET_NAME).sheet1
        menu_data = sheet.get_all_records()

        menu_text = "🍽️ **HOTEL MENU** 🍽️\n\n"
        for item in menu_data:
            menu_text += f"📌 *{item['Item']}*\n"
            menu_text += f"   ₹{item['Price']} | {item['Category']}\n"
            if 'Description' in item and item['Description']:
                menu_text += f"   {item['Description']}\n"
            menu_text += "\n"

        return menu_text
    except Exception as e:
        return f"Error fetching menu: {str(e)}"


def save_order_to_sheet(order_details: dict):
    """Save order to Google Sheets"""
    if not client:
        return False

    try:
        sheet = client.open(ORDERS_SHEET_NAME).sheet1

        # Prepare order row
        order_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            order_details.get("customer_name", ""),
            order_details.get("phone_number", ""),
            order_details.get("room_number", ""),
            json.dumps(order_details.get("items", [])),
            order_details.get("total_amount", 0),
            order_details.get("special_instructions", ""),
            "Pending"
        ]

        sheet.append_row(order_row)
        return True
    except Exception as e:
        print(f"Error saving order: {str(e)}")
        return False


# LangChain Tools
@tool
def get_menu() -> str:
    """Retrieve the hotel menu with items, prices, and descriptions."""
    return get_menu_from_sheet()


@tool
def get_item_details(item_name: str) -> str:
    """Get detailed information about a specific menu item."""
    if not client:
        return "Unable to fetch item details."

    try:
        sheet = client.open(MENU_SHEET_NAME).sheet1
        menu_data = sheet.get_all_records()

        for item in menu_data:
            if item_name.lower() in item['Item'].lower():
                details = f"*{item['Item']}*\n"
                details += f"Price: ₹{item['Price']}\n"
                details += f"Category: {item['Category']}\n"
                if 'Description' in item and item['Description']:
                    details += f"Description: {item['Description']}\n"
                return details

        return f"Item '{item_name}' not found in menu."
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def place_order(customer_name: str, phone_number: str, room_number: str,
                items: str, special_instructions: str = "") -> str:
    """
    Place an order for the customer.

    Args:
        customer_name: Customer's name
        phone_number: Customer's phone number
        room_number: Hotel room number
        items: JSON string of ordered items with quantities
        special_instructions: Any special requests
    """
    try:
        items_list = json.loads(items)

        # Calculate total (in production, fetch prices from sheet)
        total = 0
        if client:
            sheet = client.open(MENU_SHEET_NAME).sheet1
            menu_data = sheet.get_all_records()
            menu_dict = {item['Item'].lower(): item['Price'] for item in menu_data}

            for item in items_list:
                item_name = item['name'].lower()
                quantity = item['quantity']
                if item_name in menu_dict:
                    total += menu_dict[item_name] * quantity

        order_details = {
            "customer_name": customer_name,
            "phone_number": phone_number,
            "room_number": room_number,
            "items": items_list,
            "total_amount": total,
            "special_instructions": special_instructions
        }

        success = save_order_to_sheet(order_details)

        if success:
            order_summary = f"✅ Order placed successfully!\n\n"
            order_summary += f"Customer: {customer_name}\n"
            order_summary += f"Room: {room_number}\n"
            order_summary += f"Items:\n"
            for item in items_list:
                order_summary += f"  - {item['quantity']}x {item['name']}\n"
            if total > 0:
                order_summary += f"\nTotal: ₹{total}\n"
            if special_instructions:
                order_summary += f"Special Instructions: {special_instructions}\n"
            order_summary += f"\nYour order will be delivered shortly!"
            return order_summary
        else:
            return "❌ Failed to place order. Please try again or contact support."

    except Exception as e:
        return f"Error placing order: {str(e)}"


# LangGraph State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_info: dict


# Agent Nodes
def should_continue(state: AgentState):
    """Determine if we should continue or end"""
    messages = state["messages"]
    last_message = messages[-1]

    # If there are no tool calls, end
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
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


# FastAPI Routes
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages from Twilio"""
    form_data = await request.form()

    incoming_msg = form_data.get("Body", "").strip()
    from_number = form_data.get("From", "")

    # Get or create user session
    if from_number not in user_sessions:
        user_sessions[from_number] = {
            "messages": [],
            "user_info": {}
        }

    session = user_sessions[from_number]

    # Add user message to session
    session["messages"].append(HumanMessage(content=incoming_msg))

    # Run the agent
    result = graph.invoke({
        "messages": session["messages"],
        "user_info": session["user_info"]
    })

    # Get the last AI message
    ai_response = result["messages"][-1].content

    # Update session with full conversation
    session["messages"] = result["messages"]

    # Prepare Twilio response
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Message>{ai_response}</Message>
    </Response>"""

    return Response(content=response_xml, media_type="application/xml")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "WhatsApp Hotel Chatbot"}


@app.post("/clear-session/{phone_number}")
async def clear_session(phone_number: str):
    """Clear user session (for testing)"""
    if phone_number in user_sessions:
        del user_sessions[phone_number]
        return {"message": "Session cleared"}
    return {"message": "No session found"}


# Setup Instructions
"""
SETUP INSTRUCTIONS:

1. Google Sheets Setup:
   - Create two Google Sheets:
     a) "Hotel Menu" with columns: Item, Price, Category, Description
     b) "Hotel Orders" with columns: Timestamp, Customer Name, Phone Number, 
        Room Number, Items, Total Amount, Special Instructions, Status

   - Get Google Sheets API credentials:
     a) Go to Google Cloud Console
     b) Create a service account
     c) Download the JSON credentials file as 'credentials.json'
     d) Share both sheets with the service account email

2. Environment Variables:
   export OPENAI_API_KEY="your-openai-api-key"
   export TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"

3. Twilio WhatsApp Setup:
   - Sign up for Twilio
   - Enable WhatsApp sandbox or get approved number
   - Set webhook URL to: https://your-domain.com/webhook

4. Install Dependencies:
   pip install fastapi uvicorn gspread oauth2client langchain-openai langgraph langchain-core

5. Run the Application:
   uvicorn main:app --host 0.0.0.0 --port 8000

6. For production deployment, use:
   - ngrok for testing: ngrok http 8000
   - Or deploy to cloud platforms like Railway, Render, or AWS

Example Menu Sheet Format:
| Item          | Price | Category    | Description                    |
|---------------|-------|-------------|--------------------------------|
| Masala Dosa   | 120   | Breakfast   | Crispy dosa with potato filling|
| Chicken Biryani| 250  | Main Course | Aromatic basmati rice with chicken|
| Filter Coffee | 50    | Beverages   | Traditional South Indian coffee|
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)