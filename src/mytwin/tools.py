import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

# pushover_user = os.getenv("PUSHOVER_USER")
# pushover_token = os.getenv("PUSHOVER_TOKEN")
# pushover_url = "https://api.pushover.net/1/messages.json"

telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(text):
    response = requests.post(
        telegram_url,
        data={
            "chat_id": telegram_chat_id,
            "text": text,
            "disable_notification": False
        },
    )
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message. Error: {response.text}")


def record_user_details(email, name="Name not provided", notes="not provided"):
    send_telegram_message(f"Recording interest from {name} with email {email} and notes {notes}")
    return "OK"


def record_unknown_question(question):
    send_telegram_message(f"Recording {question} asked that I couldn't answer")
    return "OK"


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {
                "type": "string",
                "description": "Any additional info about the conversation that's worth recording to give context",
            },
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"},
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
]

tool_map = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
}


def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = tool_map.get(tool_name)
        result = tool(**arguments) if tool else "Unknown tool: " + tool_name
        results.append(
            {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id}
        )
    return results
