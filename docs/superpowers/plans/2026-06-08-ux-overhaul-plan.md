# UX 全面重构 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将学习助手从左右分栏+斜杠命令的 CLI 风格改造为纯聊天式交互，新增自然语言意图路由和知识点记忆追踪。

**Architecture:** 保持 Gradio 前端和现有 RAG 基础设施不变，新增 `router/`（意图分类）和 `memory/`（记忆追踪）两个服务模块，重构 `app_web.py` 为纯聊天布局。`llm/learning_assistant.py` 砍掉课程总结和复习提纲。

**Tech Stack:** Gradio 6.x, DashScope (qwen-turbo), ChromaDB, Python 3.x

---

## File Map

| 文件 | 动作 | 职责 |
|------|------|------|
| `memory/__init__.py` | 新建 | 包初始化 |
| `memory/tracker.py` | 新建 | 章节记录 + 知识点掌握度 + 上下文注入 |
| `router/__init__.py` | 新建 | 包初始化 |
| `router/intent_router.py` | 新建 | LLM 意图分类 + 斜杠命令兜底 |
| `llm/learning_assistant.py` | 修改 | 删除 `generate_course_summary` 和 `generate_review_outline` |
| `app_web.py` | 重构 | 纯聊天界面，集成 router + tracker |
| `storage/course_memory.json` | 新建 | tracker 的持久化存储（首次运行时自动创建） |

---

### Task 1: 创建 `memory/tracker.py` — 记忆追踪模块

**Files:**
- Create: `memory/__init__.py`
- Create: `memory/tracker.py`

- [ ] **Step 1: 创建包初始化文件**

```python
# memory/__init__.py
```

内容为空文件。

- [ ] **Step 2: 创建 tracker.py**

```python
# memory/tracker.py
# -*- coding: utf-8 -*-
"""
课程记忆追踪 — 章节学习记录 + 知识点掌握度标记。

存储位置: storage/course_memory.json
"""
import json
import os
from datetime import datetime


MEMORY_PATH = os.path.join("storage", "course_memory.json")


def _load() -> dict:
    """加载记忆文件，文件不存在或损坏时返回空 dict。"""
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # 损坏 → 备份后返回空
        backup = MEMORY_PATH + ".bak"
        try:
            os.rename(MEMORY_PATH, backup)
        except OSError:
            pass
        return {}


def _save(data: dict) -> None:
    """保存记忆文件，写入失败时静默忽略。"""
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def _ensure_course(data: dict, course: str) -> dict:
    """确保课程条目存在，返回该课程的 dict。"""
    if course not in data:
        data[course] = {
            "chapters_learned": [],
            "mastery": {},
            "last_active": "",
        }
    return data[course]


# ── 公开 API ──


def record_chapter(course: str, chapter: str) -> None:
    """记录某课程的一个章节已被学习（去重）。"""
    if not course or not chapter:
        return
    data = _load()
    entry = _ensure_course(data, course)
    if chapter not in entry["chapters_learned"]:
        entry["chapters_learned"].append(chapter)
    entry["last_active"] = datetime.now().isoformat()
    _save(data)


def mark_mastery(course: str, concept: str, level: str) -> None:
    """
    标记一个知识点的掌握程度。

    level 取值: "mastered" | "weak" | "unmarked"
    """
    if not course or not concept:
        return
    if level not in ("mastered", "weak", "unmarked"):
        return
    data = _load()
    entry = _ensure_course(data, course)
    entry["mastery"][concept] = level
    entry["last_active"] = datetime.now().isoformat()
    _save(data)


def get_weak_concepts(course: str) -> list[str]:
    """获取某课程所有标记为薄弱的知识点列表。"""
    data = _load()
    entry = data.get(course, {})
    return [k for k, v in entry.get("mastery", {}).items() if v == "weak"]


def get_chapters_learned(course: str) -> list[str]:
    """获取某课程已学习的章节列表。"""
    data = _load()
    entry = data.get(course, {})
    return entry.get("chapters_learned", [])


def get_context_prompt(course: str | None) -> str:
    """
    生成注入 LLM 的上下文摘要（~几十 token）。

    返回空字符串表示无上下文。
    """
    if not course:
        return ""

    data = _load()
    entry = data.get(course, {})
    chapters = entry.get("chapters_learned", [])
    weak = [k for k, v in entry.get("mastery", {}).items() if v == "weak"]

    if not chapters and not weak:
        return ""

    parts = [f"当前课程：{course}"]
    if chapters:
        parts.append(f"已学章节：{', '.join(chapters[-10:])}")
    if weak:
        parts.append(f"薄弱知识点（建议加强）：{', '.join(weak)}")

    return "\n".join(parts)


def get_summary(course: str) -> dict:
    """获取某课程的完整记忆摘要，供 UI 展示。"""
    data = _load()
    entry = data.get(course, {})
    return {
        "chapters_learned": entry.get("chapters_learned", []),
        "mastery": entry.get("mastery", {}),
        "weak_count": len(get_weak_concepts(course)),
        "last_active": entry.get("last_active", ""),
    }
```

