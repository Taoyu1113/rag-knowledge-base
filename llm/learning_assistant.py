# -*- coding: utf-8 -*-
"""
学习助手模块 — 课程学习相关的 AI 功能。

包含：
  任务5: 课程总结    generate_course_summary()
  任务6: 章节总结    generate_chapter_summary()
  任务7: 复习提纲    generate_review_outline()
  任务8: 自动出题    generate_exam_questions()
  任务9: 知识点解释  explain_concept()

设计原则：
  - 每个功能都先检索相关知识，再构建专用 Prompt，最后调用 LLM
  - Prompt 针对大学生学习场景做了优化
  - 不照抄教材，用通俗语言解释
"""

from retrieval.search import search
from llm.dashscope_llm import generate
from ingestion.indexer import collection


def _get_course_chunks(course: str, max_chunks: int = 30) -> tuple[list[str], list[dict]]:
    """获取某门课程的所有 chunk（用于总结类功能）。"""
    # 从 ChromaDB 获取课程的所有文档
    results = collection.get(
        where={"course": course},
        include=["documents", "metadatas"],
        limit=max_chunks,
    )
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    return docs, metas


# ═══════════════════════════════════════════════════════════
# 任务5: 课程总结
# ═══════════════════════════════════════════════════════════

COURSE_SUMMARY_PROMPT = """你是一位大学课程辅导老师。请根据提供的课程资料片段，生成一份完整的课程总结。

要求：
1. **课程概览**：一两句话描述这门课主要学什么
2. **核心知识点**：列出5-10个最重要的知识点，每个用一句话说明
3. **重点章节**：指出哪几章最重要，为什么
4. **高频考点**：列出考试中最常考的内容（3-5个）
5. **学习路线**：给出推荐的学习顺序（分阶段，如：第一阶段→第二阶段→第三阶段）
6. **推荐复习顺序**：按重要性和难度排序

格式要求：使用 Markdown，标题用 ## 级别，列表清晰。

注意：
- 如果资料不足以覆盖以上所有方面，请说明"根据现有资料..."
- 不要编造资料中没有的内容
- 用语要适合大学生阅读"""


def generate_course_summary(course: str) -> str:
    """
    生成课程总结（任务5）。

    参数：
      course: 课程名称

    返回：
      Markdown 格式的课程总结
    """
    docs, metas = _get_course_chunks(course, max_chunks=40)

    if not docs:
        return (f"课程「{course}」暂无资料。\n\n"
                "请先上传该课程的 PDF 教材或课件。")

    # 用课程名作为查询词检索核心内容
    overview_docs, overview_metas, _ = search(course, course=course, top_k=8, enable_mmr=True)
    key_docs = overview_docs if overview_docs else docs

    prompt = (f"课程名称：{course}\n\n"
              f"课程资料（共 {len(docs)} 个片段，以下为关键片段）：\n\n")

    for i, (doc, meta) in enumerate(zip(key_docs, overview_metas if overview_docs else metas), 1):
        section = meta.get("section", "")
        page = meta.get("page", 0)
        header = f"[片段{i}]"
        if section:
            header += f" 章节: {section}"
        if page:
            header += f" 页码: {page}"
        prompt += f"{header}\n{doc[:1500]}\n\n"

    prompt += "\n请根据以上课程资料生成课程总结。"
    return generate(prompt, key_docs, overview_metas if overview_docs else metas)


# ═══════════════════════════════════════════════════════════
# 任务6: 章节总结
# ═══════════════════════════════════════════════════════════

CHAPTER_SUMMARY_PROMPT = """你是一位大学课程辅导老师。请根据提供的章节资料，生成一份详细的章节总结。

要求：
1. **章节简介**：用1-2句话概括这章讲什么
2. **重点知识**：列出3-6个本章最重要的知识点，每个附带简要说明
3. **难点知识**：指出本章最难理解的部分（1-3个），并解释为什么难
4. **考试常考内容**：指出哪些知识点最常出现在考试中
5. **关键概念**：列出本章必须掌握的5-10个关键术语/概念

格式要求：使用 Markdown，重要概念用 **粗体** 标出。

注意：
- 如果资料中找不到指定章节，请明确说明
- 不要编造资料中没有的内容"""


