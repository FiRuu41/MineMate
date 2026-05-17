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
用户 → Gradio UI → Router Agent ──┬── kb_query → HybridRetriever (Qdrant + BGE-M3)
                                  ├── recommendation → recommend_mods (MySQL tags)
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

**技术栈：** Python 3.11 · DeepSeek · Qdrant · MySQL · Gradio · BGE-M3 · LlamaIndex

## 快速开始

### 前置条件

- Python 3.11+
- Docker Desktop（提供 Qdrant + MySQL）
- DeepSeek API key（[申请链接](https://platform.deepseek.com)）

### 安装

```bash
git clone https://github.com/FiRuu41/MineMate.git
cd minemate
cp .env.example .env          # 编辑 DEEPSEEK_API_KEY
pip install -e .
docker-compose up -d           # 启动 Qdrant + MySQL
```

### 导入数据

**方式 A：使用预构建数据包（最快）**

如果你有数据包（`mods.sql.gz` + `qdrant_storage.zip`）：
```bash
minemate import-data
```

**方式 B：自行爬取**

配置代理后运行爬虫，再建索引和打标：
```bash
minemate crawl --recent
minemate build-index
minemate build-tags
```

### 启动

```bash
minemate start
```

打开 http://127.0.0.1:7860。

## 使用

```
minemate start      启动 Web 界面
minemate setup      首次设置向导
minemate status     查看系统状态
```

### Gradio 界面

- ChatGPT 风格气泡对话
- 对话历史可滚动查看
- 每个模组名附带 mcmod.cn 链接
- 调试信息折叠在底部

## 测试

```bash
uv run pytest                 # 单元测试（54 个）
uv run pytest -m slow         # 含 BGE-M3 模型测试（需要 ~2GB 下载）
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
├── kb/retriever.py              # 混合检索 (向量 + RRF)
├── llm/
│   ├── deepseek_client.py       # DeepSeek API
│   └── embeddings.py            # BGE-M3 (GPU 自动检测)
├── pipeline/
│   ├── build_index.py           # 建向量索引
│   ├── tag_mods.py              # LLM 打标 (10并发)
│   ├── extract_integrations.py  # 兼容性抽取
│   └── storage/                 # SQLAlchemy + Qdrant
├── config/                      # 配置 + Prompt 模板
├── docker-compose.yml           # Qdrant + MySQL
└── tests/                       # 54 个单元测试
```

## FAQ

**Q: 能否不装 Docker？**
A: 目前不行。Qdrant 和 MySQL 通过 Docker Compose 管理。后续可支持远程服务。

**Q: 数据从哪来？**
A: 本项目不包含模组数据。数据来源为 mcmod.cn，可通过爬虫自行获取。

**Q: 检索不到某个模组？**
A: 说明该模组未被爬取。可扩大爬取范围或手动添加。

**Q: GPU 有什么用？**
A: 建向量索引时，GPU (CUDA) 比 CPU 快约 10 倍。CPU 也能跑，只是慢。

## License

MIT

## Disclaimer

本项目仅作技术展示，不附带任何模组百科内容数据。使用者自行负责数据获取与合规。
