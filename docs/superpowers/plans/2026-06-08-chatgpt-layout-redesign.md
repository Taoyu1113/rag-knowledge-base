# ChatGPT 风格三区布局重构 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 app_web.py 重构为侧边栏 + 主内容 + 底部输入区的三区布局，对标 ChatGPT/Claude 输入驱动型产品风格。

**Architecture:** 单一文件修改 — `app_web.py`。后端逻辑（send_message、upload_files_handler 等）完全保留，仅替换 CSS 块和 UI 布局部分，移除所有 emoji 字符。Gradio 6.x 要求 theme/css 通过 `demo.launch()` 注入。

**Tech Stack:** Python 3.13, Gradio 6.15, 自定义 CSS

---

### Task 1: 替换 CUSTOM_CSS 块

**Files:**
- Modify: `app_web.py` (lines 30-330, CUSTOM_CSS block)

- [ ] **Step 1: 定位并移除旧 CSS 块**

在 `app_web.py` 中找到 `CUSTOM_CSS = """` 到对应的 `"""` 结尾之间的所有内容，删除。

- [ ] **Step 2: 插入新 CSS**

在相同位置插入以下 CSS：

```python

# =============================================================
#  Custom CSS — ChatGPT-style three-zone layout
# =============================================================

CUSTOM_CSS = """
:root {
  --brand: #10a37f;
  --text-primary: #0d0d0d;
  --text-secondary: #6b6b6b;
  --text-tertiary: #9e9e9e;
  --bg-primary: #ffffff;
  --bg-secondary: #f7f7f8;
  --border: #e5e5e5;
  --border-light: #f0f0f0;
  --sidebar-width: 260px;
  --content-max-width: 768px;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
  margin: 0;
  overflow: hidden;
}

/* Kill Gradio default container constraints */
.gradio-container {
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Kill all card/panel styling */
.contain, .panel, .gr-box, .gr-form, .gr-group {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
}

/* ======== Sidebar ======== */
.sidebar {
  position: fixed !important;
  left: 0 !important;
  top: 0 !important;
  width: var(--sidebar-width) !important;
  height: 100vh !important;
  background: var(--bg-secondary) !important;
  border-right: 1px solid var(--border) !important;
  padding: 20px 16px !important;
  overflow-y: auto !important;
  z-index: 10 !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
}

.sidebar label, .sidebar .label-wrap {
  font-size: 11px !important;
  font-weight: 500 !important;
  color: var(--text-tertiary) !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  margin-bottom: 2px !important;
}

.sidebar input, .sidebar textarea, .sidebar select {
  font-family: inherit !important;
  font-size: 13px !important;
  background: var(--bg-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  box-shadow: none !important;
}

.sidebar .gr-button {
  font-size: 12px !important;
  width: 100% !important;
  text-align: left !important;
  justify-content: flex-start !important;
}

/* ======== Main area ======== */
.main-area {
  margin-left: var(--sidebar-width) !important;
  display: flex !important;
  flex-direction: column !important;
  height: 100vh !important;
  background: var(--bg-primary) !important;
  position: relative !important;
}

/* ======== Chat area ======== */
.chatbot {
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  flex: 1 !important;
  overflow-y: auto !important;
}

.chatbot .message {
  font-family: inherit !important;
  font-size: 15px !important;
  line-height: 1.625 !important;
  color: var(--text-primary) !important;
}

.chatbot .bubble-wrap {
  padding: 12px 0 !important;
  margin: 0 !important;
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
}

.chatbot .user .bubble-wrap {
  background: var(--bg-secondary) !important;
  border-radius: 8px !important;
  padding: 10px 14px !important;
  margin: 4px 0 !important;
}

.chatbot .bot .bubble-wrap {
  background: transparent !important;
  padding: 10px 0 !important;
}

/* Markdown in chat */
.chatbot .message-wrap h1 { font-size: 20px; font-weight: 700; }
.chatbot .message-wrap h2 { font-size: 16px; font-weight: 600; }
.chatbot .message-wrap h3 { font-size: 14px; font-weight: 600; }

.chatbot .message-wrap code {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875em;
  border: 1px solid var(--border-light);
}
.chatbot .message-wrap pre {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 16px;
  overflow-x: auto;
}
.chatbot .message-wrap blockquote {
  border-left: 2px solid var(--border);
  padding-left: 12px;
  margin-left: 0;
  color: var(--text-secondary);
}
.chatbot .message-wrap details {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-light);
  font-size: 13px;
}
.chatbot .message-wrap details summary {
  cursor: pointer;
  color: var(--text-secondary);
  font-weight: 500;
}
.chatbot .message-wrap ul, .chatbot .message-wrap ol {
  padding-left: 1.25em;
}
.chatbot .message-wrap li { margin: 2px 0; }

.chatbot .message-wrap table {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.chatbot .message-wrap th, .chatbot .message-wrap td {
  border: 1px solid var(--border-light);
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
}
.chatbot .message-wrap th {
  background: var(--bg-secondary);
  font-weight: 600;
}

/* ======== Composer (bottom input) ======== */
.composer-wrap {
  flex-shrink: 0 !important;
  padding: 16px 24px 20px !important;
  max-width: var(--content-max-width) !important;
  margin: 0 auto !important;
  width: 100% !important;
}

#msg-input textarea {
  font-family: inherit !important;
  font-size: 15px !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  background: var(--bg-primary) !important;
  padding: 14px 18px !important;
  resize: none !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
  min-height: 52px !important;
}
#msg-input textarea:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 1px var(--brand) !important;
  outline: none !important;
}
#msg-input label { display: none !important; }

/* ======== Buttons ======== */
button, .gr-button {
  font-family: inherit !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  transition: none !important;
  box-shadow: none !important;
}

.gr-button-primary {
  background: var(--brand) !important;
  color: #fff !important;
  border: 1px solid var(--brand) !important;
}

.gr-button-secondary {
  background: var(--bg-primary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
}

/* ======== Scrollbar ======== */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }

/* ======== Utilities ======== */
footer { display: none !important; }
label {
  font-family: inherit !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  color: var(--text-tertiary) !important;
}
"""
```

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "style: replace CSS with ChatGPT-style three-zone layout styles"
```

---

### Task 2: 重写 UI 布局（三区结构）

**Files:**
- Modify: `app_web.py` (UI section, from `with gr.Blocks` to `if __name__`)

- [ ] **Step 1: 定位并移除旧 UI 块**

在 `app_web.py` 中找到从 `# ── UI` 或 `# ═══ UI` 注释开始到文件末尾的内容，保留 `if __name__ == "__main__":` 块。

