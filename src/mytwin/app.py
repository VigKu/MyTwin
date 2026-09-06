from openai import OpenAI
from src.mytwin.cache import LRUSemanticPromptCache
from src.mytwin.context import TWIN_SYSTEM_PROMPT
from src.mytwin.tools import tools, handle_tool_calls
from src.mytwin.styles import CSS, JS, EXAMPLES
from dotenv import load_dotenv
import gradio as gr
from time import perf_counter

load_dotenv(override=True)

MODEL_NAME = "gpt-5.4-nano" #"gpt-4o-mini"

openai = OpenAI()
# Initialize your Semantic Prompt Cache here
# This needs to live globally so it doesn't reset on every chat turn
pcache = LRUSemanticPromptCache(threshold=0.7, lexical_threshold=80.0, max_size=15)
system = [{"role": "system", "content": TWIN_SYSTEM_PROMPT}]

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

    # 3. Save the final resolved answer to the cache for future use
    if final_content:
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
