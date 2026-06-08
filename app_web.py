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


# ── helpers ─────────────────────────────────────────────

def _build_course_choices():
    """返回课程下拉列表选项。"""
    courses = list_courses()
    return ["全部"] + courses


def _build_welcome(course: str | None) -> str:
    """生成切换课程后的欢迎消息。"""
    if not course or course == "全部":
        return (
            "## 📚 欢迎使用大学课程学习助手\n\n"
            "请选择一个课程，或上传 PDF 课件开始学习。\n\n"
            "💡 你可以直接输入问题，比如：\n"
            '- "总结一下第一章"\n'
            '- "出5道选择题"\n'
            '- "解释死锁的概念"'
        )

    from ingestion.indexer import list_sections
    sources = list_sources(course)
    sections = list_sections(course)
    memory = get_summary(course)

    lines = [f"## 📖 {course}\n"]
    lines.append(f"已上传 {len(sources)} 个文件。")

    if sections:
        lines.append("\n**检测到的章节：**")
        for s in sections:
            learned = " ✅" if s in memory.get("chapters_learned", []) else ""
            lines.append(f"- {s}{learned}")

    if memory.get("weak_count", 0) > 0:
        lines.append(f"\n⚠️ {memory['weak_count']} 个薄弱知识点待加强。")

    lines.append('\n💡 你可以直接说："总结第二章" / "出5道选择" / "解释关键概念"')
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

with gr.Blocks(title="大学课程学习助手") as demo:
    gr.Markdown("# 📚 大学课程学习助手")

    # ── Top toolbar ──
    with gr.Row():
        course_dd = gr.Dropdown(
            label="当前课程",
            choices=["全部"],
            value="全部",
            scale=3,
            interactive=True,
        )
        new_course_tb = gr.Textbox(
            label="新建课程",
            placeholder="输入课程名...",
            scale=2,
        )
        create_btn = gr.Button("创建", scale=1)
        upload_btn = gr.UploadButton(
            "📎 上传 PDF/PPT",
            file_types=[".pdf", ".pptx", ".ppt"],
            file_count="multiple",
            scale=1,
        )
        delete_btn = gr.Button("🗑 删除课程", variant="stop", scale=1)

    top_msg = gr.Markdown("")

    # ── Chat area ──
    chatbot = gr.Chatbot(label="对话", height=500)

    with gr.Row():
        msg_input = gr.Textbox(
            label="输入你的问题",
            placeholder="直接说人话，比如：总结第二章 / 出5道选择 / 解释死锁...",
            scale=5,
        )
        send_btn = gr.Button("发送", variant="primary", scale=1)

    # ── Quick buttons ──
    with gr.Row():
        quick_exam_btn = gr.Button("📝 出题练习", size="sm")
        quick_weak_btn = gr.Button("⚠️ 薄弱点", size="sm")
        clear_btn = gr.Button("🗑 清空对话", size="sm")

    # ── State ──
    current_course_state = gr.State("全部")

    # ── Events ──

    def _on_load():
        choices = _build_course_choices()
        return gr.update(choices=choices, value="全部"), ""

    demo.load(fn=_on_load, outputs=[course_dd, top_msg])

    def _create_course(name):
        name = name.strip()
        if not name:
            return gr.update(), gr.update(choices=_build_course_choices()), "请输入课程名称"
        if name == "全部":
            return gr.update(), gr.update(choices=_build_course_choices()), "课程名不能为'全部'"
        if name in list_courses():
            return gr.update(), gr.update(choices=_build_course_choices()), f"课程「{name}」已存在"
        choices = _build_course_choices()
        return "", gr.update(choices=choices, value=name), f"✅ 课程「{name}」已创建，请上传资料"

    create_btn.click(
        fn=_create_course,
        inputs=[new_course_tb],
        outputs=[new_course_tb, course_dd, top_msg],
    )

    def _on_course_change(course):
        welcome = _build_welcome(course)
        return welcome, course

    course_dd.change(
        fn=_on_course_change,
        inputs=[course_dd],
        outputs=[top_msg, current_course_state],
    )

    def _on_upload(files, course):
        msg, dd_update = upload_files_handler(files, course)
        welcome = _build_welcome(course)
        return msg, dd_update, welcome

    upload_btn.upload(
        fn=_on_upload,
        inputs=[upload_btn, current_course_state],
        outputs=[top_msg, course_dd, top_msg],
    )

    def _on_delete(course):
        msg, dd_update = delete_course_handler(course)
        return msg, dd_update, ""

    delete_btn.click(
        fn=_on_delete,
        inputs=[current_course_state],
        outputs=[top_msg, course_dd, current_course_state],
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

    # Quick buttons
    quick_exam_btn.click(fn=lambda: "出5道关于", outputs=[msg_input])
    quick_weak_btn.click(fn=lambda: "我的薄弱点有哪些", outputs=[msg_input])
    clear_btn.click(fn=clear_chat, outputs=[chatbot, msg_input])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=10)
    demo.launch(ssr_mode=False)
