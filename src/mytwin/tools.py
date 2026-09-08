import json
import os
import requests
import threading
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download

load_dotenv(override=True)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

# telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
# telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
# telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
# DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

REPO_ID = "Vikool/MyData"
hf_token = os.getenv("HF_TOKEN")
filename = "knowledge_gap.txt"

# FUNCTIONS

def push(text):
    requests.post(
        pushover_url,
        data={
            "token": pushover_token,
            "user": pushover_user,
            "message": text,
        },
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return "OK"


def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return "OK"

def save_knowledge_gap(question: str, answer: str):
    """Downloads knowledge_gap.txt, appends the QA pair, and pushes it back up to HF."""
    api = HfApi(token=hf_token)
    
    # 1. Download existing or start fresh
    try:
        local_path = hf_hub_download(repo_id=REPO_ID, filename=filename, token=hf_token, repo_type="dataset")
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        content = "" # If file doesn't exist yet

    # 2. Format the new entry
    new_entry = f"Prompt: {question.strip()}\nAnswer: {answer.strip()}\n\n"
    updated_content = content + new_entry

    # 3. Save locally and upload
    local_write_path = os.path.join("./", filename) #f"/tmp/{filename}"
    with open(local_write_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    try:
        api.upload_file(
            path_or_fileobj=local_write_path,
            path_in_repo=filename,
            repo_id=REPO_ID,
            repo_type="dataset"
        )
        print("-> Successfully uploaded knowledge gap entry to HF.")
    except Exception as e:
        print(f"-> Failed to upload knowledge gap to HF: {e}")

def query_additional_knowledge():
    """Tool for the model to pull the latest resolved context dynamically."""
    hf_token = os.getenv("HF_TOKEN")
    try:
        local_path = hf_hub_download(repo_id=REPO_ID, filename="knowledge_gap.txt", token=hf_token, repo_type="dataset")
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return "No additional knowledge gap file found or error downloading it."

# SCHEMAS

query_additional_knowledge_json = {
    "name": "query_additional_knowledge",
    "description": "Call this tool to read the external knowledge_gap text file containing answered edge case questions. Use this before giving up or if the core resume lacks the data.",
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

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

# schemas array
tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
    {"type": "function", "function": query_additional_knowledge_json},
]

# routing map
tool_map = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
    "query_additional_knowledge": query_additional_knowledge,
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
