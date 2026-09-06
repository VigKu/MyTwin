import gradio as gr
from src.mytwin.styles import CSS, JS
from src.mytwin.app import demo

if __name__ == "__main__":
    """
    We need app.py in root folder to deploy in huggingface spaces
    so this points to our original app.py in src/mytwin.
    """
    demo.launch(css=CSS, js=JS, theme=gr.themes.Base())