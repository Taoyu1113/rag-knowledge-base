# Echo Workspace 前端重设计 — 设计规约 v2

**日期**: 2026-06-10  
**状态**: 设计已锁定，待实现  
**基于**: 1550c27 功能完整版本（无自定义 CSS）

## 一、设计目标

将 Echo 从"课程管理后台"转变为"AI 对话学习工作空间"。

**核心原则**: 学生打开后立即知道"我应该在这里提问"，而非"我要管理什么"。

| 指标 | 当前 | 目标 |
|------|------|------|
| 视觉焦点 | 分散（10+ 组件同级） | 唯一（输入框） |
| 第一印象 | 管理仪表盘 | ChatGPT 对话界面 |
| 输入框权重 | ~15% | ~50% |
| 侧边栏权重 | ~30% | ~5% |
| 色彩 | Gradio 默认蓝色+灰色 hex | 纯黑白 rgba(0,0,0,X) |

## 二、整体布局

```
┌──────────┬─────────────────────────────────────────┐
│ Sidebar  │          Main Area                      │
│ 240px    │          max-width: 820px               │
│ fixed    │          margin: auto                   │
│          │                                         │
│ Echo     │    ┌──────────────────────────┐         │
│ ────     │    │  Chatbot (flex: 1)       │         │
│ 课程     │    │  - 空状态: 欢迎语居中     │         │
│ · 数据.. │    │  - 对话中: 消息顶对齐     │         │
│ · 线性.. │    │  - max-width: 820px      │         │
│ · 概率.. │    │  - padding: 0 24px       │         │
│ · 全部   │    └──────────────────────────┘         │
│          │    ┌──────────────────────────┐         │
│ + 新建.. │    │  Composer (pill 56px)    │         │
│          │    │  [+ 输入框 发送]          │         │
└──────────┴─────────────────────────────────────────┘
```

**关键约束**:
- Sidebar: `position: fixed; width: 240px; height: 100vh`
- Main: `margin-left: 240px; display: flex; flex-direction: column; height: 100vh`
- 内容区: `max-width: 820px; width: 100%; margin: 0 auto`
- 2K/4K 屏幕: 左右保留大量留白

## 三、侧边栏 (Sidebar)

**职责**: 仅课程切换。存在感 5%。

**内容（从上到下）**:
1. Brand: "Echo" (14px, font-weight 600, rgba(0,0,0,0.85))
2. Section 标签: "课程" (10px, uppercase, rgba(0,0,0,0.35))
3. 课程列表: 每项 13px, rgba(0,0,0,0.55), padding 6px 8px, border-radius 6px
   - 选中态: background rgba(0,0,0,0.04), color rgba(0,0,0,0.85)
   - 右侧分隔线: border-right: 1px solid rgba(0,0,0,0.06)
4. 底部: "+ 新建课程" 文字链接 (12px, rgba(0,0,0,0.35))

**新建课程交互**: 点击"+ 新建课程"→ 文字消失 → 原地出现输入框 + 取消/创建按钮 → 创建成功后输入框收起 → 新课程出现在列表并自动选中。

**右键菜单**: 右键课程名弹出:
- 上传文件
- 重命名  
- ───
- 删除课程 (红色 rgba(220,38,38,0.85))

## 四、空状态 (Empty State)

**方案**: 欢迎语作为 Chatbot 第一条消息。

```
Chatbot value = [{"role": "assistant", "content": welcome_html}]
```

**CSS 行为**:
- 仅一条消息时: `justify-content: center`（垂直居中）
- 多条消息时: `justify-content: flex-start`（默认顶对齐）

**实现方式**: Chatbot 容器始终 `justify-content: center` + `flex: 1` + `overflow-y: auto`。当只有欢迎消息时内容不足容器高度 → 居中显示。当多条消息超出容器高度 → 内容从顶部开始自然溢出，滚动条出现，视觉效果即为顶对齐。无 JS、无 :has()、纯 CSS。

**欢迎语内容（无课程/全部模式）**:
```html
<div style="text-align:center;">
  <div style="font-size:18px;font-weight:500;color:rgba(0,0,0,0.8);">今天想学什么？</div>
  <div style="font-size:14px;color:rgba(0,0,0,0.35);">选择示例问题或直接输入你想了解的内容</div>
  <div class="example-item" onclick="...">总结一下课程的主要内容</div>
  <div class="example-item" onclick="...">出5道选择题测试我的理解</div>
  <div class="example-item" onclick="...">解释一下课程的核心概念</div>
  <div class="example-item" onclick="...">查看我的薄弱点</div>
</div>
```

**示例问题交互**: 点击后填入输入框（JS onclick 操作 textarea.value），不自动发送。

**课程特定欢迎语**: 纯文本，显示课程名 + 文件数 + 章节列表 + 薄弱点统计。无 emoji、无 Markdown 标题。