def generate_chapter_summary(course: str, section: str) -> str:
    """
    生成章节总结（任务6）。

    参数：
      course:   课程名称
      section:  章节名称/标题（如"红黑树"、"第三章"）

    返回：
      Markdown 格式的章节总结
    """
    if not section.strip():
        return "请指定要总结的章节名称。\n\n示例：`章节总结：红黑树`"

    # 用章节名称作为查询
    query = f"{section} 主要内容 知识点"
    docs, metas, _ = search(query, course=course, top_k=10, enable_mmr=True)

    if not docs:
        return (f"未在课程「{course}」中找到与「{section}」相关的内容。\n\n"
                f"请检查章节名称是否正确，或上传包含该章节的资料。")

    prompt = (f"课程：{course}\n"
              f"章节：{section}\n\n"
              f"章节相关资料：\n\n")

    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        page = meta.get("page", 0)
        header = f"[片段{i}]" + (f" 页码: {page}" if page else "")
        prompt += f"{header}\n{doc[:1500]}\n\n"

    prompt += f"\n请根据以上资料生成「{section}」的章节总结。"
    return generate(prompt, docs, metas)


# ═══════════════════════════════════════════════════════════
# 任务7: 复习提纲
# ═══════════════════════════════════════════════════════════

REVIEW_OUTLINE_PROMPT = """你是一位经验丰富的大学课程辅导老师。请根据课程资料，生成一份**考前复习提纲**。

要求：
1. **一级重点**（必考/高频）：列出3-5个最重要的知识点，每个标注掌握程度要求
2. **二级重点**（常考/可能考）：列出5-8个次重点
3. **学习顺序**：按重要性和知识依赖关系排列复习顺序
4. **预计复习时间**：给每个一级/二级重点估计复习时间（如"约30分钟"）
5. **考前建议**：给出一条最实用的考前冲刺建议

格式：
```
## 一级重点（必考）
| 序号 | 知识点 | 掌握要求 | 预计时间 |
|------|--------|----------|----------|
| 1    | ...    | ...      | ...      |

## 二级重点（常考）
| 序号 | 知识点 | 掌握要求 | 预计时间 |
|------|--------|----------|----------|

## 推荐复习顺序
1. ...
2. ...

## 考前建议
> ...
```

注意：
- 只包含资料中实际出现的内容
- 掌握要求描述要具体（如"能默写算法步骤"而非"掌握"）
- 时间估计要合理"""


def generate_review_outline(course: str) -> str:
    """
    生成复习提纲（任务7）。

    参数：
      course: 课程名称

    返回：
      Markdown 格式的复习提纲
    """
    docs, metas = _get_course_chunks(course, max_chunks=40)

    if not docs:
        return (f"课程「{course}」暂无资料。\n\n"
                "请先上传该课程的 PDF 教材或课件。")

    # 用"重点 考点 总结"检索关键内容
    key_docs, key_metas, _ = search(
        "重点 考点 总结 核心", course=course, top_k=10, enable_mmr=True,
    )
    use_docs = key_docs if key_docs else docs
    use_metas = key_metas if key_docs else metas

    prompt = (f"课程名称：{course}\n"
              f"为你整理了课程资料的关键片段，请据此生成考前复习提纲：\n\n")

    for i, (doc, meta) in enumerate(zip(use_docs, use_metas), 1):
        section = meta.get("section", "")
        header = f"[片段{i}]" + (f" ({section})" if section else "")
        prompt += f"{header}\n{doc[:1500]}\n\n"

    prompt += "\n请生成考前复习提纲。"
    return generate(prompt, use_docs, use_metas)


# ═══════════════════════════════════════════════════════════
# 任务8: 自动出题
# ═══════════════════════════════════════════════════════════

EXAM_QUESTIONS_PROMPT = """你是一位大学课程出题老师。请根据提供的课程资料，生成考试题目。

要求：
1. 题目必须基于提供的资料内容
2. 题目类型按需生成（选择题、判断题、简答题）
3. 每道题都要包含：题目、正确答案、解析、来源章节
4. 题目难度适中，适合大学生期末考试水平
5. 选择题提供4个选项（A/B/C/D）

输出格式：
```
## 选择题

**1. [题目]**
A. ...  B. ...  C. ...  D. ...
> ✅ 答案：X
> 📖 解析：...
> 📂 来源：[章节名]

## 判断题

**1. [题目]**
> ✅ 答案：正确/错误
> 📖 解析：...
> 📂 来源：[章节名]

## 简答题

**1. [题目]**
> ✅ 参考答案：...
> 📖 解析：...
> 📂 来源：[章节名]
```

注意：
- 题目要覆盖不同难度层次
- 解析要详细，帮助学生理解为什么对/错
- 不要出资料中没有的题目"""