- [ ] **Step 3: 验证模块可导入**

```bash
.venv/Scripts/python -c "from memory.tracker import record_chapter, mark_mastery, get_context_prompt, get_summary; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add memory/__init__.py memory/tracker.py
git commit -m "feat: add memory/tracker module for chapter tracking and mastery"
```

---

### Task 2: 创建 `router/intent_router.py` — 意图路由模块

**Files:**
- Create: `router/__init__.py`
- Create: `router/intent_router.py`

- [ ] **Step 1: 创建包初始化文件**

```python
# router/__init__.py
```

内容为空文件。

- [ ] **Step 2: 创建 intent_router.py**

```python
# router/intent_router.py
# -*- coding: utf-8 -*-
"""
意图路由器 — 将用户自然语言消息分类为功能意图。

三层策略：
  1. 斜杠命令正则匹配 → 不消耗 LLM 调用
  2. LLM 意图分类 (qwen-turbo) → 主路径
  3. 降级为 qa → 兜底
"""
import json
import re

from llm.dashscope_llm import generate


INTENT_PROMPT = """你是学习助手的意图路由器。分析用户消息，返回 JSON。

意图类型：
- "qa": 一般问答，如"什么是进程"、"第二章讲了什么"
- "chapter_summary": 要求总结某个章节，如"总结第二章"、"第二章重点"
- "exam": 要求出题，如"出5道选择"、"给我出几道关于B树的判断题"
- "explain": 要求解释概念，如"解释红黑树"、"什么是死锁"
- "mark_mastery": 标记掌握度，如"标记死锁为薄弱点"、"进程同步我学会了"
- "course_mgmt": 课程管理，如"有哪些文件"、"上传PDF"

参数说明：
- chapter: 章节名（chapter_summary 时提取）
- concept: 概念名（explain / mark_mastery 时提取）
- question_type: "choice"/"truefalse"/"shortanswer"/"mixed"，仅 exam
- count: 出题数量（1-20），仅 exam
- mastery_level: "mastered"/"weak"/"unmarked"，仅 mark_mastery

上下文：
{context}

用户消息：{message}

只返回 JSON，不要其他内容。无法判断时 intent 为 "qa"。
JSON:"""


# ── 斜杠命令正则（Layer 1 兜底）──

_SLASH_PATTERNS = [
    (r"^/(?:章节|chapter)\s+(.+)", "chapter_summary"),
    (r"^/(?:出题|exam)\s+(.*)", "exam"),
    (r"^/(?:解释|explain)\s+(.+)", "explain"),
    (r"^/(?:帮助|help|\?)$", "help"),
    (r"^/(?:历史)\s*(.*)", "history"),
]


def _parse_slash_command(message: str) -> dict | None:
    """斜杠命令正则匹配，命中返回 intent dict，否则返回 None。"""
    msg = message.strip()
    for pattern, intent in _SLASH_PATTERNS:
        m = re.match(pattern, msg)
        if m:
            result = {"intent": intent, "chapter": None, "concept": None,
                      "question_type": None, "count": None, "mastery_level": None}
            arg = m.group(1).strip() if m.lastindex and m.group(1) else ""

            if intent == "chapter_summary":
                result["chapter"] = arg if arg else None
            elif intent == "explain":
                result["concept"] = arg if arg else None
            elif intent == "exam":
                # 复用 app_web 中的出题参数解析逻辑会带来循环依赖，
                # 这里做简单解析：最后一个数字是数量，其余是知识点
                result["question_type"] = "mixed"
                result["count"] = 5
                if arg:
                    parts = arg.split()
                    if parts and parts[-1].isdigit():
                        result["count"] = max(1, min(int(parts[-1]), 20))
                        parts = parts[:-1]
                    # 题型检测
                    type_map = {"选择": "choice", "选择题": "choice",
                                "判断": "truefalse", "判断题": "truefalse",
                                "简答": "shortanswer", "简答题": "shortanswer"}
                    if parts and parts[-1] in type_map:
                        result["question_type"] = type_map[parts[-1]]
                        parts = parts[:-1]
                    if parts:
                        result["chapter"] = " ".join(parts)
            elif intent == "history":
                result["chapter"] = arg if arg else None

            return result
    return None


def _classify_by_llm(message: str, context: str) -> dict:
    """用 qwen-turbo 做意图分类，返回 intent dict。异常时降级为 qa。"""
    prompt = INTENT_PROMPT.format(context=context, message=message)

    try:
        response = generate(prompt, docs=[""], metas=[{}])
    except Exception:
        return _qa_fallback()

    # 提取 JSON
    try:
        # 去掉可能的 markdown 代码块标记
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        result = json.loads(text)
        result.setdefault("chapter", None)
        result.setdefault("concept", None)
        result.setdefault("question_type", None)
        result.setdefault("count", None)
        result.setdefault("mastery_level", None)
        result.setdefault("intent", "qa")
        return result
    except (json.JSONDecodeError, ValueError):
        return _qa_fallback()


def _qa_fallback() -> dict:
    return {"intent": "qa", "chapter": None, "concept": None,
            "question_type": None, "count": None, "mastery_level": None}


# ── 公开 API ──


def route(message: str, course: str | None = None,
          context_prompt: str = "") -> dict:
    """
    路由用户消息到意图。

    返回:
      {
        "intent": str,        # qa|chapter_summary|exam|explain|mark_mastery|course_mgmt|help|history
        "chapter": str|None,
        "concept": str|None,
        "question_type": str|None,  # choice|truefalse|shortanswer|mixed
        "count": int|None,
        "mastery_level": str|None,  # mastered|weak|unmarked
      }
    """
    # Layer 1: 斜杠命令
    slash = _parse_slash_command(message)
    if slash:
        return slash

    # Layer 2: LLM 分类
    context = context_prompt or ""
    return _classify_by_llm(message, context)
```

