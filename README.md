# MineMate

> Your AI buddy for Minecraft mods.

基于 mcmod.cn 的 Minecraft 模组智能问答系统（RAG + Multi-Agent）。

## 功能

- **模组百科问答**：查询模组介绍、机制、合成表
- **风格推荐**：「有没有恐怖点的模组」「推荐几个科技模组」——基于 LLM 自动打标
- **兼容性查询**：「机械动力可以和什么模组兼容」「A 和 B 兼容吗」
- **多轮对话**：上下文记忆，支持代词消解（"它"、"那个模组"）
- **ChatGPT 式 UI**：气泡聊天 + 调试侧栏

## 架构

```
用户 → Gradio → Router Agent ──┬── kb_query → VectorRetriever (Qdrant + BGE-M3)
                               ├── recommendation → recommend_mods (MySQL tags)
                               ├── compatibility → get_compatible_mods (MySQL integrations)
                               └── chitchat → Answerer 直接回应
                                       ↓
                                  Answerer Agent → 回答（含引用/推荐列表/兼容信息）
```

## Quick Start

### 前置条件

- Python 3.11+
- Docker Desktop
- DeepSeek API key

### pip 安装

```bash
git clone https://github.com/FiRuu41/MineMate.git
cd minemate
cp .env.example .env           # 填入 DEEPSEEK_API_KEY
pip install -r requirements.txt
docker-compose up -d           # 启动 Qdrant + MySQL
python -m scripts.init_db
```

### uv 安装

```bash
git clone https://github.com/FiRuu41/MineMate.git
cd minemate
cp .env.example .env
uv sync
docker-compose up -d
uv run python -m scripts.init_db
```

### 导入数据 & 启动

```bash
# 1. 将模组数据导入 MySQL mods 表（字段见下方）
# 2. 构建向量索引
uv run python -m pipeline.build_index
# 3. 打标签（推荐功能需要）
uv run python -m pipeline.tag_mods
# 4. 抽取兼容性（兼容性查询需要）
uv run python -m pipeline.extract_integrations
# 5. 启动
uv run python -m app.gradio_app
```

打开 http://127.0.0.1:7860。

> **本项目不包含爬虫和模组数据。** 数据通过 `mods` 表导入。

### mods 表结构

| 字段 | 类型 | 说明 |
|---|---|---|
| `mod_id` | VARCHAR(64) PK | 唯一标识 |
| `name_zh` | VARCHAR(128) | 中文名 |
| `name_en` | VARCHAR(128) | 英文名 |
| `mcmod_url` | VARCHAR(256) | mcmod 链接 |
| `loader` | VARCHAR(64) | Forge / Fabric 等 |
| `mc_versions` | JSON | 支持的 MC 版本列表 |
| `author` | VARCHAR(128) | 作者 |
| `description` | TEXT | 模组简介（主要知识来源） |
| `tags` | JSON | `{"genres": [...], "themes": [...], "mood": "...", "difficulty": "..."}` |
| `known_integrations` | JSON | `[{"mod_name_zh": "...", "evidence": "...", "source_url": "..."}]` |

## 测试

```bash
uv run pytest                 # 单元测试（跳过 slow/e2e）
uv run pytest -m slow         # 含 BGE-M3 模型测试 (~2GB)
```

## 目录结构

```
├── config/         # pydantic-settings + loguru + prompts
├── kb/             # 领域模型 + 向量检索
├── pipeline/       # build_index, tag_mods, extract_integrations
├── llm/            # DeepSeek 客户端 + BGE-M3 Embedding
├── tools/          # search_mcmod_kb / recommend_mods / compatibility
├── agents/         # Router / Answerer / Workflow / Memory
├── app/            # ChatGPT 式 Gradio UI
├── scripts/        # init_db
└── tests/          # 35 个单元测试
```

## License

MIT

## Disclaimer

本项目仅作技术展示，不附带模组百科内容数据。使用者自行负责数据获取与合规。
