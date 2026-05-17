import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import asyncio
import json
import time
from pathlib import Path

import gradio as gr

from agents.answerer import AnswererAgent
from agents.critic import CriticAgent
from agents.router import RouterAgent
from agents.workflow import McmodWorkflow
from app.chat_handler import ChatHandler
from config.logging import setup_logging
from kb.retriever import HybridRetriever

CONV_DIR = Path("data/conversations")
CONV_DIR.mkdir(parents=True, exist_ok=True)

CSS = """
footer { display: none !important; }
.gradio-container { max-width: 100% !important; margin: 0 !important; }
#sidebar { background: #f3f4f6; border-right: 1px solid #d1d5db; padding: 0; min-height: 100vh; }
#sidebar-header { padding: 12px; border-bottom: 1px solid #d1d5db; }
#sidebar-list button { text-align: left !important; font-size: 13px !important;
    padding: 10px 12px !important; border-radius: 0 !important; border: none !important;
    border-bottom: 1px solid #e5e7eb !important; background: transparent !important; }
#sidebar-list button:hover { background: #e5e7eb !important; }
#sidebar-list button.selected { background: #bfdbfe !important; }
#chat-col { padding: 0 !important; }
#chatbot { height: calc(100vh - 110px) !important; }
#input-box { padding: 12px 20px !important; border-top: 1px solid #d1d5db !important; background: #fff !important; }
#chatbot .bubble { font-size: 15px; line-height: 1.6; }
#chatbot .bubble a { color: #2563eb; text-decoration: underline; }
.debug-box textarea { font-size: 11px; font-family: 'Consolas', monospace; opacity: 0.6; }
"""


def build_handler() -> ChatHandler:
    workflow = McmodWorkflow(
        router=RouterAgent(),
        retriever=HybridRetriever(),
        answerer=AnswererAgent(),
        critic=CriticAgent(),
    )
    return ChatHandler(workflow=workflow)


def _list_convs():
    files = sorted(CONV_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            title = data.get("title", f.stem)
            updated = data.get("updated", 0)
            result.append((f.stem, title, updated))
        except Exception:
            pass
    return result


def _save_conv(conv_id: str, messages: list, title: str = ""):
    data = {
        "id": conv_id, "title": title or "新对话",
        "messages": messages, "updated": time.time(),
    }
    (CONV_DIR / f"{conv_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_conv(conv_id: str) -> list:
    f = CONV_DIR / f"{conv_id}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8")).get("messages", [])
    return []


def _delete_conv(conv_id: str):
    f = CONV_DIR / f"{conv_id}.json"
    if f.exists():
        f.unlink()


def main() -> None:
    setup_logging()
    handler = build_handler()

    async def respond(message: str, history: list, conv_id: str):
        if not message.strip():
            return "", history, "", conv_id
        answer, debug = await handler.chat(message)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})
        title = history[0]["content"][:40] if history else "新对话"
        _save_conv(conv_id, history, title)
        return "", history, debug, conv_id

    def new_chat():
        handler.clear()
        cid = str(int(time.time() * 1000))
        _save_conv(cid, [], "新对话")
        return [], "", "", cid, _build_radio()

    def load_chat(cid: str):
        msgs = _load_conv(cid)
        handler.clear()
        # Replay messages into memory
        for m in msgs:
            if m["role"] == "user":
                handler.memory.add_user(m["content"])
            elif m["role"] == "assistant":
                handler.memory.add_assistant(m["content"])
        return msgs, "", "", cid

    def handle_radio_select(evt: gr.SelectData):
        convs = _list_convs()
        idx = evt.index
        if 0 <= idx < len(convs):
            cid = convs[idx][0]
            return load_chat(cid)
        return gr.skip()

    def _build_radio():
        convs = _list_convs()
        if not convs:
            return gr.Radio(choices=[], label="历史对话", interactive=False)
        choices = [(f"{title[:25]}\n{_fmt_time(ts)}", cid) for cid, title, ts in convs]
        return gr.Radio(choices=choices, label="历史对话", interactive=True, elem_id="sidebar-list")

    def _fmt_time(ts):
        from datetime import datetime
        dt = datetime.fromtimestamp(ts)
        now = datetime.now()
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        return dt.strftime("%m-%d")

    with gr.Blocks(title="MineMate", css=CSS) as demo:
        conv_id = gr.State(str(int(time.time() * 1000)))

        with gr.Row(equal_height=True):
            # Sidebar
            with gr.Column(scale=1, min_width=240, elem_id="sidebar"):
                gr.HTML('<div id="sidebar-header"><h3 style="margin:0;font-size:16px">MineMate</h3></div>')
                new_btn = gr.Button("＋ 新对话", variant="secondary", size="sm")
                radio = gr.Radio(choices=[], label="历史对话", interactive=True, elem_id="sidebar-list")
                with gr.Accordion("调试", open=False, elem_classes=["debug-box"]):
                    debug_out = gr.Textbox(label="", lines=5, interactive=False, show_label=False, container=False)

            # Main chat
            with gr.Column(scale=4, elem_id="chat-col"):
                chatbot = gr.Chatbot(
                    elem_id="chatbot", label="", layout="bubble",
                    buttons=["copy"], avatar_images=(None, None),
                    placeholder="<div style='text-align:center;color:#888;padding:80px'>"
                                  "<p style='font-size:1.3em'>MineMate</p>"
                                  "<p style='font-size:0.9em'>你的 MC 模组智能助手</p>"
                                  "</div>",
                )
                with gr.Row(elem_id="input-box"):
                    msg = gr.Textbox(
                        label="", placeholder="输入问题...", scale=9,
                        show_label=False, container=False,
                    )
                    send = gr.Button("发送", variant="primary", scale=1)

        # Events
        def _sync_respond(m, h, cid):
            if not m.strip():
                return m, h, "", cid
            return asyncio.run(respond(m, h, cid))

        send.click(_sync_respond, inputs=[msg, chatbot, conv_id],
                   outputs=[msg, chatbot, debug_out, conv_id]).then(lambda: "", None, [msg])
        msg.submit(_sync_respond, inputs=[msg, chatbot, conv_id],
                   outputs=[msg, chatbot, debug_out, conv_id]).then(lambda: "", None, [msg])
        new_btn.click(new_chat, outputs=[chatbot, msg, debug_out, conv_id, radio])
        radio.select(handle_radio_select, outputs=[chatbot, msg, debug_out, conv_id])

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