- [ ] **Step 3: 验证模块可导入并测试斜杠命令**

```bash
.venv/Scripts/python -c "
from router.intent_router import route
# 测试斜杠命令兜底
r = route('/章节 第二章', course='操作系统')
print('slash:', r)
assert r['intent'] == 'chapter_summary'
assert r['chapter'] == '第二章'
print('OK')
"
```

Expected: `slash: {...} OK`

- [ ] **Step 4: Commit**

```bash
git add router/__init__.py router/intent_router.py
git commit -m "feat: add router/intent_router for natural language intent classification"
```

---

### Task 3: 清理 `llm/learning_assistant.py`

**Files:**
- Modify: `llm/learning_assistant.py`

- [ ] **Step 1: 删除 `generate_course_summary` 函数**

删除 `COURSE_SUMMARY_PROMPT` 常量和 `generate_course_summary()` 函数（`learning_assistant.py` 第 174-230 行）。

执行以下替换：删除从 `# ═══════════════════════════════════════════════════════════` 开始的任务5注释块到 `return generate(prompt, ...)` 结束的 `generate_course_summary` 函数。

```python
# 在 learning_assistant.py 中定位并删除以下内容：
# 1. 第 174 行 COUSE_SUMMARY_PROMPT 常量（约 20 行）
# 2. 第 196-230 行 generate_course_summary 函数
```

精确操作：删除从 `COURSE_SUMMARY_PROMPT` 到 `generate_course_summary` 函数 return 语句之后、下一个 `# ══` 分隔线之前的所有内容。

- [ ] **Step 2: 删除 `generate_review_outline` 函数**

删除 `REVIEW_OUTLINE_PROMPT` 常量和 `generate_review_outline()` 函数（原第 315-381 行）。

精确操作：删除从 `REVIEW_OUTLINE_PROMPT` 到 `generate_review_outline` 函数 return 语句之后的所有内容。

- [ ] **Step 3: 验证模块仍可导入**

