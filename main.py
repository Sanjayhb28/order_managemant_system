from fastapi import FastAPI, Request

app = FastAPI(title="Hotel WhatsApp Chatbot")
user_sessions = {}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages from Twilio"""
    form_data = await request.form()

    incoming_msg = form_data.get("Body", "").strip()
    from_number = form_data.get("From", "")

    print(incoming_msg, from_number)

    return incoming_msg, from_number


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

