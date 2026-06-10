# -*- coding: utf-8 -*-
import os
import shutil

import gradio as gr

from ingestion.pdf_loader import load_pdf, load_pdf_with_meta
from ingestion.chunker import chunk_text, chunk_text_with_meta
from ingestion.indexer import (
    index_chunks, list_courses, get_course_stats, delete_course,
    list_sources, delete_source, get_source_count, collection,
)
from retrieval.search import search
from llm.dashscope_llm import generate, generate_stream
from llm.learning_assistant import (
    generate_chapter_summary,
    generate_exam_questions,
    explain_concept,
)
from router.intent_router import route as route_intent
from memory.tracker import (
    record_chapter, mark_mastery, get_context_prompt,
    get_summary, get_chapters_learned, get_weak_concepts,
)
from utils.text_clean import clean_text
from utils.ppt_converter import convert_pptx_to_pdf
from storage.learning_log import save_record, get_history

# =============================================================
#  Custom CSS — ChatGPT Workspace (pure black & white)
# =============================================================

CUSTOM_CSS = """
:root {
  --text-strong:  rgba(0,0,0,0.85);
  --text-base:    rgba(0,0,0,0.55);
  --text-weak:    rgba(0,0,0,0.35);
  --border-light: rgba(0,0,0,0.06);
  --border-input: rgba(0,0,0,0.12);
  --border-focus: rgba(0,0,0,0.22);
  --bg:           #ffffff;
  --sidebar-width: 240px;
  --content-width: 820px;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  color: var(--text-strong);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  margin: 0;
  overflow: hidden;
}

/* ── Strip Gradio defaults ──────────────────────────── */
.gradio-container { max-width: none !important; margin: 0 !important; padding: 0 !important; }
footer, .versions, #footer, .watermark, .built-with { display: none !important; }

/* ── Sidebar — 240px fixed, course list only ────────── */
.sidebar {
  position: fixed !important; left: 0 !important; top: 0 !important;
  width: var(--sidebar-width) !important; height: 100vh !important;
  background: var(--bg) !important;
  border-right: 1px solid var(--border-light) !important;
  padding: 24px 20px !important; overflow-y: auto !important; z-index: 10 !important;
  display: flex !important; flex-direction: column !important; gap: 0 !important;
}
.sidebar * { font-family: inherit !important; background: transparent !important; box-shadow: none !important; }
.sidebar label { font-size: 11px !important; font-weight: 500 !important; color: var(--text-weak) !important; }
.sidebar input, .sidebar textarea {
  font-size: 13px !important; color: var(--text-strong) !important;
  background: var(--bg) !important;
  border: 1px solid var(--border-light) !important; border-radius: 6px !important;
}
.sidebar button {
  font-size: 13px !important; font-weight: 400 !important;
  border-radius: 6px !important; color: var(--text-base) !important;
}

/* ── Main area ──────────────────────────────────────── */
.main-area {
  margin-left: var(--sidebar-width) !important; display: flex !important;
  flex-direction: column !important; height: 100vh !important;
  background: var(--bg) !important;
}
.main-area * { font-family: inherit !important; }

/* ── Chatbot — transparent, center welcome, top-align chat ─ */
.chatbot {
  border: none !important; border-radius: 0 !important;
  background: transparent !important; box-shadow: none !important;
  flex: 1 !important; overflow-y: auto !important; padding: 0 !important;
  display: flex !important; flex-direction: column !important;
  justify-content: center !important;
}
.chatbot * { background: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important; }
.chatbot .message {
  font-size: 15px !important; line-height: 1.625 !important;
  color: var(--text-strong) !important;
  max-width: var(--content-width) !important; width: 100% !important;
  margin: 0 auto !important; padding: 0 24px !important;
}
.chatbot .bubble-wrap { padding: 8px 0 !important; margin: 0 !important; }
.chatbot .user .bubble-wrap { color: var(--text-base) !important; }
.chatbot .bot .bubble-wrap { color: var(--text-strong) !important; }

/* ── Message markdown ───────────────────────────────── */
.chatbot .message-wrap h1 { font-size: 1.05rem; font-weight: 600; color: var(--text-strong); }
.chatbot .message-wrap h2 { font-size: 1rem; font-weight: 600; color: var(--text-strong); }
.chatbot .message-wrap h3 { font-size: 0.9375rem; font-weight: 600; color: var(--text-strong); }
.chatbot .message-wrap p, .chatbot .message-wrap div { color: var(--text-strong); }
.chatbot .message-wrap pre {
  border: 1px solid var(--border-light) !important; border-radius: 6px !important;
  padding: 12px 16px; overflow-x: auto;
}
.chatbot .message-wrap blockquote {
  border-left: 2px solid rgba(0,0,0,0.12); padding-left: 12px;
  margin-left: 0; color: var(--text-base);
}
.chatbot .message-wrap details {
  margin-top: 12px; padding: 0; font-size: 0.8125rem; color: rgba(0,0,0,0.45);
}
.chatbot .message-wrap details summary { cursor: pointer; color: rgba(0,0,0,0.45); font-weight: 500; }
.chatbot .message-wrap ul, .chatbot .message-wrap ol { padding-left: 1.25em; }
.chatbot .message-wrap li { margin: 2px 0; }

/* ── Example prompts in welcome ─────────────────────── */
.example-item {
  font-size: 14px; color: var(--text-weak); padding: 7px 0;
  cursor: pointer; text-align: center; transition: color 0.15s; user-select: none;
}
.example-item:hover { color: var(--text-base); }

/* ── Composer — pill container ──────────────────────── */
.composer-wrap {
  flex-shrink: 0 !important;
  max-width: var(--content-width) !important;
  margin: 0 auto 24px !important; width: 100% !important;
  display: flex !important; gap: 4px !important;
  align-items: center !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 28px !important; background: var(--bg) !important;
  padding: 4px 8px 4px 4px !important;
}
.composer-wrap:focus-within { border-color: var(--border-focus) !important; }
.composer-wrap * { box-shadow: none !important; }

#msg-input { flex: 1 !important; border: none !important; background: transparent !important; box-shadow: none !important; min-width: 0 !important; }
#msg-input * { background: transparent !important; border: none !important; box-shadow: none !important; }
#msg-input label { display: none !important; }
#msg-input textarea {
  font-family: inherit !important; font-size: 15px !important;
  height: 48px !important; border: none !important; border-radius: 0 !important;
  background: transparent !important; padding: 12px 4px !important;
  resize: none !important; box-shadow: none !important; width: 100% !important;
  line-height: 24px !important; outline: none !important; color: var(--text-strong) !important;
}

/* ── Upload button (in composer) ────────────────────── */
#upload-btn {
  flex-shrink: 0 !important; background: transparent !important;
  border: none !important; color: rgba(0,0,0,0.35) !important;
  font-size: 18px !important; font-weight: 300 !important; cursor: pointer !important;
  width: 32px !important; height: 32px !important; min-width: 32px !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  padding: 0 !important; margin: 0 !important;
}
#upload-btn:hover { color: var(--text-base) !important; }
#upload-btn button, #upload-btn .gr-button {
  background: transparent !important; border: none !important; color: inherit !important;
  font-size: 18px !important; font-weight: 300 !important; padding: 0 !important;
  margin: 0 !important; box-shadow: none !important; line-height: 1 !important;
}

/* ── Send button ────────────────────────────────────── */
#send-btn {
  flex-shrink: 0 !important; background: rgba(0,0,0,0.85) !important;
  color: #fff !important; border: none !important; border-radius: 24px !important;
  padding: 8px 18px !important; font-size: 13px !important; font-weight: 500 !important;
  cursor: pointer !important; box-shadow: none !important; margin: 0 !important; line-height: 1.3 !important;
}
#send-btn:hover { background: #000 !important; }
#send-btn button, #send-btn .gr-button {
  background: transparent !important; color: #fff !important; border: none !important;
  font-size: 13px !important; font-weight: 500 !important; padding: 0 !important; box-shadow: none !important;
}

/* ── Global button overrides ────────────────────────── */
button, .gr-button { font-family: inherit !important; box-shadow: none !important; }
.gr-button-primary { background: rgba(0,0,0,0.85) !important; color: #fff !important; border: none !important; }
.gr-button-secondary { background: transparent !important; color: var(--text-base) !important; border: 1px solid var(--border-light) !important; }

/* ── Scrollbar ──────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.25); }
"""