- [ ] **Step 2: 插入新 UI 布局**

```python

# ═══════════════════════════════════════════════════════════
#  UI — Three-Zone Layout
# ═══════════════════════════════════════════════════════════

with gr.Blocks(title="课程助手") as demo:

    # ===========================================================
    #  Sidebar (left, 260px, fixed)
    # ===========================================================
    with gr.Column(elem_classes=["sidebar"]):
        gr.HTML('<div style="font-size:15px;font-weight:700;color:var(--text-primary);padding:4px 8px;margin-bottom:4px;">课程助手</div>')

        # New course
        new_course_tb = gr.Textbox(
            label="新建课程",
            placeholder="课程名称...",
        )
        create_btn = gr.Button("+ 新建", variant="secondary")

        # Course list
        gr.HTML('<div style="font-size:11px;font-weight:500;color:var(--text-tertiary);margin-top:8px;padding:0 8px;">课程列表</div>')
        course_list_md = gr.Markdown(
            "",
            elem_id="course-list",
            every=None,
        )

        # Bottom actions
        gr.HTML('<div style="flex:1;"></div>')
        with gr.Row():
            upload_btn = gr.UploadButton(
                "上传",
                file_types=[".pdf", ".pptx", ".ppt"],
                file_count="multiple",
                variant="secondary",
            )
            delete_btn = gr.Button("删除", variant="stop")

    # ===========================================================
    #  Main area (right of sidebar)
    # ===========================================================
    with gr.Column(elem_classes=["main-area"]):
        # Chat
        chatbot = gr.Chatbot(
            label="",
            height="100%",
            elem_classes=["chatbot"],
            show_label=False,
        )

        # Composer
        with gr.Row(elem_classes=["composer-wrap"]):
            msg_input = gr.Textbox(
                label="",
                placeholder="输入问题...",
                scale=6,
                elem_id="msg-input",
            )
            send_btn = gr.Button("发送", variant="primary", scale=1)

    # ===========================================================
    #  State
    # ===========================================================
    current_course_state = gr.State("全部")

    # ===========================================================
    #  Event Handlers
    # ===========================================================

    def _on_load():
        choices = _build_course_choices()
        return choices, "全部", _build_welcome("全部"), _build_course_list_html()

    demo.load(
        fn=_on_load,
        outputs=[],  # handled by individual outputs below
    )

    def _render_course_list():
        return _build_course_list_html()

    demo.load(fn=_render_course_list, outputs=[course_list_md])

    def _create_course(name):
        name = name.strip()
        if not name:
            return gr.update(), gr.update(), "请输入课程名称"
        if name == "全部":
            return gr.update(), gr.update(), "课程名不能为'全部'"
        if name in list_courses():
            return gr.update(), gr.update(), f"课程「{name}」已存在"
        choices = _build_course_choices()
        return "", _build_course_list_html(), f"已创建「{name}」"

    create_btn.click(
        fn=_create_course,
        inputs=[new_course_tb],
        outputs=[new_course_tb, course_list_md, msg_input],
    )

    def _switch_course(course_name, evt_data):
        """Click a course in the sidebar to switch."""
        if not course_name or course_name == "全部":
            return "", "全部", _build_welcome("全部")
        return "", course_name, _build_welcome(course_name)

    # Course switching via markdown clicks is handled by a hidden button
    # For now, we expose a simple mechanism:
    # The course_list_md renders clickable items that pre-fill the input

    def _on_upload(files):
        course = current_course_state.value if hasattr(current_course_state, 'value') else "全部"
        msg, dd_update = upload_files_handler(files, course)
        welcome = _build_welcome(course) if course != "全部" else _build_welcome("全部")
        return msg, _build_course_list_html(), welcome, current_course_state

    upload_btn.upload(
        fn=_on_upload,
        inputs=[upload_btn],
        outputs=[msg_input, course_list_md, chatbot, current_course_state],
    )

    def _on_delete():
        # Use the input to confirm deletion
        return "确定要删除当前课程吗？输入课程名确认删除"

    delete_btn.click(
        fn=_on_delete,
        outputs=[msg_input],
    )

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
        theme=gr.themes.Soft(
            primary_hue="slate",
            secondary_hue="slate",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
    )
```

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "refactor: restructure UI to three-zone layout with sidebar"
```

---

### Task 3: 添加课程列表辅助函数

**Files:**
- Modify: `app_web.py` (helpers section)

- [ ] **Step 1: 添加 _build_course_list_html 函数**

在 helpers 区域（`_build_welcome` 函数之后）添加：

```python