```bash
.venv/Scripts/python -c "
from llm.learning_assistant import generate_chapter_summary, generate_exam_questions, explain_concept
print('OK - retained functions available')
"
```

Expected: `OK - retained functions available`

- [ ] **Step 4: Commit**

```bash
git add llm/learning_assistant.py
git commit -m "refactor: remove course_summary and review_outline from learning_assistant"
```

---

### Task 4: 重构 `app_web.py` — 纯聊天 UI 布局

**Files:**
- Modify: `app_web.py`

这是最大的改动。分步骤进行。

- [ ] **Step 1: 更新 import 区域**

替换 `app_web.py` 顶部的 import（第 1-25 行），添加新模块导入，移除不再需要的旧函数引用。

```python
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
```

- [ ] **Step 2: 删除旧的辅助函数**

删除以下不再需要的函数（它们是为左右分栏 UI 设计的）：
- `_build_stats_md()` — 统计面板（已无侧边栏）
- `_build_course_lists()` — 双课程选择器（改为单一选择器）
- `_build_file_choices()` — 文件下拉列表（改为聊天内管理）
- `_match_file_or_section()` — 移到 `_resolve_target` 或用 router 替代
- `_resolve_target()` — 被 `route_intent` 替代
- `_handle_learning_command()` — 被 `route_intent` 替代
- `_handle_exam_command()` — 被 router 替代
- `_detect_natural_exam()` — 被 router 替代
- `_detect_msg_type()` — 替换为新版本
- `_help_text()` — 保留但简化
- `refresh_ui()` — 替换为 `_build_top_bar()`
- `create_course()` — 替换
- `upload_files()` — 保留核心逻辑
- `_upload_result()` — 替换
- `_course_count()` — 保留（简单 helper）
- `delete_selected()` — 替换
- `on_course_change()` — 不需要（Gradio 组件直接绑定）
- `delete_file()` — 保留核心逻辑
- `_file_result()` — 保留
- `send_message()` — 重构
- `clear_chat()` — 保留

- [ ] **Step 3: 添加新的辅助函数**

在 `app_web.py` 中添加以下新函数：

```python
# ── new helpers ──


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
            "- \"总结一下第一章\"\n"
            "- \"出5道选择题\"\n"
            "- \"解释死锁的概念\""
        )

    sources = list_sources(course)
    from ingestion.indexer import list_sections
    sections = list_sections(course)
    memory = get_summary(course)

    lines = [f"## 📖 {course}\n"]
    lines.append(f"已上传 {len(sources)} 个文件。")

    if sections:
        lines.append(f"\n**检测到的章节：**")
        for s in sections:
            learned = " ✅" if s in memory.get("chapters_learned", []) else ""
            lines.append(f"- {s}{learned}")

    if memory.get("weak_count", 0) > 0:
        lines.append(f"\n⚠️ {memory['weak_count']} 个薄弱知识点待加强。")

    lines.append("\n💡 你可以直接说：\"总结第二章\" / \"出5道选择\" / \"解释关键概念\"")
    return "\n".join(lines)


def _format_sources_detail(docs, metas, scores) -> str:
    """生成折叠的检索来源 HTML。"""
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
    """从意图路由结果或消息中获取消息类型，供学习记录使用。"""
    # 先检查斜杠命令
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
    """保存问答记录（静默失败）。"""
    try:
        save_record(
            question=question,
            answer=answer,
            course=course or "",
            sources=sources,
            msg_type=msg_type,
        )
    except Exception:
        pass
```

- [ ] **Step 4: 重构 `send_message` — 主聊天处理器**

用以下代码替换现有的 `send_message` 函数：