# ── helpers ─────────────────────────────────────────────

def _build_course_choices():
    """返回课程下拉列表选项。"""
    courses = list_courses()
    return ["全部"] + courses


def _build_welcome(course: str | None) -> str:
    """Generate ChatGPT-style welcome with clickable example prompts."""
    if not course or course == "全部":
        examples = [
            "总结一下课程的主要内容",
            "出5道选择题测试我的理解",
            "解释一下课程的核心概念",
            "查看我的薄弱点",
        ]
        items = "\n".join(
            f'<div class="example-item" onclick="var t=document.querySelector(\'#msg-input textarea\');if(t){{t.value=\'{ex}\';t.dispatchEvent(new Event(\'input\',{{bubbles:true}}));t.focus();}}">{ex}</div>'
            for ex in examples
        )
        return (
            '<div style="text-align:center;">'
            '<div style="font-size:18px;font-weight:500;color:rgba(0,0,0,0.8);margin-bottom:6px;">今天想学什么？</div>'
            '<div style="font-size:14px;color:rgba(0,0,0,0.35);margin-bottom:24px;">选择示例问题或直接输入你想了解的内容</div>'
            + items +
            '</div>'
        )

    from ingestion.indexer import list_sections
    sources = list_sources(course)
    sections = list_sections(course)
    memory = get_summary(course)

    lines = [f"{course}"]
    lines.append(f"已上传 {len(sources)} 个文件。")

    if sections:
        lines.append("\n检测到的章节：")
        for s in sections:
            learned = " ✓" if s in memory.get("chapters_learned", []) else ""
            lines.append(f"  {s}{learned}")

    if memory.get("weak_count", 0) > 0:
        lines.append(f"\n{memory['weak_count']} 个薄弱知识点待加强。")

    return "\n".join(lines)


