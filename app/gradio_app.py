import os

# MUST come before any import that loads huggingface_hub (e.g. gradio).
# huggingface_hub caches HF_ENDPOINT at import time, so setting it later is too late.
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import asyncio

import gradio as gr

from agents.answerer import AnswererAgent
from agents.router import RouterAgent
from agents.workflow import McmodWorkflow
from app.chat_handler import ChatHandler
from config.logging import setup_logging
from kb.retriever import VectorRetriever


def build_handler() -> ChatHandler:
    workflow = McmodWorkflow(
        router=RouterAgent(),
        retriever=VectorRetriever(),
        answerer=AnswererAgent(),
    )
    return ChatHandler(workflow=workflow)


def main() -> None:
    setup_logging()
    handler = build_handler()

    async def respond(message: str, show_debug: bool):
        answer, debug = await handler.chat(message)
        return answer, debug if show_debug else ""

    with gr.Blocks(title="MC Mod QA") as demo:
        gr.Markdown("# MC 模组智能问答（MVP）")
        with gr.Row():
            with gr.Column(scale=2):
                msg = gr.Textbox(label="你的问题", placeholder="例：什么是机械动力？")
                ask = gr.Button("提问", variant="primary")
                ans = gr.Markdown(label="回答")
            with gr.Column(scale=1):
                show_debug = gr.Checkbox(label="显示调试信息", value=True)
                debug_out = gr.Textbox(label="调试", lines=12, interactive=False)

        def _sync_respond(m, d):
            return asyncio.run(respond(m, d))

        ask.click(_sync_respond, inputs=[msg, show_debug], outputs=[ans, debug_out])

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