## 五、Composer（输入框）

**页面唯一视觉焦点。50% 权重。**

**规格**:
| 属性 | 值 |
|------|-----|
| 容器高度 | 56px（含 padding） |
| Textarea 高度 | 48px |
| 容器圆角 | 28px (pill) |
| 容器边框 | 1px solid rgba(0,0,0,0.12) |
| 聚焦边框 | 1px solid rgba(0,0,0,0.22) |
| 容器 padding | 4px 8px 4px 4px |
| 内部 gap | 4px |
| 距底部 | margin: 0 auto 24px |
| 最大宽度 | 820px |

**子组件（从左到右）**:

1. **上传按钮** (`#upload-btn`): "+" 字符, 32×32px, color rgba(0,0,0,0.35), hover → rgba(0,0,0,0.55), 无边框无背景
2. **输入框** (`#msg-input` textarea): flex: 1, 无边框, 背景透明, font-size 15px, line-height 24px, padding 12px 4px
3. **发送按钮** (`#send-btn`): 黑底白字, border-radius 24px, padding 8px 18px, font-size 13px, font-weight 500

**状态**:
- 默认: 发送按钮 rgba(0,0,0,0.85)
- 聚焦: 边框加深至 rgba(0,0,0,0.22)
- 有内容: 发送按钮 #000

**键盘**: Enter 发送, Shift+Enter 换行。

**上传行为（未选课程）**: 点击 + → placeholder 变为"请先在左侧选择课程，再上传文件"（2 秒恢复）。不弹出文件选择器。

## 六、对话视图

**Chatbot 样式**:
- 所有后代元素: `background: transparent; border: none; box-shadow: none; border-radius: 0`
- 消息最大宽度: 820px, margin: 0 auto, padding: 0 24px
- 用户消息: color rgba(0,0,0,0.55)
- 助手消息: color rgba(0,0,0,0.85)
- 字号: 15px, line-height: 1.625
- 代码块: border: 1px solid rgba(0,0,0,0.06), border-radius: 6px
- 引用块: border-left: 2px solid rgba(0,0,0,0.12)
- 检索来源: 折叠 details/summary, font-size 0.8125rem

**过渡**:
- 空状态: 欢迎语在 chatbot 内，垂直居中
- 发送第一条消息: 欢迎语被 chat_history 替换，对话顶对齐

## 七、颜色系统

**唯一允许的颜色值**:
- `rgba(0,0,0,X)` — 全部文本、边框、背景
- `#fff` — 白色背景
- `#000` — 纯黑（发送按钮 hover）

**Token 定义**:
```
--text-strong:  rgba(0,0,0,0.85)  标题、正文、选中课程
--text-base:    rgba(0,0,0,0.55)  课程名、用户消息
--text-weak:    rgba(0,0,0,0.35)  示例问题、placeholder、标签
--border-light: rgba(0,0,0,0.06)  侧边栏分割线
--border-input: rgba(0,0,0,0.12)  输入框边框
--border-focus: rgba(0,0,0,0.22)  输入框聚焦
```

**严格禁止**:
- 任何灰色 hex 值 (#f5f5f5, #e5e7eb, #999, #666, #333...)
- 任何品牌色 hex 值（#10a37f, #3b82f6...）
- box-shadow
- 渐变 (linear-gradient, radial-gradient)
- 圆角卡片（.panel, .card 类型样式）

## 八、技术要求

**主题**: `gr.themes.Base(font=gr.themes.GoogleFont("Inter"))` — 零默认颜色注入。

**CSS 注入**: 通过 `demo.launch(css=CUSTOM_CSS)`。

**Gradio 全局重置**:
- `.gradio-container { max-width: none; margin: 0; padding: 0 }`
- `footer, .versions, #footer, .watermark, .built-with { display: none }`
- 所有按钮: `box-shadow: none`
- 滚动条: 5px 宽, thumb rgba(0,0,0,0.12)

## 九、实施策略

**分两步走**，每步独立可发布：

**Step 1 — 核心布局**（最关键）:
- 移除顶部工具栏，改为 Sidebar + Main 布局
- Sidebar: 课程 Radio + 新建课程（原地展开）
- Main: Chatbot + Composer
- Welcome 进 Chatbot 第一条消息
- 所有现有回调保持不变（`send_message`, `upload_files_handler`, `_create_course` 等）

**Step 2 — 细节完善**:
- 右键菜单（上传/重命名/删除）
- 示例问题点击填入
- 键盘快捷键
- 微交互（hover 过渡等）

## 十、文件清单

唯一修改文件: **`E:\echo\app_web.py`**
- CUSTOM_CSS（约 250 行，纯黑白）
- UI 结构（with gr.Blocks → with gr.Row/Column）
- 新增: `_build_welcome()` 返回 HTML
- 保持: 所有现有回调函数签名不变
