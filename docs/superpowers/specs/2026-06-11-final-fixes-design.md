# Echo 学习助手 - 最终修复设计文档

**日期**: 2026-06-11  
**依据**: test_screenshots/FINAL_REPORT.md 真实大学生用户测试报告  
**范围**: P0 + P1 + P2 共 12 个问题（P3-1 暗色模式延后）  
**原则**: 功能优先于设计，所有修改不得削弱现有功能

---

## 改动范围

- **主要文件**: `app_web.py` — UI 回调逻辑 + 界面布局
- **辅助文件**: `llm/learning_assistant.py` — 引用标注增强
- **不改动**: config.py, ingestion/, retrieval/, memory/, router/

---

## P0（系统不可用）

### P0-1: 课程状态间歇性丢失

**现象**: 创建课程后提问，系统间歇返回"请先在顶部选择一个课程。"

**根因**: `create_btn.click` 通过 outputs 更新 `course_dd.value`，但 `current_course_state` 只在 `course_dd.change` 事件触发时更新。Gradio 不保证 click→set dropdown value→触发 change 链。

**修复**:
1. `_create_course` 的 outputs 增加 `current_course_state`，成功后直接写入新课程名
2. `send_message` 增加防御性检查：若 `chat_course == "全部"`，从 `course_dd.value` 重新读取（通过额外 state 同步）
3. 所有依赖 `current_course_state` 的回调确保 state 与 dropdown 同步

---

## P1（严重影响学习）

### P1-1: 新手操作引导

**修复**:
- `_on_load` 返回引导内容到 `top_msg`：
  - Step ① 输入课程名 → 点击"创建"
  - Step ② 上传 PDF/PPT 课件
  - Step ③ 在底部输入框提问
- 无课程时显示引导，有课程后切换为课程欢迎信息
- 初始状态下高亮"新建课程"输入框（placeholder 加提示）

### P1-2: 上传处理状态

**修复**:
- 消息改用学生友好语言，去掉技术术语：
  - `入库完成: 1/1 个文件, 4 个 chunk` → `✅ 学习完成！已解析 4 个知识点，现在可以提问了`
- 上传失败时明确告知原因

### P1-3: 回答引用标注

**修复**:
- 所有回答路径（chapter_summary, exam, explain, qa）统一追加检索来源 `<details>` 块
- LLM prompt 增加要求：用 `📖 来自课件` 和 `💡 补充知识` 标签区分信息来源
- 无检索来源时也说明"本回答基于 AI 通用知识，非课程资料"

### P1-4: 课程切换清空对话

**修复**:
- `_on_course_change` outputs 增加 `chatbot`，返回空列表 `[]`
- welcome 消息明确显示 "📌 已切换到课程「XX」"
- 不清空已有的 `current_course_state`（保持正确）

---

## P2（影响体验）

### P2-1: 功能说明

**修复**: 标题下增加副标题 markdown：
```
> 📚 上传课程资料，AI 帮你总结、出题、答疑 — 所有回答基于你的课件
```

### P2-2: 界面层次优化

**修复**:
- 用 `gr.Accordion("📂 文件管理", open=False)` 包裹文件列表和删除操作
- 危险按钮保持 `variant="stop"`（已有）
- 主操作（创建、上传）放在 Accordion 外部

### P2-3: 创建课程反馈

**修复**:
- 成功消息加 `✅` 前缀，用醒目语言
- `_create_course` 返回 `✅ 课程「XX」已创建！请上传课件`

### P2-4: 快捷按钮直接触发

**修复**:
- `quick_exam_btn` 和 `quick_weak_btn` 改为直接提交
- 实现方式：click 输出到 `msg_input`，然后通过 `msg_input.submit` 自动触发（Gradio 的 `.then()` 链式调用）

### P2-5: 创建后自动选中

**确认**: 现有 `_create_course` 已返回 `value=name`，功能正常。仅需确保 state 同步（与 P0-1 合并修复）。

### P2-6: 学习统计展示

**修复**:
- `_build_welcome` 中增加统计行：
  - 📄 N 个文件 | ❓ 已提问 M 次 | 📖 已学 K 章节
- `_on_load` 从 `get_history` 获取提问计数
- 利用已有 `save_record`/`get_history` 基础设施

### P2-7: 初始欢迎区

**修复**:
- 与 P1-1 合并：`_on_load` 返回引导内容
- 无操作前显示引导 + 功能介绍
- 有课程后切换为课程欢迎信息

---

## 实现顺序

1. P0-1: 课程状态同步（最先修，影响所有功能）
2. P1-1 + P2-7: 新手引导 + 欢迎区（合并实现）
3. P1-4: 课程切换清空对话
4. P1-2: 上传反馈优化
5. P1-3: 引用标注增强
6. P2-1: 副标题
7. P2-2: 界面层次
8. P2-3: 创建反馈
9. P2-4: 快捷按钮
10. P2-5: 确认自动选中
11. P2-6: 学习统计

---

## 验收标准

1. 创建课程后连续提问5次，不再出现"请先选择课程"错误
2. 首次打开页面看到三步引导
3. 上传PDF后看到"学习完成"而非"chunk"术语
4. 切换课程后对话历史清空
5. 点击快捷按钮直接获得回答（不需再点发送）
6. 所有回答包含来源标注
7. 创建课程后下拉自动选中新课程
