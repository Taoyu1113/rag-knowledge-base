# Echo 学习助手最终修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复大学生用户测试报告中全部 P0/P1/P2 问题（12个），确保系统功能完整可用

**Architecture:** 所有改动集中在 `app_web.py`（UI布局+回调逻辑），少量改动 `llm/learning_assistant.py`（LLM prompt 增强引用标注）。不引入新依赖，不修改 config/ingestion/retrieval/memory/router 层。

**Tech Stack:** Gradio 6.x, Python 3.x, ChromaDB, DashScope LLM

---

### Task 1: P0-1 修复课程状态丢失

**Files:**
- Modify: `app_web.py`

**What**: `create_btn.click` 设置 `course_dd.value=new_name` 但不一定触发 `course_dd.change`，导致 `current_course_state` 不更新。修复方式：outputs 中直接写入 `current_course_state`，且 `send_message` 加防御性容错。

- [ ] **Step 1: `_create_course` outputs 增加 `current_course_state`**

修改 `create_btn.click` 的 outputs，在 `_create_course` 成功返回时同步更新 `current_course_state`。

找到 `app_web.py` 中 `create_btn.click` 调用（约第475行）：

```python
# 修改前:
create_btn.click(
    fn=_create_course,
    inputs=[new_course_tb],
    outputs=[new_course_tb, course_dd, top_msg, file_dd],
)

# 修改后:
create_btn.click(
    fn=_create_course,
    inputs=[new_course_tb],
    outputs=[new_course_tb, course_dd, top_msg, file_dd, current_course_state],
)
```

修改 `_create_course` 函数，所有 return 路径加一个 `name` 值：

```python
def _create_course(name):
    name = name.strip()
    empty_files = gr.update(choices=[], value=None)
    if not name:
        return gr.update(), gr.update(choices=_build_course_choices()), "请输入课程名称", empty_files, "全部"
    if name == "全部":
        return gr.update(), gr.update(choices=_build_course_choices()), "课程名不能为'全部'", empty_files, "全部"
    if name in list_courses():
        return gr.update(), gr.update(choices=_build_course_choices()), f"课程「{name}」已存在", empty_files, "全部"
    choices = _build_course_choices()
    if name not in choices:
        choices.append(name)
    # 注意：第五个返回值同步更新 current_course_state
    return "", gr.update(choices=choices, value=name), f"课程「{name}」已创建，请上传资料", empty_files, name
```

- [ ] **Step 2: `send_message` 防御性容错**

在 `send_message` 函数开头（约第145行），当 `chat_course == "全部"` 时不做额外推断（保持"全部"语义），但将 `"请先在顶部选择一个课程"` 提示改成更友好的措辞：

```python
def send_message(message, chat_history, chat_course):
    if not message.strip():
        yield chat_history, ""
        return

    # 防御: 如果课程状态为"全部"但下拉可能选中了课程，这里保持原逻辑
    # 状态同步已由 P0-1 Step1 修复
    course_name = None if chat_course == "全部" else chat_course
```

将所有 "请先在顶部选择一个课程。" 改为更友好的提示：
```python
"📌 请先在顶部下拉菜单选择课程，或输入课程名点击「创建」"
```

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "fix: P0-1 course state sync - add current_course_state to create_btn outputs"
```

---

### Task 2: P1-1 + P2-7 新手引导与欢迎区

**Files:**
- Modify: `app_web.py`

**What**: `_on_load` 显示三步引导，`_build_welcome` 保留课程信息。无课程时用引导替换空白。

- [ ] **Step 1: 更新 `_on_load` 返回引导内容**

修改 `_on_load` 函数（约第455行）：

```python
def _on_load():
    choices = _build_course_choices()
    guide = """## 🎓 大学课程学习助手

> 📚 上传课程资料，AI 帮你总结、出题、答疑 — 所有回答基于你的课件

---

### 🚀 三步开始

| 步骤 | 操作 | 说明 |
|------|------|------|
| **①** | 输入课程名 → 点击 **「创建」** | 例如：数据结构、计算机网络 |
| **②** | 点击 **「上传 PDF/PPT」** | 上传教材、课件、讲义 |
| **③** | 在底部输入框提问 | 例如："总结第一章"、"出5道选择题" |

> 💡 **提示**：所有回答都基于你的课件，不会凭空编造。支持 PDF、PPT、PPTX 格式。
"""
    return gr.update(choices=choices, value="全部"), guide, gr.update(choices=[], value=None)
