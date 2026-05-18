# MineMate

> Your AI buddy for Minecraft mods. Ask anything — recommendations, compatibility, modpack ideas.

MineMate 是一个基于 RAG + Multi-Agent 的 Minecraft 模组智能问答系统。以 mcmod.cn 为知识源，支持百科查询、风格推荐、兼容性分析、整合包编排等多种问答类型。

## 功能

| 问答类型 | 示例 |
|---|---|
| 模组百科 | "工业时代2是什么模组"、"雾中人有什么技能" |
| 风格推荐 | "推荐几个恐怖模组"、"有没有休闲的科技模组" |
| 兼容查询 | "IC2可以和什么模组兼容"、"Create和JEI能一起用吗" |
| 元信息 | "BuildCraft支持哪些版本"、"Create是Forge还是Fabric" |
| 最新模组 | "最近有什么新模组"、"最新科技模组" |
| 整合包 | "推荐轻量科技整合包 1.20.1"、"帮我组一个魔法冒险包" |
| 多轮对话 | 上下文记忆，支持"它"、"那个模组"等代词消解 |

## 架构

```
用户 → Gradio UI → Router Agent ──┬── kb_query → HybridRetriever (Chroma + BGE-M3)
                                  ├── recommendation → recommend_mods (SQLite tags)
                                  ├── compatibility → get_compatible_mods
                                  ├── mod_info_query → get_mod_info
                                  ├── latest_mods → find_latest_mods
                                  ├── modpack_curation → curate_modpack
                                  └── chitchat → 直接回复
                                          ↓
                                     Critic Agent (校验 + 重试)
                                          ↓
                                     Answerer → 回答（含链接 + 引用）
```

**技术栈：** Python 3.11 · DeepSeek · SQLite · ChromaDB · Gradio · BGE-M3 · LlamaIndex

## 快速开始

### 前置条件