```python
def send_message(message, chat_history, chat_course):
    """
    处理用户消息的完整流程：
      1. 上下文增强
      2. 意图路由
      3. 执行功能
      4. 记忆更新
      5. 返回 + 折叠来源
    """
    if not message.strip():
        yield chat_history, ""
        return

    course_name = None if chat_course == "全部" else chat_course

    # ── Step 1: 上下文增强 ──
    context = get_context_prompt(course_name)

    # ── Step 2: 意图路由 ──
    intent = route_intent(message, course=course_name, context_prompt=context)

    # ── 帮助命令 ──
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

    # ── 历史命令 ──
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

    # ── 掌握度标记 ──
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

    # ── 课程管理 ──
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
            lines.append(f"\n**章节：**")
            for s in sections:
                lines.append(f"- {s}")
        lines.append("\n💡 上传 PDF：点击输入框旁的 📎 按钮")
        reply = "\n".join(lines)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # ── 章节总结 ──
    if intent["intent"] == "chapter_summary":
        chapter = intent.get("chapter") or message
        if not course_name:
            reply = "请先在顶部选择一个课程。"
        else:
            reply = generate_chapter_summary(course_name, chapter)
            # 记忆更新
            if "未在课程" not in reply:
                record_chapter(course_name, chapter)
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        _save_qa_record(message, reply, course_name, msg_type="chapter")
        yield chat_history, ""
        return

    # ── 出题 ──
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

    # ── 知识点解释 ──
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

    # ── 默认：RAG 问答 (qa) ──
    docs, metas, scores = search(message, course=course_name)

    if not docs:
        reply = "未在当前课程资料中找到相关内容。\n\n"
        if course_name:
            secs = [s for s in _list_sections_safe(course_name)]
            if secs:
                reply += f"**该课程已有章节：**\n"
                for s in secs:
                    reply += f"- {s}\n"
            reply += "\n建议：\n- 换个说法试试\n- 切换到「全部」检索\n- 上传更多课程资料"
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": reply})
        yield chat_history, ""
        return

    # 流式生成
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

    # 追加折叠的检索来源
    sources_html = _format_sources_detail(docs, metas, scores)
    chat_history[-1]["content"] = full_answer + sources_html

    # 保存记录
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
```

- [ ] **Step 5: 添加 `_list_sections_safe` 和保留的上传/删除回调**

```python
def _list_sections_safe(course):
    """安全获取 sections 列表。"""
    from ingestion.indexer import list_sections
    try:
        return list_sections(course)
    except Exception:
        return []


def upload_files_handler(files, course):
    """上传文件回调（保留核心逻辑，简化返回值）。"""
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
    """删除课程回调。"""
    if not course or course == "全部":
        return "请选择要删除的课程", gr.update(choices=_build_course_choices(), value="全部")
    delete_course(course)
    return f"已删除课程「{course}」", gr.update(choices=_build_course_choices(), value="全部")


def quick_exam_click():
    """快捷按钮：填入出题提示。"""
    return "出5道关于"


def quick_weak_click():
    """快捷按钮：查看薄弱点。"""
    return "我的薄弱点有哪些"
```

- [ ] **Step 6: 重构 UI 构建代码（替换 `with gr.Blocks` 部分）**

用新的纯聊天布局替换 `app_web.py` 第 717 行起的所有 UI 构建代码：

```python
def clear_chat():
    return [], ""


# ── UI ──────────────────────────────────────────────────

css = """
.upload-btn { margin-top: 0.5em; }
"""

with gr.Blocks(title="大学课程学习助手", css=css) as demo:
    gr.Markdown("# 📚 大学课程学习助手")

    # ── 顶部工具栏 ──
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

    # ── 聊天区 ──
    chatbot = gr.Chatbot(label="对话", height=500, scale=1)

    with gr.Row():
        msg_input = gr.Textbox(
            label="输入你的问题",
            placeholder="直接说人话，比如：总结第二章 / 出5道选择 / 解释死锁...",
            scale=5,
        )
        send_btn = gr.Button("发送", variant="primary", scale=1)

    # ── 快捷按钮 ──
    with gr.Row():
        quick_exam_btn = gr.Button("📝 出题练习", size="sm")
        quick_weak_btn = gr.Button("⚠️ 薄弱点", size="sm")
        clear_btn = gr.Button("🗑 清空对话", size="sm")

    # ── 状态变量 ──
    current_course_state = gr.State("全部")

    # ── 事件绑定 ──

    # 页面加载
    def _on_load():
        choices = _build_course_choices()
        return gr.update(choices=choices, value="全部"), ""

    demo.load(fn=_on_load, outputs=[course_dd, top_msg])

    # 创建课程
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

    # 切换课程
    def _on_course_change(course):
        welcome = _build_welcome(course)
        return welcome, course

    course_dd.change(
        fn=_on_course_change,
        inputs=[course_dd],
        outputs=[top_msg, current_course_state],
    )

    # 上传文件
    def _on_upload(files, course):
        msg, dd_update = upload_files_handler(files, course)
        welcome = _build_welcome(course)
        return msg, dd_update, welcome

    upload_btn.upload(
        fn=_on_upload,
        inputs=[upload_btn, current_course_state],
        outputs=[top_msg, course_dd, top_msg],
    )

    # 删除课程
    def _on_delete(course):
        msg, dd_update = delete_course_handler(course)
        return msg, dd_update, ""

    delete_btn.click(
        fn=_on_delete,
        inputs=[current_course_state],
        outputs=[top_msg, course_dd, current_course_state],
    )

    # 聊天
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

    # 快捷按钮
    quick_exam_btn.click(
        fn=lambda: "出5道关于",
        outputs=[msg_input],
    )

    quick_weak_btn.click(
        fn=lambda: "我的薄弱点有哪些",
        outputs=[msg_input],
    )

    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_input],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=10)
    demo.launch(ssr_mode=False)
```