```

- [ ] **Step 2: 更新 `_build_welcome` 保留课程欢迎信息**

`_build_welcome` 保持不变，它在切换课程时由 `_on_course_change` 调用。

- [ ] **Step 3: 确认 `_on_course_change` 无课程时显示引导**

`_on_course_change` 中当 `course == "全部"` 时，也显示引导（复用 `_on_load` 的引导内容）。将引导提取为函数：

```python
def _build_guide() -> str:
    return """## 🎓 大学课程学习助手

> 📚 上传课程资料，AI 帮你总结、出题、答疑 — 所有回答基于你的课件

---

### 🚀 三步开始

| 步骤 | 操作 | 说明 |
|------|------|------|
| **①** | 输入课程名 → 点击 **「创建」** | 例如：数据结构、计算机网络 |
| **②** | 点击 **「上传 PDF/PPT」** | 上传教材、课件、讲义 |
| **③** | 在底部输入框提问 | 例如："总结第一章"、"出5道选择题" |

> 💡 **提示**：所有回答都基于你的课件，不会凭空编造。支持 PDF、PPT、PPTX 格式。
"""
```

然后在 `_build_welcome` 的 `全部` 分支调用它：

```python
def _build_welcome(course: str | None) -> str:
    if not course or course == "全部":
        return _build_guide()
    # ... 其余课程信息不变
```

- [ ] **Step 4: 提交**

```bash
git add app_web.py
git commit -m "feat: P1-1 + P2-7 new user guide and welcome content"
```

---

### Task 3: P1-4 课程切换清空对话

**Files:**
- Modify: `app_web.py`

**What**: `_on_course_change` 返回空 chatbot，并显示切换提示。

- [ ] **Step 1: 修改 `_on_course_change` outputs 和返回值**

```python
# 找到 course_dd.change (约第487行)
# 修改前 outputs:
course_dd.change(
    fn=_on_course_change,
    inputs=[course_dd],
    outputs=[top_msg, current_course_state, file_dd],
)

# 修改后 outputs (增加 chatbot):
course_dd.change(
    fn=_on_course_change,
    inputs=[course_dd],
    outputs=[top_msg, current_course_state, file_dd, chatbot],
)
```

修改 `_on_course_change` 函数（约第481行），所有 return 加空 chatbot：

```python
def _on_course_change(course):
    welcome = _build_welcome(course)
    file_choices = _build_file_choices(course)
    file_value = file_choices[0] if file_choices else None
    return welcome, course, gr.update(choices=file_choices, value=file_value), []
```

- [ ] **Step 2: Welcome 消息加切换标记**

在 `_build_welcome` 的非全部分支首行加切换提示：

```python
def _build_welcome(course: str | None) -> str:
    if not course or course == "全部":
        return _build_guide()
    
    # ... 原有课程信息 ...
    lines = [f"📌 已切换到课程「{course}」\n"]
    lines.append(f"## {course}\n")
    # ... 其余不变
```

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "feat: P1-4 clear chat on course switch with notification"
```

---

### Task 4: P1-2 上传反馈优化

**Files:**
- Modify: `app_web.py`

**What**: 去掉 "chunk" 等技术术语，改用学生友好语言。

- [ ] **Step 1: 修改 `upload_files_handler` 的返回消息**

在 `upload_files_handler` 中（约第378-382行）：

