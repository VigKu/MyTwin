from openai import OpenAI
from src.mytwin.cache import LRUSemanticPromptCache
from src.mytwin.context import get_twin_system_prompt
from src.mytwin.tools import tools, handle_tool_calls
from src.mytwin.styles import CSS, JS, EXAMPLES
from dotenv import load_dotenv
import gradio as gr
from time import perf_counter
import re
from src.mytwin.tools import save_knowledge_gap

load_dotenv(override=True)

MODEL_NAME = "gpt-5.4-nano" #"gpt-4o-mini"

openai = OpenAI()
# Initialize your Semantic Prompt Cache here
# This needs to live globally so it doesn't reset on every chat turn
pcache = LRUSemanticPromptCache(threshold=0.7, lexical_threshold=80.0, max_size=15)
system = [{"role": "system", "content": get_twin_system_prompt()}]


def contains_pii(text: str) -> bool:
    """Checks if the text looks like it contains names, emails, or phone numbers."""
    # Simple regex for email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    # Simple regex for phone numbers (matches various international/local formats)
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    # Catching explicit self-introductions (e.g., "My name is...", "I am...")
    name_intro_pattern = r'(?i)\b(my name is|i am|call me)\b'

    if re.search(email_pattern, text) or re.search(phone_pattern, text) or re.search(name_intro_pattern, text):
        return True
    return False

def is_unknown_response(text: str) -> bool:
    """Detects variations of 'I don't know' or requests to contact directly."""
    lowercase_text = text.lower().replace("’", "'").replace("`", "'")
    indicators = [
        "i don't know", "dont know", "do not know", "insufficient information",
        "don't have that information", "not mentioned",
        "don't have additional confirmed details", "don't have details", "do not have details"
    ]
    return any(ind in lowercase_text for ind in indicators)

def chat(message, history):
    # --- Optional: If you want full context tracking, uncomment the next 2 lines ---
    # from your previous historical requirement:
    # conversation_signature = "\n".join([f"{m['role']}: {m['content']}" for m in history + [{"role": "user", "content": message}]])
    # cache_key = conversation_signature

    # Add time tracking
    start_time = perf_counter()
    
    # Defaulting to your current code structure:
    cache_key = message 

    # 1. Check the semantic cache first
    cached_res, score = pcache.query(cache_key)
    print(f"-> Similarity Score: {score}")
    if cached_res:
        duration = perf_counter() - start_time
        print(f"-> [CACHE HIT] Similarity Score: {score:.2f} | Time taken: {duration:.5f}")
        return cached_res

    print("-> [CACHE MISS] Querying LLM...")

    # 2. Proceed with OpenAI LLM logic if cache misses
    messages = system + history + [{"role": "user", "content": message}]
    
    # FIX: Added [0] index to choices
    response = openai.chat.completions.create(model=MODEL_NAME, messages=messages, tools=tools)
    while response.choices[0].finish_reason == "tool_calls":
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls
        results = handle_tool_calls(tool_calls)
        messages.append(assistant_message)
        messages.extend(results)
        response = openai.chat.completions.create(model=MODEL_NAME, messages=messages, tools=tools)
    
    # FIX: Added [0] index to choices
    final_content = response.choices[0].message.content

    # 3. Handle saving logic with validation rules
    if final_content:
        # Check Rule 1 & Rule 2: Do not cache if PII is present OR if it's an "I don't know" response
        if contains_pii(message) or is_unknown_response(final_content):
            print("-> [CACHE SKIP] Prompt/Response contains PII or Unknown Answer state. Not saving to cache.")
            
            # Rule 3: Save unknown answers to huggingface dataset knowledge_gap.txt
            if is_unknown_response(final_content):
                print("-> [KNOWLEDGE GAP DETECTED] Writing to Hugging Face...")
                save_knowledge_gap(message, final_content)
        else:
            pcache.add(cache_key, final_content)
            
    duration = perf_counter() - start_time
    print(f"Time taken: {duration:.5f}")
    return final_content

demo = gr.ChatInterface(
        chat,
        examples=EXAMPLES,
        title="My Digital Twin",
        description="Have a chat with my AI twin about my career.",
        chatbot=gr.Chatbot(show_label=False),
    )
# if __name__ == "__main__":
#     gr.ChatInterface(
#         chat,
#         examples=EXAMPLES,
#         title="My Digital Twin",
#         description="Have a chat with my AI twin about my career.",
#         chatbot=gr.Chatbot(show_label=False),
#     ).launch(css=CSS, js=JS, theme=gr.themes.Base())