- [ ] **Step 7: 验证 app_web.py 语法正确**

```bash
.venv/Scripts/python -c "compile(open('app_web.py').read(), 'app_web.py', 'exec'); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 8: 验证模块导入成功**

```bash
.venv/Scripts/python -c "import app_web; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 9: Commit**

```bash
git add app_web.py
git commit -m "refactor: redesign app_web.py to pure chat UI with intent routing"
```

---

### Task 5: 端到端集成测试

**Files:**
- Create: `tests/test_integration.py`（如 tests 目录不存在则先创建）

- [ ] **Step 1: 创建测试目录和文件**

```bash
mkdir -p tests
```

```python
# tests/__init__.py
```

```python
# tests/test_integration.py
# -*- coding: utf-8 -*-
"""端到端集成测试：意图路由 + 记忆追踪 + 搜索"""
import sys
sys.path.insert(0, ".")

from router.intent_router import route
from memory.tracker import record_chapter, mark_mastery, get_context_prompt, get_summary


class TestIntentRouter:
    """测试意图路由（不调用 LLM 的斜杠命令路径）。"""

    def test_slash_chapter_summary(self):
        r = route("/章节 第二章", course="操作系统")
        assert r["intent"] == "chapter_summary"
        assert r["chapter"] == "第二章"

    def test_slash_explain(self):
        r = route("/解释 死锁", course="操作系统")
        assert r["intent"] == "explain"
        assert r["concept"] == "死锁"

    def test_slash_exam_with_count(self):
        r = route("/出题 选择 5", course="操作系统")
        assert r["intent"] == "exam"
        assert r["question_type"] == "choice"
        assert r["count"] == 5

    def test_slash_help(self):
        r = route("/帮助", course="操作系统")
        assert r["intent"] == "help"

    def test_normal_text_fallback(self):
        """非斜杠命令走 LLM，但若 LLM 不可达则降级为 qa"""
        r = route("这是一个普通问题", course="操作系统", context_prompt="")
        # 如果 LLM 正常，可能返回 qa 或其他；但至少不会崩溃
        assert "intent" in r
        assert r["intent"] in ("qa", "chapter_summary", "exam", "explain",
                               "mark_mastery", "course_mgmt")


class TestMemoryTracker:
    """测试记忆追踪模块。"""

    def test_record_chapter(self):
        record_chapter("test_course", "第一章")
        chapters = get_summary("test_course")["chapters_learned"]
        assert "第一章" in chapters

    def test_record_chapter_dedup(self):
        record_chapter("test_course", "第一章")
        record_chapter("test_course", "第一章")
        chapters = get_summary("test_course")["chapters_learned"]
        assert chapters.count("第一章") == 1

    def test_mark_mastery(self):
        mark_mastery("test_course", "死锁", "weak")
        summary = get_summary("test_course")
        assert summary["mastery"].get("死锁") == "weak"
        assert summary["weak_count"] >= 1

    def test_mark_mastery_mastered(self):
        mark_mastery("test_course", "进程同步", "mastered")
        summary = get_summary("test_course")
        assert summary["mastery"].get("进程同步") == "mastered"

    def test_context_prompt(self):
        record_chapter("test_course", "第一章")
        mark_mastery("test_course", "死锁", "weak")
        ctx = get_context_prompt("test_course")
        assert "test_course" in ctx
        assert "第一章" in ctx
        assert "死锁" in ctx

    def test_context_prompt_no_course(self):
        assert get_context_prompt(None) == ""
        assert get_context_prompt("") == ""

    def test_empty_course(self):
        summary = get_summary("nonexistent_course")
        assert summary["chapters_learned"] == []
        assert summary["mastery"] == {}


class TestSearchPipeline:
    """测试搜索流水线（需 Cosine 距离的 collection）。"""

    def test_search_basic(self):
        from retrieval.search import search
        docs, metas, scores = search("进程", course="萨达", top_k=3, min_score=0.0)
        assert len(docs) > 0, "搜索应返回结果（确保 collection 使用 cosine 距离）"
        for s in scores:
            assert 0.0 <= s <= 1.0, f"相似度应在 0~1 范围，实际: {s}"

    def test_search_with_section_filter(self):
        from retrieval.search import search
        docs, metas, scores = search(
            "进程", course="萨达",
            section="第二章    进程的描述与控制",
            top_k=3, min_score=0.0,
        )
        assert len(docs) > 0, "章节过滤搜索应返回结果"
```