def generate_exam_questions(
    course: str,
    section: str = "",
    question_type: str = "mixed",
    count: int = 5,
) -> str:
    """
    自动出题（任务8）。

    参数：
      course:        课程名称
      section:       章节（可选，如"第三章"、"红黑树"）
      question_type: 题型 — "choice"(选择), "truefalse"(判断),
                     "shortanswer"(简答), "mixed"(混合，默认)
      count:         题目数量

    返回：
      Markdown 格式的题目列表
    """
    # 构建查询
    if section:
        query = f"{section} 知识点 考点 重点"
    else:
        query = "重点 考点 关键概念 核心知识点"

    docs, metas, _ = search(query, course=course, top_k=12, enable_mmr=True)

    if not docs:
        return (f"课程「{course}」暂无相关资料。\n\n"
                "请先上传该课程的 PDF 教材或课件。")

    type_desc = {"choice": "选择题", "truefalse": "判断题",
                 "shortanswer": "简答题", "mixed": "混合题型"}
    type_str = type_desc.get(question_type, "混合题型")

    scope = f"课程「{course}」" + (f" 的「{section}」章节" if section else "全部内容")

    prompt = (f"出题范围：{scope}\n"
              f"题型要求：{type_str}\n"
              f"题目数量：共 {count} 道\n\n"
              f"参考资料：\n\n")

    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        section_name = meta.get("section", "")
        page = meta.get("page", 0)
        header = f"[片段{i}]"
        if section_name:
            header += f" 章节: {section_name}"
        if page:
            header += f" 页码: {page}"
        prompt += f"{header}\n{doc[:1500]}\n\n"

    prompt += (f"\n请根据以上资料生成 {count} 道{type_str}。"
               f"确保题目覆盖资料中的不同知识点。")
    return generate(prompt, docs, metas)


# ═══════════════════════════════════════════════════════════
# 任务9: 知识点解释模式
# ═══════════════════════════════════════════════════════════

EXPLAIN_CONCEPT_PROMPT = """你是一位善于讲课的大学助教。你的任务是用大学生**最容易理解的方式**解释知识点。

核心原则：
1. **不要照抄教材**。教材上的定义通常很抽象，你需要翻译成"人话"。
2. **举例优先**。每个抽象概念至少给一个具体、生动的例子。
3. **善用类比**。把陌生的概念类比成日常生活中熟悉的事物。
4. **图景化描述**。用文字描绘画面，帮助学生在脑中建立直观理解。
5. **由浅入深**。先给最直观的理解，再逐步深入细节。

回答结构：
1. 一句话概览（最直观的理解）
2. 通俗解释（类比 + 举例）
3. 技术细节（如果需要）
4. 常见误区（如果存在）
5. 考试小贴士（如果相关内容在考试中常出现）

注意：
- 如果课程资料包含该知识点的解释，引用并展开
- 如果资料不完整，基于你的知识补充，但要注明哪些来自资料、哪些来自补充
- 语言要亲切自然，像学长/学姐在给你讲题"""


def explain_concept(course: str, concept: str, style: str = "通俗") -> str:
    """
    知识点解释（任务9）。

    参数：
      course:  课程名称
      concept: 要解释的知识点（如"TCP三次握手"）
      style:   解释风格 — "通俗"(默认), "学术", "应试"

    返回：
      Markdown 格式的知识点解释
    """
    if not concept.strip():
        return "请输入要解释的知识点。\n\n示例：`请解释：红黑树的旋转操作`"

    # 检索相关知识
    docs, metas, _ = search(concept, course=course, top_k=8, enable_mmr=True)

    style_guide = {
        "通俗": "用通俗易懂的语言，多举例、多类比，像学长学姐在讲课",
        "学术": "保持学术严谨，引用资料中的定义，但也要解释清楚",
        "应试": "聚焦考试要点，说明怎么考、怎么答、常见陷阱",
    }
    style_prompt = style_guide.get(style, style_guide["通俗"])

    prompt = (f"课程：{course}\n"
              f"知识点：{concept}\n"
              f"解释风格：{style_prompt}\n\n")

    if docs:
        prompt += "课程相关资料：\n\n"
        for i, (doc, meta) in enumerate(zip(docs, metas), 1):
            section = meta.get("section", "")
            header = f"[片段{i}]" + (f" (章节: {section})" if section else "")
            prompt += f"{header}\n{doc[:1200]}\n\n"

    prompt += (f"\n请用{style_prompt}的方式解释「{concept}」。"
               f"回答末尾请注明哪些内容来自课程资料，哪些来自补充知识。")

    return generate(prompt, docs if docs else ["（无资料，请基于通用知识解释）"],
                    metas if metas else [{}])


# ═══════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("学习助手模块加载成功。")
    print("可用函数：")
    print("  generate_course_summary(course)")
    print("  generate_chapter_summary(course, section)")
    print("  generate_review_outline(course)")
    print("  generate_exam_questions(course, section, type, count)")
    print("  explain_concept(course, concept, style)")
