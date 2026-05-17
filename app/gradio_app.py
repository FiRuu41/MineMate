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
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
footer { display: none !important; }
.gradio-container { max-width: 100% !important; margin: 0 !important; }
/* Sidebar - dirt block inspired */
#sidebar {
    background: linear-gradient(180deg, #8B6914 0%, #A0855B 4px, #f3f4f6 4px, #f3f4f6 100%) !important;
    border-right: 3px solid #5D4E37 !important; padding: 0; min-height: 100vh;
}
#sidebar-header {
    padding: 14px 12px 10px 12px;
    background: linear-gradient(180deg, #7C9E5C 0%, #5D8A3C 60%, #4A7030 100%);
    border-bottom: 2px solid #3D5C1E;
    color: white !important;
    text-shadow: 1px 1px 0 #3D5C1E;
}
#sidebar-header h3 { color: white !important; font-weight: bold; font-size: 17px; letter-spacing: 1px; }
#sidebar-list button { text-align: left !important; font-size: 13px !important;
    padding: 10px 12px !important; border-radius: 0 !important; border: none !important;
    border-bottom: 1px solid #e5e7eb !important; background: transparent !important; }
#sidebar-list button:hover { background: #e5e7eb !important; }
#sidebar-list button.selected { background: #d4e6c8 !important; border-left: 3px solid #5D8A3C !important; }
#chat-col { padding: 0 !important; }
/* Header bar - grass block */
.header-bar {
    background: linear-gradient(180deg, #7C9E5C 0%, #5D8A3C 50%, #4A7030 100%);
    padding: 10px 20px; border-bottom: 3px solid #3D5C1E;
    color: white; font-weight: bold; display: flex; align-items: center; gap: 8px;
}
#chatbot { height: calc(100vh - 150px) !important; }
#input-box {
    padding: 12px 20px !important;
    border-top: 3px solid #8B6914 !important;
    background: linear-gradient(0deg, #f5f0e8 0%, #fff 100%) !important;
}
#chatbot .bubble { font-size: 15px; line-height: 1.6; }
#chatbot .bubble a { color: #2563eb; text-decoration: underline; }
/* User bubble - stone gray */
.bubble.user { background: #e8e4dc !important; border: 2px solid #a0a0a0 !important; }
/* Bot bubble - grass green tint */
.bubble.bot { background: #f0f7ec !important; border: 2px solid #a8c898 !important; }
/* Buttons - wood style */
button.primary { background: #8B6914 !important; border: 2px solid #5D4E37 !important; }
button.primary:hover { background: #A07818 !important; }
button.secondary { background: #8B8B8B !important; border: 2px solid #606060 !important; color: white !important; }
/* Pixel art block corners on chatbot */
#chatbot { border: 3px solid #8B6914; border-radius: 0 !important; }
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
        # Update sidebar after save
        return "", history, debug, conv_id, _build_radio()

    STEVE_AVATAR = "https://minotar.net/helm/Steve/64.png"
    BOT_AVATAR = "https://minotar.net/helm/GrassBlock/64.png"

    def new_chat():
        handler.clear()
        cid = str(int(time.time() * 1000))
        _save_conv(cid, [], "新对话")
        return [], "", "", cid, _build_radio()

    def delete_chat(conv_id: str):
        _delete_conv(conv_id)
        handler.clear()
        new_id = str(int(time.time() * 1000))
        _save_conv(new_id, [], "新对话")
        return [], "", "", new_id, _build_radio()

    def load_chat(cid: str):
        msgs = _load_conv(cid)
        handler.clear()
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
                gr.HTML('<div id="sidebar-header"><h3 style="margin:0;font-size:16px">⛏️ MineMate</h3></div>')
                new_btn = gr.Button("＋ 新对话", variant="secondary", size="sm")
                del_btn = gr.Button("🗑 删除当前对话", variant="stop", size="sm")
                radio = gr.Radio(choices=[], label="历史对话", interactive=True, elem_id="sidebar-list")
                with gr.Accordion("调试", open=False, elem_classes=["debug-box"]):
                    debug_out = gr.Textbox(label="", lines=5, interactive=False, show_label=False, container=False)

            # Main chat
            with gr.Column(scale=4, elem_id="chat-col"):
                chatbot = gr.Chatbot(
                    elem_id="chatbot", label="", layout="bubble",
                    buttons=["copy"], avatar_images=(STEVE_AVATAR, BOT_AVATAR),
                    placeholder="<div style='text-align:center;padding:80px 0'>"
                                  "<p style='font-size:3em;margin:0'>⛏️</p>"
                                  "<p style='font-size:1.3em;color:#5D4E37;margin:10px 0'>MineMate</p>"
                                  "<p style='font-size:0.9em;color:#888'>你的 MC 模组智能助手</p>"
                                  "<p style='font-size:0.8em;color:#aaa;margin-top:30px'>"
                                  "💎 百科查询 · 🎯 风格推荐 · 🔗 兼容分析 · 📦 整合包</p>"
                                  "</div>",
                )
                with gr.Row(elem_id="input-box"):
                    msg = gr.Textbox(
                        label="", placeholder="💬 输入问题...", scale=9,
                        show_label=False, container=False,
                    )
                    send = gr.Button("发送", variant="primary", scale=1)

        # Events
        def _sync_respond(m, h, cid):
            if not m.strip():
                return m, h, "", cid
            return asyncio.run(respond(m, h, cid))

        send.click(_sync_respond, inputs=[msg, chatbot, conv_id],
                   outputs=[msg, chatbot, debug_out, conv_id, radio]).then(lambda: "", None, [msg])
        msg.submit(_sync_respond, inputs=[msg, chatbot, conv_id],
                   outputs=[msg, chatbot, debug_out, conv_id, radio]).then(lambda: "", None, [msg])
        new_btn.click(new_chat, outputs=[chatbot, msg, debug_out, conv_id, radio])
        del_btn.click(
            lambda cid: delete_chat(cid), inputs=[conv_id],
            outputs=[chatbot, msg, debug_out, conv_id, radio]
        )
        radio.select(handle_radio_select, outputs=[chatbot, msg, debug_out, conv_id])
        demo.load(_build_radio, outputs=[radio])

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