```python
# 修改前:
msg = f"入库完成: {success_count}/{len(files)} 个文件, {total_chunks} 个 chunk"
if errors:
    msg += f"\n**注意：** {len(errors)} 个失败: " + "; ".join(errors)

# 修改后:
if success_count > 0:
    msg = f"✅ 学习完成！已解析 {total_chunks} 个知识点，现在可以提问了"
    if success_count > 1:
        msg = f"✅ 学习完成！已解析 {success_count} 个文件、{total_chunks} 个知识点，现在可以提问了"
if errors:
    msg += f"\n\n⚠️ {len(errors)} 个文件处理失败: " + "; ".join(errors)
if success_count == 0:
    msg = "❌ 文件处理失败，请检查文件格式"
    if errors:
        msg += ": " + "; ".join(errors)
```

- [ ] **Step 2: 同步更新 `_on_upload` 回调中的消息拼接**

`_on_upload` 中（约第493行）修改消息拼接：

```python
def _on_upload(files, course):
    msg, dd_update = upload_files_handler(files, course)
    welcome = _build_welcome(course)
    file_choices = _build_file_choices(course)
    file_value = file_choices[0] if file_choices else None
    return f"{msg}\n\n{welcome}", dd_update, gr.update(choices=file_choices, value=file_value)
```

保持拼接逻辑不变，但 `upload_files_handler` 返回的消息已经是友好语言。

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "fix: P1-2 replace technical terms with student-friendly upload messages"
```

---

### Task 5: P1-3 引用标注增强

**Files:**
- Modify: `app_web.py`
- Modify: `llm/learning_assistant.py`

**What**: 所有回答路径统一追加来源标注 + LLM prompt 要求区分信息来源。

- [ ] **Step 1: `send_message` 的 chapter_summary/explain/exam 路径追加来源**

当前只有 qa 路径在回答末尾追加 `_format_sources_detail`。需要在 chapter_summary、exam、explain 路径也追加。

修改 `send_message` 约第232-275行的三个分支，每个 return 前追加 sources：

```python
# chapter_summary 分支 (约第232行)
if intent["intent"] == "chapter_summary":
    chapter = intent.get("chapter") or message
    if not course_name:
        reply = "📌 请先在顶部下拉菜单选择课程，或输入课程名点击「创建」"
    else:
        reply = generate_chapter_summary(course_name, chapter)
        if "未在课程" not in reply:
            record_chapter(course_name, chapter)
        # 追加来源
        docs, metas, scores = search(
            f"{chapter} 主要内容", course=course_name, top_k=5
        )
        if docs:
            reply += _format_sources_detail(docs, metas, scores)
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": reply})
    _save_qa_record(message, reply, course_name, msg_type="chapter")
    yield chat_history, ""
    return
```

```python
# exam 分支 (约第247行) — 类似追加 sources
# explain 分支 (约第264行) — 类似追加 sources
```

- [ ] **Step 2: 更新 `learning_assistant.py` 的 prompt 要求标注来源**

在 `EXPLAIN_CONCEPT_PROMPT` 末尾（约第356行），明确要求标注：

```python
EXPLAIN_CONCEPT_PROMPT = """...（前面不变）...

回答末尾必须标注信息来源：
- 📖 **来自课件**：引用资料中的定义和解释
- 💡 **补充知识**：基于AI通用知识的补充

如果课程资料不包含该知识点，请明确说明并基于通用知识解释。"""
```

在 `CHAPTER_SUMMARY_PROMPT` 末尾加：

```python
    "回答末尾请标注：\n"
    "- 📖 **来自课件**的内容\n"
    "- 💡 **补充扩展**的内容（如有）"
```

在 `EXAM_QUESTIONS_PROMPT` 末尾加类似的来源标注要求。

- [ ] **Step 3: 提交**

```bash
git add app_web.py llm/learning_assistant.py
git commit -m "feat: P1-3 add source citations to all response paths"
```

---

### Task 6: P2-1 副标题

**Files:**
- Modify: `app_web.py`

**What**: 页面标题下增加功能说明副标题。

- [ ] **Step 1: 修改标题 markdown**

```python
# 修改前:
gr.Markdown("# 大学课程学习助手")

