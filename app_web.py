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
    generate_course_summary,
    generate_chapter_summary,
    generate_review_outline,
    generate_exam_questions,
    explain_concept,
)
from utils.text_clean import clean_text
from utils.ppt_converter import convert_pptx_to_pdf
from storage.learning_log import save_record, get_history


# ── helpers ─────────────────────────────────────────────

def _build_stats_md():
    stats = get_course_stats()
    if not stats:
        return "暂无资料"
    lines = []
    total = sum(stats.values())
    lines.append(f"共 **{total}** 个 chunk")
    for course, n in sorted(stats.items()):
        lines.append(f"- {course}: {n}")
    return "\n".join(lines)


def _build_course_lists(extra=None):
    courses = list_courses()
    if extra and extra not in courses:
        courses = [extra] + courses
    choices = ["全部"] + courses
    return choices, choices


def _build_file_choices(course):
    if not course or course == "全部":
        return []
    choices = []
    for s in list_sources(course):
        n = get_source_count(course, s)
        choices.append(f"{s} ({n} chunks)")
    return choices


# ── learning record helpers ─────────────────────────────

def _detect_msg_type(message: str) -> str:
    """从命令消息中检测消息类型。"""
    msg = message.strip()
    if msg.startswith("/总结"):
        return "summary"
    elif msg.startswith("/章节"):
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
    """保存问答记录到学习日志（忽略保存异常）。"""
    try:
        save_record(
            question=question,
            answer=answer,
            course=course or "",
            sources=sources,
            msg_type=msg_type,
        )
    except Exception:
        pass  # 静默失败，不影响主流程


# ── learning assistant command handler ───────────────────

def _handle_learning_command(message: str, course: str | None) -> str | None:
    """
    处理学习助手斜杠命令。返回 None 表示不是命令，继续正常问答流程。

    支持的命令：
      /总结        — 课程总结
      /总结 课程名  — 指定课程总结
      /章节 章节名 — 章节总结
      /复习        — 复习提纲
      /出题 N       — 自动出题（N=数量，默认5）
      /出题 章节 N  — 指定章节出题
      /解释 知识点  — 知识点通俗解释
      /帮助        — 显示命令帮助
    """
    msg = message.strip()

    # ── /帮助 ──
    if msg in ["/帮助", "/help", "/?"]:
        return _help_text()

    # ── /历史 ──
    if msg.startswith("/历史"):
        target = msg[3:].strip() or (course if course else "")
        records = get_history(course=target, limit=20)
        if not records:
            return "暂无学习记录。"
        lines = [f"## 📝 学习记录 ({target or '全部课程'})\n"]
        for r in records:
            ts = r["timestamp"][:19].replace("T", " ")
            c = r.get("course", "")
            q = r["question"][:80]
            lines.append(f"- **{ts}** [{c}] {q}")
        return "\n".join(lines)

    # ── /总结 ──
    if msg.startswith("/总结"):
        target = msg[3:].strip()
        if target:
            return generate_course_summary(target)
        elif course:
            return generate_course_summary(course)
        else:
            return "请指定课程名称或先在左侧选择课程。\n\n用法：`/总结 课程名`"

    # ── /章节 ──
    if msg.startswith("/章节"):
        section = msg[3:].strip()
        if not section:
            return "请指定章节名称。\n\n用法：`/章节 红黑树`"
        if not course:
            return "请先在左侧选择课程。"
        return generate_chapter_summary(course, section)

    # ── /复习 ──
    if msg.startswith("/复习"):
        target = msg[3:].strip()
        if target:
            return generate_review_outline(target)
        elif course:
            return generate_review_outline(course)
        else:
            return "请指定课程名称或先在左侧选择课程。\n\n用法：`/复习 课程名`"

    # ── /出题 ──
    if msg.startswith("/出题"):
        args = msg[3:].strip()
        if not course:
            return "请先在左侧选择课程。"
        return _handle_exam_command(course, args)

    # ── /解释 ──
    if msg.startswith("/解释"):
        concept = msg[3:].strip()
        if not concept:
            return "请输入要解释的知识点。\n\n用法：`/解释 TCP三次握手`"
        if not course:
            return "请先在左侧选择课程。"
        return explain_concept(course, concept)

    # ── 自然语言出题：识别 "再出N道关于XX的题" ──
    exam_result = _detect_natural_exam(msg)
    if exam_result and course:
        topic, count, qtype = exam_result
        return generate_exam_questions(
            course, section=topic, question_type=qtype, count=count,
        )

    return None  # 不是命令，进入正常问答


