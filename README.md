# mc-mod-qa

基于 mcmod.cn 的 Minecraft 模组智能体问答系统。

> **当前版本：v0.1.0 MVP**：3 个示例模组（机械动力 / JEI / 植物魔法）+ Router/Answerer 双 Agent + 向量检索 + Gradio 单轮问答。详细设计见 `docs/superpowers/specs/2026-05-16-mc-mod-qa-design.md`。

## 架构

```
用户 → Gradio → Router Agent → VectorRetriever → Answerer Agent → 回答
                    ↓                ↓
                  意图分类        Qdrant + BGE-M3
```

数据来源：mcmod.cn。本项目本身**不包含**任何模组百科内容，使用者自行运行爬虫获取数据。

## Quick Start

前置条件：

- Python 3.11+，已安装 [uv](https://docs.astral.sh/uv/)
- Docker Desktop（运行中）
- DeepSeek API key

```bash
git clone <repo>
cd mc-mod-qa
cp .env.example .env           # 填入 DEEPSEEK_API_KEY
uv sync                        # 安装依赖
docker-compose up -d           # 启动 Qdrant + MySQL
uv run python -m scripts.init_db
uv run python -m pipeline.crawl --mods create jei botania
uv run python -m pipeline.build_index
uv run python -m app.gradio_app
```

打开 http://127.0.0.1:7860 即可问答。

## 测试

```bash
uv run pytest                 # 单元测试（默认跳过 slow/e2e/integration）
uv run pytest -m integration  # 需要 Qdrant 在运行
uv run pytest -m slow         # 需要下载 BGE-M3 模型 (~2GB)
uv run pytest -m e2e          # 端到端，需要 Qdrant + 索引 + DeepSeek key
```

## 目录结构

详见 `docs/superpowers/specs/2026-05-16-mc-mod-qa-design.md` § 9。

```
mc-mod-qa/
├── config/         # pydantic-settings + loguru + prompts
├── kb/             # 领域模型 + 向量检索
├── pipeline/       # 离线数据管线（爬取、清洗、切分、入库）
├── llm/            # DeepSeek 封装 + Embedding 封装
├── tools/          # Agent 工具
├── agents/         # Router / Answerer / Workflow
├── app/            # Gradio UI
├── scripts/        # 初始化脚本
└── tests/          # 单元 / 集成 / e2e
```

## License

MIT，详见 `LICENSE`。

## Disclaimer

本项目仅作技术学习展示，不附带任何模组/百科内容数据。使用爬虫时请遵守 mcmod.cn 使用条款、控制请求频率（默认 1.5 秒间隔），尊重原作者版权。