# 修改后:
gr.Markdown("""# 🎓 大学课程学习助手
> 📚 上传课程资料，AI 帮你总结、出题、答疑 — 所有回答基于你的课件""")
```

- [ ] **Step 2: 提交**

```bash
git add app_web.py
git commit -m "feat: P2-1 add subtitle with system description"
```

---

### Task 7: P2-2 界面层次优化

**Files:**
- Modify: `app_web.py`

**What**: 用 `gr.Accordion` 包裹文件管理行，降低危险操作的视觉权重。

- [ ] **Step 1: 将文件管理行放入 Accordion**

```python
# 修改前 (约第420-431行):
with gr.Row() as file_mgmt_row:
    file_dd = gr.Dropdown(...)
    file_delete_btn = gr.Button("删除选中文件", variant="stop", scale=1)

# 修改后:
with gr.Accordion("📂 文件管理", open=False):
    with gr.Row():
        file_dd = gr.Dropdown(
            label="课程文件",
            choices=[],
            value=None,
            scale=4,
            interactive=True,
        )
        file_delete_btn = gr.Button("删除选中文件", variant="stop", scale=1)
```

- [ ] **Step 2: 将删除课程按钮放入 Accordion**

同时把 `delete_btn` 移入 Accordion：

```python
# 修改前 (约第418行，在 toolbar Row 中):
delete_btn = gr.Button("删除课程", variant="stop", scale=1)

# 修改后: 移到 Accordion 内，工具栏只保留创建+上传
```

工具栏变为：
```python
with gr.Row():
    course_dd = gr.Dropdown(...)
    new_course_tb = gr.Textbox(...)
    create_btn = gr.Button("创建", scale=1)
    upload_btn = gr.UploadButton(...)
```

Accordion 内：
```python
with gr.Accordion("📂 文件管理", open=False):
    with gr.Row():
        file_dd = gr.Dropdown(...)
        file_delete_btn = gr.Button("删除选中文件", variant="stop", scale=1)
    delete_btn = gr.Button("⚠️ 删除整个课程", variant="stop", scale=1)
```

- [ ] **Step 3: 更新事件绑定**

`delete_btn` 移到 Accordion 内后，事件绑定（inputs/outputs）不变，因为 Gradio 组件引用不变。

- [ ] **Step 4: 提交**

```bash
git add app_web.py
git commit -m "feat: P2-2 reorganize UI with Accordion for file management and danger actions"
```

---

### Task 8: P2-3 创建课程反馈增强

**Files:**
- Modify: `app_web.py`

**What**: `_create_course` 成功时返回醒目的绿色提示。

- [ ] **Step 1: 修改成功消息**

在 `_create_course` 中（约第461行）：

```python
# 修改前:
return "", gr.update(choices=choices, value=name), f"课程「{name}」已创建，请上传资料", empty_files, name

# 修改后:
return "", gr.update(choices=choices, value=name), f"✅ 课程「{name}」创建成功！请上传课件开始学习 📚", empty_files, name
```

- [ ] **Step 2: 提交**

```bash
git add app_web.py
git commit -m "fix: P2-3 enhance course creation feedback with success indicator"
```

---

### Task 9: P2-4 快捷按钮自动发送

**Files:**
- Modify: `app_web.py`

**What**: 快捷按钮点击后自动触发发送，不需要再点"发送"。

- [ ] **Step 1: 使用 `.then()` 链式触发 send**

```python
# 修改前 (约第553行):
quick_exam_btn.click(fn=lambda: "出5道关于", outputs=[msg_input])
quick_weak_btn.click(fn=lambda: "我的薄弱点有哪些", outputs=[msg_input])

# 修改后:
quick_exam_btn.click(
    fn=lambda: "出5道选择题",
    outputs=[msg_input],
).then(
    fn=send_message,
    inputs=[msg_input, chatbot, current_course_state],
    outputs=[chatbot, msg_input],
)