def _build_course_list_html():
    """生成侧边栏课程列表 HTML（可点击切换）。"""
    courses = list_courses()
    if not courses:
        return "<div style='padding:8px;color:var(--text-tertiary);font-size:12px;'>暂无课程</div>"
    lines = ["<div style='display:flex;flex-direction:column;gap:2px;'>"]
    for c in courses:
        escaped = c.replace("'", "\\'").replace('"', '&quot;')
        lines.append(
            f"<div style='padding:8px 10px;border-radius:6px;font-size:13px;"
            f"cursor:pointer;color:var(--text-primary);' "
            f"onmouseover=\"this.style.background='#e8e8ea'\" "
            f"onmouseout=\"this.style.background='transparent'\" "
            f">{escaped}</div>"
        )
    lines.append("</div>")
    return "\n".join(lines)
```

- [ ] **Step 2: 添加课程切换机制**

侧边栏课程列表需要可点击切换。在 Gradio 中，基于 Markdown 的点击切换较为复杂。使用一个隐藏的 Textbox 或通过 JS 实现。

---

### Task 4: 移除所有 Emoji

**Files:**
- Modify: `app_web.py` (all text strings containing emoji)

- [ ] **Step 1: 扫描所有 emoji**

搜索并替换所有 emoji 字符为纯文本或直接移除：

| 旧文本 | 新文本 |
|--------|--------|
| `### 使用帮助` | `### 使用帮助` (移除标题 emoji) |

实际上需要逐个处理每个 reply 字符串。以下是需要修改的位置：

