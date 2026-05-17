import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import asyncio

import gradio as gr

from agents.answerer import AnswererAgent
from agents.critic import CriticAgent
from agents.router import RouterAgent
from agents.workflow import McmodWorkflow
from app.chat_handler import ChatHandler
from config.logging import setup_logging
from kb.retriever import HybridRetriever


def build_handler() -> ChatHandler:
    workflow = McmodWorkflow(
        router=RouterAgent(),
        retriever=HybridRetriever(),
        answerer=AnswererAgent(),
        critic=CriticAgent(),
    )
    return ChatHandler(workflow=workflow)


CSS = """
footer { display: none !important; }
.debug-panel textarea { font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }
"""


def main() -> None:
    setup_logging()
    handler = build_handler()

    async def respond(message: str, history: list):
        """Called by gr.ChatInterface on each user message."""
        answer, debug = await handler.chat(message)
        # Append assistant response to history for chatbot display
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})
        return "", history, debug

    async def on_clear():
        handler.clear()
        return [], "", ""

    with gr.Blocks(css=CSS, title="MineMate") as demo:
        gr.Markdown("# MineMate — MC 模组智能问答")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    bubble_full_width=False,
                    height=550,
                    show_copy_button=True,
                    avatar_images=(None, None),
                )
                with gr.Row():
                    msg = gr.Textbox(
                        label="",
                        placeholder="输入你的问题，例如：有没有恐怖点的模组？",
                        scale=8,
                        show_label=False,
                    )
                    send = gr.Button("发送", variant="primary", scale=1)

            with gr.Column(scale=1, elem_classes=["debug-panel"]):
                gr.Markdown("### 调试信息")
                show_debug = gr.Checkbox(label="显示调试", value=True)
                debug_out = gr.Textbox(label="", lines=18, interactive=False, show_label=False)
                clear_btn = gr.Button("清空对话", size="sm")

        def _sync_respond(m, h):
            return asyncio.run(respond(m, h))

        send.click(
            _sync_respond, inputs=[msg, chatbot], outputs=[msg, chatbot, debug_out]
        ).then(lambda: "", None, [msg])
        msg.submit(
            _sync_respond, inputs=[msg, chatbot], outputs=[msg, chatbot, debug_out]
        ).then(lambda: "", None, [msg])

        clear_btn.click(
            lambda: asyncio.run(on_clear()),
            outputs=[chatbot, msg, debug_out],
        )

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