def _handle_exam_command(course: str, args: str) -> str:
    """
    解析 /出题 命令的参数。

    支持格式：
      /出题 N              → N道混合题（全部课程）
      /出题 知识点 N       → N道混合题（指定知识点）
      /出题 选择 N         → N道选择题
      /出题 知识点 选择 N  → N道选择题（指定知识点）
      /出题 判断           → 5道判断题
      /出题 简答 10        → 10道简答题

    知识点可以是章节名、概念名或任何自定义关键词。
    """
    section = ""
    question_type = "mixed"
    count = 5

    if not args:
        return generate_exam_questions(course, count=count)

    parts = args.split()
    type_map = {
        "选择": "choice", "选择题": "choice",
        "判断": "truefalse", "判断题": "truefalse",
        "简答": "shortanswer", "简答题": "shortanswer",
        "混合": "mixed", "全部": "mixed",
    }

    # 从末尾开始解析：最后一段如果是数字=数量，倒数第二段如果是题型名=题型
    last_is_digit = parts[-1].isdigit() if parts else False

    if last_is_digit:
        count = max(1, min(int(parts[-1]), 20))
        parts = parts[:-1]  # 去掉数量

    # 检查最后一个词是否是题型
    if parts and parts[-1] in type_map:
        question_type = type_map[parts[-1]]
        parts = parts[:-1]  # 去掉题型

    # 剩余部分是知识点
    if parts:
        section = " ".join(parts)

    return generate_exam_questions(
        course, section=section, question_type=question_type, count=count,
    )


def _detect_natural_exam(msg: str) -> tuple[str, int, str] | None:
    """
    识别自然语言出题请求。

    匹配模式：
      - "再出N道关于XX的题"
      - "再出N道XX选择题"
      - "给我出N道关于XX的简答题"
      - "出N道XX判断题"
    """
    import re

    type_map = {
        "选择": "choice", "选择题": "choice",
        "判断": "truefalse", "判断题": "truefalse",
        "简答": "shortanswer", "简答题": "shortanswer",
    }

    patterns = [
        # "再出5道关于B树的题" / "给我出3道红黑树的选择题"
        r"(?:再|给[我你]|帮我)?\s*出\s*(\d+)\s*道\s*(?:关于)?\s*(.+?)\s*(?:的)?\s*(选择题|判断题|简答题|选择|判断|简答)?\s*(?:题|题目)?\s*$",
        # "出5道B树题" / "出3道选择"
        r"^出\s*(\d+)\s*道\s*(.+?)\s*(选择题|判断题|简答题|选择|判断|简答)?\s*(?:题|题目)?\s*$",
    ]

    for pat in patterns:
        m = re.match(pat, msg)
        if m:
            count = int(m.group(1))
            count = max(1, min(count, 20))
            topic = m.group(2).strip().rstrip("的。！？")
            qtype_raw = m.group(3) or ""
            qtype = type_map.get(qtype_raw, "mixed")
            return (topic, count, qtype)

    return None