quick_weak_btn.click(
    fn=lambda: "我的薄弱点有哪些",
    outputs=[msg_input],
).then(
    fn=send_message,
    inputs=[msg_input, chatbot, current_course_state],
    outputs=[chatbot, msg_input],
)
```

- [ ] **Step 2: 提交**

```bash
git add app_web.py
git commit -m "feat: P2-4 quick buttons auto-send without extra click"
```

---

### Task 10: P2-5 确认创建后自动选中

**Files:**
- Modify: `app_web.py`

**What**: 已在 Task 1 中修复（`_create_course` 返回 `value=name` 且同步 `current_course_state`）。此任务仅验证。

- [ ] **Step 1: 验证逻辑检查**

检查 `_create_course` 所有返回路径：
- 失败路径返回 `"全部"` — 正确
- 成功路径返回 `name` — 正确（Task1 已修改）
- `course_dd` 的 `gr.update(choices=choices, value=name)` — 已存在，正确

- [ ] **Step 2: 同步确认 `_on_upload` inputs 使用 `current_course_state`**

`upload_btn.upload` 已使用 `inputs=[upload_btn, current_course_state]` — 正确。

无需代码修改。

---

### Task 11: P2-6 学习统计展示

**Files:**
- Modify: `app_web.py`

**What**: `_build_welcome` 中显示学习统计。

- [ ] **Step 1: 在 `_build_welcome` 中增加统计行**

```python
def _build_welcome(course: str | None) -> str:
    if not course or course == "全部":
        return _build_guide()

    from ingestion.indexer import list_sections
    from storage.learning_log import get_course_stats_from_history
    sources = list_sources(course)
    sections = list_sections(course)
    memory = get_summary(course)

    lines = [f"📌 已切换到课程「{course}」\n"]
    lines.append(f"## {course}\n")

    # 学习统计行
    stats = get_course_stats_from_history()
    course_stats = stats.get(course, {"total": 0})
    lines.append(f"📄 {len(sources)} 个文件 | ❓ 已提问 {course_stats.get('total', 0)} 次 | "
                 f"📖 已学 {len(memory.get('chapters_learned', []))} 章节\n")

    # 显示文件列表
    if sources:
        lines.append(f"**已上传 {len(sources)} 个文件：**")
        # ...
    
    # ... 其余不变
```

- [ ] **Step 2: 提交**

```bash
git add app_web.py
git commit -m "feat: P2-6 add learning statistics to course welcome"
```

---

### Task 12: 最终验证

**Files:**
- 验证: `app_web.py`

**What**: 启动应用，逐一验证所有 12 个修复点。

- [ ] **Step 1: 启动应用**

```bash
cd E:/echo && source .venv/Scripts/activate && python app_web.py
```

- [ ] **Step 2: 验证清单**

| # | 验证项 | 预期结果 |
|---|--------|----------|
| P0-1 | 创建课程→提问5次 | 无"请先选择课程"错误 |
| P1-1 | 首次打开页面 | 看到三步引导 |
| P1-2 | 上传PDF | 看到"学习完成！已解析N个知识点" |
| P1-3 | 提问课程问题 | 回答含来源标注 |
| P1-4 | 切换课程 | 对话清空，显示"已切换" |
| P2-1 | 页面标题 | 有副标题 |
| P2-2 | 界面布局 | 文件管理在折叠区内 |
| P2-3 | 创建课程 | 反馈消息含✅ |
| P2-4 | 点击快捷按钮 | 自动获得回答 |
| P2-5 | 创建课程后 | 下拉自动选中新课程 |
| P2-6 | 课程欢迎页 | 显示学习统计 |
| P2-7 | 无操作时 | 消息区显示引导 |

- [ ] **Step 3: 最终提交**

```bash
git add app_web.py
git commit -m "chore: final verification - all 12 fixes confirmed"
```