- [ ] **Step 2: 运行测试**

```bash
.venv/Scripts/python -m pytest tests/test_integration.py -v 2>&1
```

Expected: All tests pass (非斜杠 LLM 测试可能因 API 问题而行为不同，不做硬断言)。

- [ ] **Step 3: 清理测试数据**

```bash
rm -f storage/course_memory.json
```

- [ ] **Step 4: Commit**

```bash
git add tests/__init__.py tests/test_integration.py
git commit -m "test: add integration tests for router, tracker, and search pipeline"
```

---

### Task 6: 最终验证 — 启动应用并手动测试

- [ ] **Step 1: 启动应用**

```bash
.venv/Scripts/python app_web.py
```

- [ ] **Step 2: 手动验证以下场景**

在浏览器中打开 Gradio URL，逐一验证：

| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 斜杠命令兜底 | 输入 `/章节 第二章` | 返回章节总结 |
| 自然语言章节总结 | 输入 "总结第二章" | 返回章节总结 |
| 自然语言出题 | 输入 "出5道选择" | 返回5道选择题 |
| 自然语言解释 | 输入 "解释进程的定义" | 返回解释 |
| 标记薄弱点 | 输入 "标记死锁为薄弱点" | 返回确认消息 |
| 查看薄弱点 | 输入 "我的薄弱点有哪些" | 列出薄弱点 |
| 普通问答 | 输入 "进程是什么" | RAG 问答 + 折叠来源 |
| 课程管理 | 输入 "有哪些文件" | 列出文件 |
| 切换课程 | 下拉菜单切换课程 | 显示欢迎消息 |
| 上传文件 | 点击上传按钮 | 入库成功 |
| 快捷按钮 | 点"出题练习" | 输入框填入提示文字 |
| 检索来源折叠 | 做一次问答 | 来源默认折叠，点击展开 |

- [ ] **Step 3: Commit any fixes**

如有问题，修复后提交。

---

## Self-Review

1. **Spec coverage check:**
   - ✅ 纯聊天 UI — Task 4 Step 6
   - ✅ 意图路由 — Task 2
   - ✅ 记忆追踪 — Task 1
   - ✅ 删除课程总结/复习提纲 — Task 3
   - ✅ 自然语言交互 — Task 4 Steps 4-6
   - ✅ 检索来源折叠 — Task 4 Step 3 (`_format_sources_detail`)
   - ✅ 快捷按钮 — Task 4 Step 6
   - ✅ 欢迎消息 — Task 4 Step 3 (`_build_welcome`)
   - ✅ 对话上下文注入 — Task 1 (`get_context_prompt`) + Task 4 Step 4
   - ✅ 斜杠命令兜底 — Task 2 (`_parse_slash_command`)
   - ✅ 错误处理降级 — Task 2 (`_qa_fallback`)
   - ✅ 存储迁移 — Task 1 (`_load` 损坏处理)

2. **Placeholder scan:** No TODOs, TBDs, or vague descriptions. All code is concrete.

3. **Type consistency:** `route()` returns dict with consistent keys across all call sites. `get_context_prompt()` returns `str`, consumed by `route()` as `context_prompt` parameter. `record_chapter()` and `mark_mastery()` signatures match their call sites in `send_message`.