def _format_sources_detail(docs, metas, scores) -> str:
    """生成折叠的检索来源 HTML details/summary。"""
    if not docs:
        return ""
    lines = ["\n<details>\n<summary>📎 检索来源 ({n}个片段)</summary>\n".format(n=len(docs))]
    for i, (doc, meta, score) in enumerate(zip(docs, metas, scores)):
        src = meta.get("source", "?")
        page = meta.get("page", 0)
        section = meta.get("section", "")
        preview = doc[:120].replace("\n", " ")
        source_info = f"[{src}]"
        if section:
            source_info += f" · 章节: {section}"
        if page:
            source_info += f" · 第{page}页"
        lines.append(
            f"- **片段{i + 1}** "
            f"(相似度: {score:.3f}) {source_info}: {preview}..."
        )
    lines.append("\n</details>")
    return "\n".join(lines)


def _detect_msg_type(message: str) -> str:
    msg = message.strip()
    if msg.startswith("/总结") or msg.startswith("/章节"):
        return "chapter"
    elif msg.startswith("/复习"):
        return "review"
    elif msg.startswith("/出题"):
        return "exam"
    elif msg.startswith("/解释"):
        return "explain"
    return "qa"


def _save_qa_record(question: str, answer: str, course: str | None,
                    sources: list[str] | None = None, msg_type: str = "qa"):
    try:
        save_record(question=question, answer=answer, course=course or "",
                    sources=sources, msg_type=msg_type)
    except Exception:
        pass


def _list_sections_safe(course):
    from ingestion.indexer import list_sections
    try:
        return list_sections(course)
    except Exception:
        return []


def _course_count(course):
    stats = get_course_stats()
    return stats.get(course, 0)


# ── chat callbacks ──────────────────────────────────────

