from fastapi import FastAPI, Request
from langchain_core.messages import HumanMessage

from llm_handler.llm import graph

app = FastAPI(title="Hotel WhatsApp Chatbot")
user_sessions = {}
from fastapi import FastAPI, Request, Response

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages from Twilio"""
    form_data = await request.form()

    incoming_msg = form_data.get("Body", "").strip()
    from_number = form_data.get("From", "")

    print(incoming_msg, from_number)

    if from_number not in user_sessions:
        user_sessions[from_number] = {
            "messages": [],
            "user_info": {"phone_number": from_number}
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
    print(ai_response)

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


# @app.post("/clear-session/{phone_number}")
def clear_session(phone_number: str):
    """Clear user session (for testing)"""
    if phone_number in user_sessions:
        del user_sessions[phone_number]
        return {"message": "Session cleared"}
    return {"message": "No session found"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

