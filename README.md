# 📚 基于 RAG 的大学课程学习助手

上传课程 PDF 教材/课件，通过语义检索 + LLM 实现智能学习辅助。

## 功能

| 功能 | 说明 |
|------|------|
| 📄 **课程资料管理** | 上传 PDF、按课程分类、文件管理 |
| 🔍 **智能问答** | 基于课程资料的 RAG 问答，带来源引用 |
| 📝 **课程总结** | 自动生成课程概览、知识点、学习路线 |
| 📖 **章节总结** | 指定章节的知识总结、重难点分析 |
| 📋 **复习提纲** | 考前冲刺提纲，含一/二级重点和时间估算 |
| ✍️ **自动出题** | 选择题/判断题/简答题，可指定知识点和数量 |
| 💡 **知识点解释** | 用通俗语言解释概念，举例+类比 |
| 📊 **学习记录** | 自动记录提问历史，按课程统计 |

### 检索特性
- **分层 Chunk 切分**（标题→段落→句子→字符），保证语义完整
- **页码/章节 Metadata**，精确定位来源
- **MMR 去重**，避免冗余内容浪费上下文
- **Rerank 重排序**（DashScope gte-rerank），提升检索精度
- **动态 TopK**，根据问题复杂度自动调整检索数量
- **低分过滤**，低于阈值的 chunk 不进入 LLM 上下文

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+ 推荐
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DashScope API Key
# DASHSCOPE_API_KEY=sk-xxxxxxxx
```

API Key 获取地址：https://dashscope.aliyun.com/

### 3. 启动

```bash
# Web 界面（推荐）
python app_web.py
# 浏览器打开 http://127.0.0.1:7860
```

```bash
# 命令行模式
python app.py
```

### 4. 使用流程

1. 左侧创建课程 → 上传 PDF 教材
2. 右侧选择课程范围 → 提问或使用命令
3. 支持的命令见下方

## 命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `/总结` | 课程总结 | `/总结` |
| `/总结 课程名` | 指定课程总结 | `/总结 数据结构` |
| `/章节 章节名` | 章节总结 | `/章节 红黑树` |
| `/复习` | 复习提纲 | `/复习` |
| `/出题 N` | 出 N 道混合题 | `/出题 10` |
| `/出题 知识点 N` | 指定知识点出题 | `/出题 B树 5` |
| `/出题 选择 N` | 选择题型 | `/出题 选择 5` |
| `/出题 判断 N` | 判断题型 | `/出题 判断 3` |
| `/出题 简答 N` | 简答题型 | `/出题 简答 3` |
| `/解释 知识点` | 通俗解释 | `/解释 TCP三次握手` |
| `/历史` | 学习记录 | `/历史` |
| `/帮助` | 命令帮助 | `/帮助` |

自然语言出题：`再出5道关于B树的题`

## 项目结构

```
rag-knowledge-base/
├── app.py                    # CLI 入口
├── app_web.py                # Web UI 入口
├── config.py                 # 全局配置
├── requirements.txt          # 依赖
├── .env.example              # 环境变量模板
│
├── ingestion/                # 文档摄入
│   ├── pdf_loader.py         # PDF 解析 + 页/章节提取
│   ├── chunker.py            # RecursiveCharacterTextSplitter
│   ├── embedder.py           # DashScope Embedding
│   └── indexer.py            # ChromaDB 向量索引
│
├── retrieval/                # 检索模块
│   ├── search.py             # 语义检索 + MMR + 动态TopK + 过滤
│   └── rerank.py             # DashScope Rerank 重排序
│
├── llm/                      # 大模型模块
│   ├── dashscope_llm.py      # LLM 调用（流式+非流式）
│   └── learning_assistant.py # 学习助手功能（总结/出题/解释）
│
├── utils/
│   └── text_clean.py         # 文本清洗
│
├── storage/
│   └── learning_log.py       # 学习记录持久化
│
└── data/pdfs/                # 测试 PDF
```

## 配置参数（config.py）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `qwen-turbo` | 大模型，可换 qwen-plus/max |
| `CHUNK_SIZE` | 800 | Chunk 目标大小（字符） |
| `CHUNK_OVERLAP` | 150 | Chunk 重叠字符数 |
| `TOP_K` | 5 | 默认检索数量 |
| `MIN_SCORE` | 0.3 | 最低相似度阈值 |
| `MMR_LAMBDA` | 0.7 | MMR 去重系数 |
| `RERANK_ENABLED` | True | 是否启用 Rerank |
| `DYNAMIC_TOPK` | True | 是否动态调整 TopK |