def send_message(message, chat_history, chat_course):
    if not message.strip():
        yield chat_history, ""
        return

    course_name = None if chat_course == "全部" else chat_course

    # Step 1: Context
    context = get_context_prompt(course_name)

    # Step 2: Intent routing
    intent = route_intent(message, context_prompt=context)

    # ── help ──
    if intent["intent"] == "help":
        reply = """## 📚 使用帮助

**直接说话就行，无需命令格式：**
- "总结第二章" → 生成章节总结
- "出5道选择题" → 自动出题
- "解释红黑树" → 知识点解释
- "标记XX为薄弱点" → 掌握度标记
- "我的薄弱点有哪些" → 查看薄弱点
- "有哪些文件" → 查看课程文件

支持的文件操作：上传 PDF/PPT/PPTX，删除课程/文件。"""
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # ── history ──
    if intent["intent"] == "history":
        target = intent.get("chapter") or course_name or ""
        records = get_history(course=target, limit=20)
        if not records:
            reply = "暂无学习记录。"
        else:
            lines = [f"## 📝 学习记录 ({target or '全部课程'})\n"]
            for r in records:
                ts = r["timestamp"][:19].replace("T", " ")
                c = r.get("course", "")
                q = r["question"][:80]
                lines.append(f"- **{ts}** [{c}] {q}")
            reply = "\n".join(lines)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # ── mark_mastery ──
    if intent["intent"] == "mark_mastery":
        concept = intent.get("concept", "")
        level = intent.get("mastery_level", "unmarked")
        if not concept:
            reply = "请说明要标记哪个知识点，例如：\"标记死锁为薄弱点\""
        else:
            mark_mastery(course_name, concept, level)
            level_label = {"mastered": "✅ 已掌握", "weak": "⚠️ 薄弱点", "unmarked": "▸ 未标记"}
            reply = f"已将「{concept}」标记为：{level_label.get(level, level)}"
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type="mastery")
        yield chat_history, ""
        return

    # ── course_mgmt ──
    if intent["intent"] == "course_mgmt":
        sources = list_sources(course_name) if course_name else []
        from ingestion.indexer import list_sections
        sections = list_sections(course_name) if course_name else []
        lines = [f"## 📁 课程「{course_name or '全部'}」\n"]
        if sources:
            lines.append("**文件列表：**")
            for s in sources:
                cnt = get_source_count(course_name, s)
                lines.append(f"- {s} ({cnt} chunks)")
        else:
            lines.append("暂无文件。")
        if sections:
            lines.append("\n**章节：**")
            for s in sections:
                lines.append(f"- {s}")
        lines.append("\n💡 上传 PDF：点击 📎 按钮")
        reply = "\n".join(lines)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # ── chapter_summary ──
    if intent["intent"] == "chapter_summary":
        chapter = intent.get("chapter") or message
        if not course_name:
            reply = "请先在顶部选择一个课程。"
        else:
            reply = generate_chapter_summary(course_name, chapter)
            if "未在课程" not in reply:
                record_chapter(course_name, chapter)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type="chapter")
        yield chat_history, ""
        return

    # ── exam ──
    if intent["intent"] == "exam":
        if not course_name:
            reply = "请先在顶部选择一个课程。"
        else:
            chapter = intent.get("chapter") or ""
            qtype = intent.get("question_type") or "mixed"
            count = intent.get("count") or 5
            reply = generate_exam_questions(course_name, section=chapter,
                                            question_type=qtype, count=count)
            if chapter and "未在课程" not in reply:
                record_chapter(course_name, chapter)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type="exam")
        yield chat_history, ""
        return

    # ── explain ──
    if intent["intent"] == "explain":
        concept = intent.get("concept") or message
        if not course_name:
            reply = "请先在顶部选择一个课程。"
        else:
            reply = explain_concept(course_name, concept)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type="explain")
        yield chat_history, ""
        return

    # ── default: qa ──
    docs, metas, scores = search(message, course=course_name)

    if not docs:
        reply = "未在当前课程资料中找到相关内容。\n\n"
        if course_name:
            secs = _list_sections_safe(course_name)
            if secs:
                reply += "**该课程已有章节：**\n"
                for s in secs:
                    reply += f"- {s}\n"
                reply += "\n建议：\n- 换个说法试试\n- 切换到「全部」检索\n- 上传更多课程资料"
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": ""})
    full_answer = ""
    try:
        for chunk in generate_stream(message, docs, metas):
            full_answer += chunk
            chat_history[-1]["content"] = full_answer
            yield chat_history, ""
    except Exception:
        full_answer = generate(message, docs, metas)
        chat_history[-1]["content"] = full_answer
        yield chat_history, ""

    sources_html = _format_sources_detail(docs, metas, scores)
    chat_history[-1]["content"] = full_answer + sources_html

    sources_list = []
    for meta in metas:
        src = meta.get("source", "?")
        page = meta.get("page", 0)
        info = src
        if page:
            info += f" (第{page}页)"
        sources_list.append(info)
    _save_qa_record(message, full_answer, course_name, sources=sources_list)

    yield chat_history, ""