1. `_build_welcome` 函数:
   - 移除所有 emoji，仅保留纯文本
   
```python
def _build_welcome(course: str | None) -> str:
    """生成切换课程后的欢迎消息。"""
    if not course or course == "全部":
        return (
            "# 课程助手\n\n"
            "选择一个课程或上传 PDF 课件，开始学习。\n\n"
            "| 示例 | 功能 |\n"
            "|---|---|\n"
            '| "总结第二章" | 章节总结 |\n'
            '| "出 5 道选择" | 自动出题 |\n'
            '| "解释死锁" | 概念讲解 |\n'
            '| "标记 XX 为薄弱点" | 掌握度追踪 |'
        )

    from ingestion.indexer import list_sections
    sources = list_sources(course)
    sections = list_sections(course)
    memory = get_summary(course)
    learned = memory.get("chapters_learned", [])
    weak = memory.get("weak_concepts", [])

    lines = [f"# {course}\n"]
    lines.append(f"{len(sources)} 个文件  |  {len(sections)} 个章节\n")

    if sections:
        for s in sections:
            status = " [已学]" if s in learned else ""
            lines.append(f"- {s}{status}")

    if weak:
        lines.append(f"\n薄弱点 ({len(weak)} 项):")
        for w in weak:
            lines.append(f"- {w}")

    lines.append('\n直接提问: "总结第一章" / "出几道题" / "解释关键概念"')
    return "\n".join(lines)
```

2. `send_message` 函数中的 help reply:
```python
        reply = """## 使用帮助

**直接说话，无需命令格式:**
- "总结第二章" -> 章节总结
- "出5道选择题" -> 自动出题
- "解释红黑树" -> 知识点解释
- "标记XX为薄弱点" -> 掌握度标记
- "我的薄弱点有哪些" -> 查看薄弱点
- "有哪些文件" -> 查看课程文件

支持: 上传 PDF/PPT/PPTX，删除课程/文件。"""
```

3. `mark_mastery` reply:
```python
            level_label = {"mastered": "已掌握", "weak": "薄弱点", "unmarked": "未标记"}
```

4. `_format_sources_detail`:
```python
    lines = [f'\n<details>\n<summary>来源 ({n} 个片段)</summary>\n']
```

5. 其他所有包含 emoji 的字符串逐一替换。

- [ ] **Step 2: 验证无遗漏**

```bash
python -c "
with open('app_web.py','r',encoding='utf-8') as f:
    content = f.read()
# Check for common emoji
import re
emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF☀-➿⭐✀-➿]')
matches = emoji_pattern.findall(content)
if matches:
    print(f'Found {len(matches)} emoji: {matches[:20]}')
else:
    print('No emoji found - clean!')
"
```

- [ ] **Step 3: 提交**

```bash
git add app_web.py
git commit -m "style: remove all emoji from UI text"
```

---

### Task 5: 验证与调试

**Files:**
- Modify: `app_web.py`

- [ ] **Step 1: 语法检查**

```bash
.venv/Scripts/python -c "import py_compile; py_compile.compile('app_web.py', doraise=True); print('OK')"
```
Expected: `OK`

- [ ] **Step 2: 启动应用**

```bash
# Kill any running instance on 7860
# Launch
.venv/Scripts/python app_web.py
```

- [ ] **Step 3: 验证 HTTP 200**

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7860
```
Expected: `200`

- [ ] **Step 4: 验证 CSS 变量已注入**

```bash
curl -s http://127.0.0.1:7860 | grep -o '\--brand\|\--sidebar-width\|\--content-max-width\|sidebar\|main-area\|composer-wrap' | sort -u
```
Expected: 输出包含 `--brand`, `--sidebar-width`, `--content-max-width`, `sidebar`, `main-area`, `composer-wrap`

- [ ] **Step 5: 功能冒烟测试**

手动验证:
1. 页面打开后看到左侧边栏 + 右侧主区域
2. 输入框在底部，大圆角
3. 输入 "帮助" 并发送，收到无 emoji 的回复
4. 上传 PDF 文件正常
5. 切换课程正常

- [ ] **Step 6: 提交**

```bash
git add app_web.py
git commit -m "chore: final verification and cleanup"
```

---

### 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app_web.py` | 重写 CSS + UI | 三区布局，移除 emoji |