- Python 3.11+ + [uv](https://docs.astral.sh/uv/) 包管理工具
- DeepSeek API key（[申请链接](https://platform.deepseek.com)，新用户有免费额度）
- 约 6 GB 可用磁盘（数据 200 MB + BGE-M3 模型 2.3 GB + Python 依赖 ~1.5 GB）

### 1. 安装代码与依赖

```bash
git clone https://github.com/FiRuu41/MineMate.git
cd MineMate
cp .env.example .env          # 然后编辑 .env, 填入 DEEPSEEK_API_KEY
uv sync                       # 装依赖（首次约 3-5 分钟）
```

### 2. 准备数据

本仓库**不公开发布模组数据**（出于 mcmod.cn 内容版权 + 反爬考虑）。

**方式 A：从作者获取数据包**（推荐）

如果你已拿到 `minemate-data-YYYYMMDD-HHMM.zip`，解压到 `data/` 即可：

```bash
# Windows (PowerShell)
Expand-Archive minemate-data-XXX.zip -DestinationPath data\

# macOS / Linux
unzip minemate-data-XXX.zip -d data/

# 解压后 data/ 下应有 minemate.db + chroma/
```

**方式 B：自行构建数据**

参考 `pipeline/storage/models.py` 的 `Mod` 表结构，自己导入 mod 元数据到 `data/minemate.db`，然后重建向量索引：

```bash
make build-index            # 用 BGE-M3 嵌入到 Chroma
```

### 3. 启动

```bash
uv run minemate status      # 检查 SQLite/Chroma/API key 是否就绪
uv run minemate start       # 启动 Web UI
```

打开 http://127.0.0.1:7860 即可对话。

> ⚠️ 首次启动会自动下载 BGE-M3 模型 (~2.3 GB) 到 `D:/hf_cache`（默认走 [hf-mirror.com](https://hf-mirror.com) 国内镜像，5-15 分钟）。模型只下一次，之后启动秒级。

### 4. 试一下

| 类型 | 试试 |
|---|---|
| 模组百科 | "工业时代2 是什么模组" |
| 风格推荐 | "推荐恐怖模组" |
| 兼容查询 | "Create 和 JEI 能一起用吗" |
| 元信息 | "BuildCraft 支持哪些版本" |
| 整合包 | "推荐轻量科技整合包 1.20.1" |
| 多轮 | "工业时代2 是什么" → "它能和什么模组兼容" |

## 常用命令

```bash
uv run minemate start       # 启动 Web 界面
uv run minemate setup       # 首次设置向导
uv run minemate status      # 查看系统状态（SQLite/Chroma/模型/API key/mod 数）
```

### Gradio 界面

- ChatGPT 风格气泡对话
- 对话历史可滚动查看
- 每个模组名附带 mcmod.cn 链接
- 调试信息折叠在底部

## 测试

```bash
uv run pytest                 # 单元测试（63 个，约 1 分钟）
uv run pytest -m slow         # 含 BGE-M3 模型测试（需要 ~2GB 下载）
uv run ruff check .           # Lint
```

## 项目结构

```
MineMate/
├── minemate/cli.py              # CLI 入口 (setup/start/status)
├── app/gradio_app.py            # Gradio Web UI
├── agents/
│   ├── workflow.py              # Agent 编排
│   ├── router.py                # 意图路由 (8 种意图)
│   ├── answerer.py              # 回答生成
│   ├── critic.py                # 答案校验 + 重试
│   └── memory.py                # 多轮对话记忆
├── tools/
│   ├── search_mcmod_kb.py       # 向量检索
│   ├── recommend_mods.py        # 风格推荐
│   ├── compatibility.py         # 兼容性查询
│   ├── get_mod_info.py          # 模组元信息
│   ├── find_latest_mods.py      # 最新模组
│   └── curate_modpack.py        # 整合包编排
├── kb/
│   ├── retriever.py             # 混合检索 (Chroma + SQLite LIKE + RRF)
│   └── chroma_retriever.py      # Chroma 向量层
├── llm/
│   ├── deepseek_client.py       # DeepSeek API
│   └── embeddings.py            # BGE-M3 (GPU 自动检测)
├── config/
│   ├── paths.py                 # 跨场景路径解析（dev/pipx/MSI）
│   ├── settings.py              # Pydantic 配置
│   └── prompts/                 # Prompt 模板
├── pipeline/
│   ├── build_index.py           # 建向量索引
│   ├── tag_mods.py              # LLM 打标 (10 并发)
│   ├── extract_integrations.py  # 兼容性抽取
│   └── storage/                 # SQLAlchemy
└── tests/                       # 单元测试 + integration + eval
```

## FAQ

**Q: 数据从哪来？**
A: 本仓库不公开发布数据（mcmod.cn 内容版权 + 反爬考虑）。可向作者私下获取数据包，或自行参考表结构构建。

**Q: 检索不到某个模组？**
A: 该模组可能不在数据快照范围内。命中 `kb_query` 路径会自动尝试在线获取 mcmod 页面兜底（直连无代理，反爬严时可能失败，会 graceful 提示）。

**Q: GPU 有什么用？**
A: 建向量索引（`make build-index`）时，GPU (CUDA) 比 CPU 快约 10 倍。日常问答只用 CPU 推理也没问题。

**Q: BGE-M3 模型很大，能否换小模型？**
A: 可以。修改 `.env` 中 `EMBEDDING_MODEL=BAAI/bge-base-zh-v1.5`（768 维，约 400 MB）。但**需要重建索引**（`make build-index`），因为现有索引是 1024 维的 BGE-M3 嵌入。

**Q: 为什么不打包成 MSI / exe？**
A: 在规划中（路线 Phase 6）。当前先保证 `uv sync + uv run minemate start` 流程稳定。

## License

MIT

## Disclaimer

本项目仅作技术展示，不附带任何模组百科内容数据。使用者自行负责数据获取与合规，遵守 mcmod.cn 的 robots.txt 与服务条款。