def clear_chat():
    return [], ""


# ── document management callbacks ────────────────────────

def upload_files_handler(files, course):
    PPT_EXTENSIONS = {".ppt", ".pptx"}
    ALL_SUPPORTED = {".pdf", ".pptx", ".ppt"}

    if files is None:
        return "请先选择文件", gr.update()
    if not course or course == "全部":
        return "请先选择或创建一个课程", gr.update()

    if not isinstance(files, list):
        files = [files]

    total_chunks = 0
    errors = []
    success_count = 0

    for f in files:
        path = f.name
        ext = os.path.splitext(path)[1].lower()
        source_name = os.path.basename(path)

        if ext not in ALL_SUPPORTED:
            errors.append(f"{source_name}: 不支持的文件类型 ({ext})")
            continue

        pdf_path = path
        temp_dir = None

        try:
            if ext in PPT_EXTENSIONS:
                pdf_path, temp_dir = convert_pptx_to_pdf(path)

            pages = load_pdf_with_meta(pdf_path)
            for p in pages:
                p["text"] = clean_text(p["text"])
            chunk_dicts = chunk_text_with_meta(pages)
            chunk_texts = [c["text"] for c in chunk_dicts]
            chunk_metas = [{"page": c["page"], "section": c["section"]} for c in chunk_dicts]

            index_chunks(chunk_texts, course=course, source=source_name,
                         chunk_metas=chunk_metas)
            total_chunks += len(chunk_texts)
            success_count += 1
        except Exception as e:
            errors.append(f"{source_name}: {e}")
        finally:
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    msg = f"入库完成: {success_count}/{len(files)} 个文件, {total_chunks} 个 chunk"
    if errors:
        msg += f"\n⚠️ {len(errors)} 个失败: " + "; ".join(errors)

    return msg, gr.update(choices=_build_course_choices())


def delete_course_handler(course):
    if not course or course == "全部":
        return "请选择要删除的课程", gr.update(choices=_build_course_choices(), value="全部")
    delete_course(course)
    return f"已删除课程「{course}」", gr.update(choices=_build_course_choices(), value="全部")


# ── UI ──────────────────────────────────────────────────

# =============================================================
#  UI — ChatGPT Workspace Layout
# =============================================================

