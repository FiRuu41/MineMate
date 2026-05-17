# MineMate

> Your AI buddy for Minecraft mods.

基于 mcmod.cn 的 Minecraft 模组智能体问答系统（RAG + Agent）。

## 架构

```
用户 → Gradio → Router Agent → VectorRetriever → Answerer Agent → 回答
                    ↓                ↓
                  意图分类        Qdrant + BGE-M3
```

## Quick Start

前置条件：

- Python 3.11+，已安装 [uv](https://docs.astral.sh/uv/)
- Docker Desktop（运行中）
- DeepSeek API key

```bash
git clone https://github.com/FiRuu41/MineMate.git
cd minemate
cp .env.example .env           # 填入 DEEPSEEK_API_KEY（以及其他配置）
uv sync                        # 安装依赖
docker-compose up -d           # 启动 Qdrant + MySQL
uv run python -m scripts.init_db
# 导入你的模组数据到 MySQL（自行准备），然后：
uv run python -m pipeline.build_index
uv run python -m app.gradio_app
```

打开 http://127.0.0.1:7860 即可问答。

> **注意：本项目不包含爬虫代码和模组百科数据。** 使用者需自行准备数据并导入 MySQL `mods` 表（字段：`mod_id`, `name_zh`, `name_en`, `mcmod_url`, `loader`, `mc_versions`, `author`, `description`），然后运行 `build_index` 构建向量索引。

## 测试

```bash
uv run pytest                 # 单元测试（默认跳过 slow）
uv run pytest -m slow         # 需要下载 BGE-M3 模型 (~2GB)
```

## 目录结构

```
MineMate/
├── config/         # pydantic-settings + loguru + prompts
├── kb/             # 领域模型 + 向量检索
├── pipeline/       # 数据管线（切分、入库）
├── llm/            # DeepSeek 封装 + Embedding 封装
├── tools/          # Agent 工具
├── agents/         # Router / Answerer / Workflow
├── app/            # Gradio UI
├── scripts/        # 初始化脚本
└── tests/          # 单元测试
```

## License

MIT，详见 `LICENSE`。

## Disclaimer

本项目仅作技术学习展示，不附带任何模组/百科内容数据。