def _help_text() -> str:
    """返回帮助信息。"""
    return """## 📚 学习助手命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/总结` | 生成当前课程总结 | `/总结` |
| `/总结 课程名` | 生成指定课程总结 | `/总结 数据结构` |
| `/章节 章节名` | 生成章节总结 | `/章节 红黑树` |
| `/复习` | 生成考前复习提纲 | `/复习` |
| `/出题 N` | 出N道混合题 | `/出题 10` |
| `/出题 知识点 N` | 指定知识点出题 | `/出题 B树 5` |
| `/出题 选择 N` | 指定题型出题 | `/出题 判断 3` |
| `/出题 知识点 选择 N` | 知识点+题型 | `/出题 红黑树 简答 3` |
| 自然语言出题 | 直接说出题需求 | `再出5道关于B树的题` |
| `/解释 知识点` | 通俗解释知识点 | `/解释 TCP三次握手` |
| `/帮助` | 显示本帮助 | `/帮助` |
| `/历史` | 查看学习记录 | `/历史` |
| `/历史 课程` | 查看指定课程记录 | `/历史 数据结构` |

💡 也可以直接输入问题，使用正常问答功能。"""


# ── document management callbacks ────────────────────────

def refresh_ui():
    radio_choices, dd_choices = _build_course_lists()
    return (
        gr.update(choices=radio_choices, value="全部"),
        gr.update(choices=dd_choices, value="全部"),
        _build_stats_md(),
        "",
    )


def create_course(name):
    name = name.strip()
    if not name:
        radio_choices, dd_choices = _build_course_lists()
        return (
            gr.update(choices=radio_choices),
            gr.update(choices=dd_choices),
            _build_stats_md(),
            "请输入课程名称",
        )
    if name == "全部":
        radio_choices, dd_choices = _build_course_lists()
        return (
            gr.update(choices=radio_choices),
            gr.update(choices=dd_choices),
            _build_stats_md(),
            "课程名不能为'全部'",
        )
    if name in list_courses():
        radio_choices, dd_choices = _build_course_lists()
        return (
            gr.update(choices=radio_choices),
            gr.update(choices=dd_choices),
            _build_stats_md(),
            f"课程 '{name}' 已存在",
        )
    # include new course in choices even though it has no chunks yet
    radio_choices, dd_choices = _build_course_lists(extra=name)
    return (
        gr.update(choices=radio_choices, value=name),
        gr.update(choices=dd_choices, value=name),
        _build_stats_md(),
        f"课程 '{name}' 已创建，请上传资料",
    )


def upload_files(files, course):
    # 支持的扩展名
    PPT_EXTENSIONS = {".ppt", ".pptx"}
    ALL_SUPPORTED = {".pdf", ".pptx", ".ppt"}

    if files is None:
        return _upload_result("请先选择 PDF / PPT / PPTX 文件")
    if not course or course == "全部":
        return _upload_result("请先在左侧选择或创建一个课程")

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
            # ── PPT/PPTX 文件：先转为 PDF ──
            if ext in PPT_EXTENSIONS:
                pdf_path, temp_dir = convert_pptx_to_pdf(path)

            # ── 使用带 metadata 的加载流程 ──
            pages = load_pdf_with_meta(pdf_path)

            # 清洗每页文本
            for p in pages:
                p["text"] = clean_text(p["text"])

            # 切分 chunk（保留页码和章节信息）
            chunk_dicts = chunk_text_with_meta(pages)

            # 转换为纯文本列表（向后兼容）
            chunk_texts = [c["text"] for c in chunk_dicts]
            # 提取 metadata 列表
            chunk_metas = [{"page": c["page"], "section": c["section"]} for c in chunk_dicts]

            index_chunks(chunk_texts, course=course, source=source_name,
                         chunk_metas=chunk_metas)
            total_chunks += len(chunk_texts)
            success_count += 1

        except Exception as e:
            errors.append(f"{source_name}: {e}")

        finally:
            # 清理临时 PDF 和目录
            if temp_dir and os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # 组装结果消息
    msg_parts = [
        f"入库完成: {success_count}/{len(files)} 个文件,"
        f" {total_chunks} 个 chunk |"
        f" 课程 '{course}' 总计: {_course_count(course)} chunks"
    ]
    if errors:
        msg_parts.append(f"\n⚠️ {len(errors)} 个文件处理失败:")
        for err in errors:
            msg_parts.append(f"  - {err}")

    return _upload_result("".join(msg_parts), course=course)


