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
.gradio-container { max-width: 900px !important; margin: 0 auto !important; }
#chatbot { height: 65vh !important; }
#chatbot .bubble { font-size: 15px !important; line-height: 1.6 !important; }
#chatbot .bubble a { color: #4da3ff !important; text-decoration: underline !important; }
#chatbot .bubble ul, #chatbot .bubble ol { padding-left: 20px !important; }
footer .show-api { display: none !important; }
.debug-box textarea { font-size: 11px !important; font-family: 'Consolas', monospace !important; opacity: 0.7; }
"""


def main() -> None:
    setup_logging()
    handler = build_handler()

    async def respond(message: str, history: list):
        answer, debug = await handler.chat(message)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})
        return "", history, debug

    async def on_clear():
        handler.clear()
        return [], "", ""

    with gr.Blocks(title="MineMate — MC Mod Q&A", css=CSS) as demo:
        gr.Markdown("# MineMate")
        gr.Markdown("Ask anything about Minecraft mods — recommendations, compatibility, modpack ideas, and more.")

        chatbot = gr.Chatbot(
            elem_id="chatbot",
            label="",
            layout="bubble",
            buttons=["copy"],
            avatar_images=(None, None),
            placeholder="<div style='text-align:center;color:#888;padding:40px'>"
                          "<p style='font-size:1.2em'>MineMate — Your AI buddy for Minecraft mods</p>"
                          "<p style='font-size:0.9em'>Try: 推荐几个恐怖模组 · 机械动力能和什么兼容 · 推荐轻量科技整合包 1.20.1</p>"
                          "</div>",
        )

        with gr.Row():
            msg = gr.Textbox(
                label="",
                placeholder="输入问题...",
                scale=9,
                show_label=False,
                container=False,
            )
            send = gr.Button("发送", variant="primary", scale=1)

        with gr.Accordion("调试信息", open=False, elem_classes=["debug-box"]):
            debug_out = gr.Textbox(label="", lines=8, interactive=False, show_label=False, container=False)

        clear_btn = gr.Button("清空对话", size="sm", variant="secondary")

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