with gr.Blocks(title="Echo") as demo:

    # ── Sidebar (240px, course list only) ──────────────

    with gr.Column(elem_classes=["sidebar"]):
        gr.HTML(
            '<div style="font-size:14px;font-weight:600;color:rgba(0,0,0,0.85);'
            'padding:4px 0;margin-bottom:20px;">Echo</div>'
        )

        course_radio = gr.Radio(
            label="课程",
            choices=[],
            value=None,
            interactive=True,
            elem_id="course-list",
        )

        # New course: inline expand
        new_course_link = gr.Button(
            "+ 新建课程", variant="secondary", size="sm",
            visible=True,
        )
        with gr.Row(visible=False) as new_course_row:
            new_course_tb = gr.Textbox(
                placeholder="课程名称",
                scale=1,
                show_label=False,
            )
            cancel_new_btn = gr.Button("取消", size="sm", scale=0)
            confirm_new_btn = gr.Button("创建", variant="primary", size="sm", scale=0)

    # ── Main area ─────────────────────────────────────

    with gr.Column(elem_classes=["main-area"]):
        chatbot = gr.Chatbot(
            label="",
            height="100%",
            elem_classes=["chatbot"],
            show_label=False,
            value=[],
        )

        with gr.Row(elem_classes=["composer-wrap"]):
            upload_btn = gr.UploadButton(
                "+",
                file_types=[".pdf", ".pptx", ".ppt"],
                file_count="multiple",
                variant="secondary",
                elem_id="upload-btn",
                size="sm",
            )
            msg_input = gr.Textbox(
                label="",
                placeholder="输入你的问题...",
                scale=1,
                elem_id="msg-input",
            )
            send_btn = gr.Button("发送", variant="primary", elem_id="send-btn")

    # ── State ─────────────────────────────────────────

    current_course_state = gr.State("全部")

    # ── Events ─────────────────────────────────────────

    def _on_load():
        choices = _build_course_choices()
        welcome = _build_welcome(None)
        return (
            gr.update(choices=choices, value=None),
            [{"role": "assistant", "content": welcome}],
        )

    demo.load(fn=_on_load, outputs=[course_radio, chatbot])

    # Course selection
    def _on_course_select(course):
        if course is None:
            course = "全部"
        if course == "全部":
            welcome = _build_welcome(None)
            return [{"role": "assistant", "content": welcome}], course
        else:
            info = _build_welcome(course)
            return [{"role": "assistant", "content": info}], course

    course_radio.change(
        fn=_on_course_select,
        inputs=[course_radio],
        outputs=[chatbot, current_course_state],
    )

    # New course: show/hide inline input
    def _show_new_course():
        return gr.update(visible=False), gr.update(visible=True), ""

    new_course_link.click(
        fn=_show_new_course,
        outputs=[new_course_link, new_course_row, new_course_tb],
    )

    def _cancel_new_course():
        return gr.update(visible=True), gr.update(visible=False), ""

    cancel_new_btn.click(
        fn=_cancel_new_course,
        outputs=[new_course_link, new_course_row, new_course_tb],
    )

    def _create_course(name):
        name = (name or "").strip()
        if not name or name == "全部":
            return gr.update(visible=True), gr.update(visible=False), "", gr.update()
        if name in list_courses():
            return gr.update(visible=True), gr.update(visible=False), "", gr.update(choices=_build_course_choices(), value=name)
        choices = _build_course_choices()
        if name not in choices:
            choices.append(name)
        return gr.update(visible=True), gr.update(visible=False), "", gr.update(choices=choices, value=name)

    confirm_new_btn.click(
        fn=_create_course,
        inputs=[new_course_tb],
        outputs=[new_course_link, new_course_row, new_course_tb, course_radio],
    )

    new_course_tb.submit(
        fn=_create_course,
        inputs=[new_course_tb],
        outputs=[new_course_link, new_course_row, new_course_tb, course_radio],
    )

    # Upload
    def _on_upload(files):
        course = current_course_state.value
        if not course or course == "全部":
            return "请先在左侧选择一个课程，再上传文件", gr.update()
        try:
            msg, radio_update = upload_files_handler(files, course)
            return msg or "上传完成", radio_update
        except Exception as e:
            return f"上传失败: {e}", gr.update()

    upload_btn.upload(
        fn=_on_upload,
        inputs=[upload_btn],
        outputs=[msg_input, course_radio],
    )

    # Chat
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, current_course_state],
        outputs=[chatbot, msg_input],
    )

    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, current_course_state],
        outputs=[chatbot, msg_input],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=10)
    demo.launch(
        ssr_mode=False,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            font=gr.themes.GoogleFont("Inter"),
        ),
    )