def _upload_result(msg, course=None):
    radio_choices, dd_choices = _build_course_lists()
    if course:
        fc = _build_file_choices(course)
        file_update = gr.update(choices=fc, value=None)
    else:
        file_update = gr.update()
    return (
        gr.update(choices=radio_choices),
        gr.update(choices=dd_choices),
        _build_stats_md(),
        msg,
        file_update,
    )


def _course_count(course):
    stats = get_course_stats()
    return stats.get(course, 0)


def delete_selected(course):
    if not course or course == "全部":
        radio_choices, dd_choices = _build_course_lists()
        return (
            gr.update(choices=radio_choices),
            gr.update(choices=dd_choices),
            _build_stats_md(),
            "请选择要删除的课程",
            gr.update(choices=[], value=None),
        )
    n = _course_count(course)
    delete_course(course)
    radio_choices, dd_choices = _build_course_lists()
    return (
        gr.update(choices=radio_choices, value="全部"),
        gr.update(choices=dd_choices, value="全部"),
        _build_stats_md(),
        f"已删除课程 '{course}'，清除 {n} 个 chunk",
        gr.update(choices=[], value=None),
    )


# ── file management callbacks ────────────────────────────

def on_course_change(course):
    """当选中课程变化时，更新文件列表"""
    return gr.update(choices=_build_file_choices(course), value=None)


def delete_file(course, file_entry):
    """删除课程中的某个文件"""
    if not course or course == "全部":
        return _file_result("请先选择课程")
    if not file_entry:
        return _file_result("请选择要删除的文件")

    # file_entry format: "filename.pdf (7 chunks)", extract filename
    source = file_entry.split(" (")[0]

    n = get_source_count(course, source)
    delete_source(course, source)

    # refresh file list
    sources = list_sources(course)
    new_choices = []
    for s in sources:
        cnt = get_source_count(course, s)
        new_choices.append(f"{s} ({cnt} chunks)")

    return (
        gr.update(choices=new_choices, value=None),
        f"已删除 '{source}'，清除 {n} 个 chunk",
    )


def _file_result(msg):
    return gr.update(), msg


# ── chat callbacks ──────────────────────────────────────

def send_message(message, chat_history, chat_course):
    """
    处理用户消息，支持流式输出。

    流程：
      1. 识别学习助手斜杠命令 → 非流式返回完整结果
      2. 正常问答 → 检索 + 流式生成 + 检索详情
    """
    if not message.strip():
        yield chat_history, ""
        return

    course_filter = None if chat_course == "全部" else chat_course
    course_name = chat_course if chat_course != "全部" else None

    # ── 学习助手命令处理（非流式）──
    reply = _handle_learning_command(message, course_name)
    if reply is not None:
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type=_detect_msg_type(message))
        yield chat_history, ""
        return

    # ── 正常问答流程 ──
    docs, metas, scores = search(message, course=course_filter)

    if not docs:
        from config import NO_RESULT_MSG
        reply = NO_RESULT_MSG
        if chat_course != "全部":
            reply += f"\n提示：当前检索范围限定在「{chat_course}」，可切换到「全部」试试。"
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # ── 构建检索详情（回答后追加）──
    detail = "\n\n---\n**检索详情**"
    if chat_course != "全部":
        detail += f" (@{chat_course})"
    detail += "\n"
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

        detail += (
            f"\n- **片段{i + 1}** "
            f"(相似度: {score:.3f}) {source_info}: {preview}..."
        )

    # ── 流式生成回答 ──
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": ""})
    full_answer = ""
    try:
        for chunk in generate_stream(message, docs, metas):
            full_answer += chunk
            chat_history[-1]["content"] = full_answer
            yield chat_history, ""
    except Exception:
        # Fallback: 非流式
        full_answer = generate(message, docs, metas)
        chat_history[-1]["content"] = full_answer
        yield chat_history, ""

    # 追加检索详情
    chat_history[-1]["content"] = full_answer + detail

    # 保存学习记录
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


# ── UI ──────────────────────────────────────────────────

with gr.Blocks(title="大学课程学习助手") as demo:
    gr.Markdown("# 📚 基于RAG的大学课程学习助手")

    with gr.Row():
        # ── left: course & document management ──
        with gr.Column(scale=1):
            gr.Markdown("### 课程管理")

            course_name = gr.Textbox(label="新建课程名称", placeholder="如：计算机网络")
            create_btn = gr.Button("创建课程")
            course_radio = gr.Radio(label="已选课程", choices=["全部"], value="全部")
            stats_display = gr.Markdown("暂无资料")
            refresh_btn = gr.Button("刷新", size="sm")

            gr.Markdown("---")
            gr.Markdown("### 上传资料")

            file_upload = gr.File(
                label="选择 PDF / PPT / PPTX 文件（可多选）",
                file_types=[".pdf", ".pptx", ".ppt"],
                file_count="multiple",
            )
            upload_btn = gr.Button("入库到当前课程", variant="primary")
            upload_msg = gr.Textbox(label="操作状态", interactive=False)

            gr.Markdown("---")
            gr.Markdown("### 文件管理")

            file_selector = gr.Dropdown(
                label="课程内文件", choices=[], interactive=True,
            )
            delete_file_btn = gr.Button("删除此文件", variant="stop")
            file_msg = gr.Textbox(label="文件操作状态", interactive=False)

            gr.Markdown("---")
            delete_btn = gr.Button("删除整个课程", variant="stop")

        # ── right: chat ──
        with gr.Column(scale=2):
            gr.Markdown("### 问答")

            chat_course_selector = gr.Dropdown(
                label="检索范围", choices=["全部"], value="全部",
            )
            chatbot = gr.Chatbot(label="对话", height=480)
            with gr.Row():
                msg_input = gr.Textbox(
                    label="输入问题",
                    placeholder="向你的知识库提问...",
                    scale=4,
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)
            clear_chat_btn = gr.Button("清空对话", size="sm")
            gr.Markdown("💡 **学习助手命令：** `/总结` `/章节 名称` `/复习` `/出题 N` `/解释 知识点` `/帮助`")

    # ── event wiring ──

    # page load
    demo.load(
        fn=refresh_ui,
        outputs=[course_radio, chat_course_selector, stats_display, upload_msg],
    )

    # course CRUD
    refresh_btn.click(
        fn=refresh_ui,
        outputs=[course_radio, chat_course_selector, stats_display, upload_msg],
    )

    create_btn.click(
        fn=create_course,
        inputs=course_name,
        outputs=[course_radio, chat_course_selector, stats_display, upload_msg],
    )

    upload_btn.click(
        fn=upload_files,
        inputs=[file_upload, course_radio],
        outputs=[course_radio, chat_course_selector, stats_display,
                 upload_msg, file_selector],
    )

    delete_btn.click(
        fn=delete_selected,
        inputs=course_radio,
        outputs=[course_radio, chat_course_selector, stats_display,
                 upload_msg, file_selector],
    )

    # file management
    course_radio.change(
        fn=on_course_change,
        inputs=course_radio,
        outputs=file_selector,
    )

    delete_file_btn.click(
        fn=delete_file,
        inputs=[course_radio, file_selector],
        outputs=[file_selector, file_msg],
    )

    # chat
    send_btn.click(
        fn=send_message,
        inputs=[msg_input, chatbot, chat_course_selector],
        outputs=[chatbot, msg_input],
    )

    msg_input.submit(
        fn=send_message,
        inputs=[msg_input, chatbot, chat_course_selector],
        outputs=[chatbot, msg_input],
    )

    clear_chat_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_input],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=10)
    demo.launch()
