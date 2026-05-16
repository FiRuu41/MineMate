# MC 模组智能体问答系统 设计文档

- **日期**：2026-05-16
- **状态**：设计已确认，待进入实现规划
- **作者**：项目主理人 + Claude（brainstorming）

---

## 1. 项目定位

一个面向 **Minecraft 模组**领域的智能体问答系统，覆盖两类需求：

- **玩家向**：模组怎么玩、物品在哪个模组、模组之间怎么搭配
- **模组百科向**：模组介绍、合成表、机制、教程

不覆盖：模组开发者向（Forge/Fabric API、Mixin 等开发问题），后续可扩展。

## 2. 范围

- **第一阶段（MVP）**：跑通端到端流程，覆盖 3~5 个热门模组、Router + Answerer 两个 Agent、`search_mcmod_kb` 一个工具
- **第二阶段（完整版，本设计目标）**：Top 20 热门模组、4 个 Agent、4 个工具、多轮对话记忆、Critic 校验

## 3. 技术栈

| 模块 | 选型 |
|---|---|
| 编排框架 | LlamaIndex Workflow（多 Agent 流程） |
| LLM | DeepSeek（Router/Answerer/Critic 都用） |
| Embedding | BGE-M3 本地（sentence-transformers / HuggingFaceEmbedding） |
| 向量库 | Qdrant（Docker） |
| 关系库 | MySQL（合成表 / alias 表 / 模组元信息） |
| 检索 | 混合检索 BM25 + 向量，RRF 融合 |
| UI | Gradio |
| 依赖管理 | uv |
| 服务编排 | docker-compose（Qdrant + MySQL） |
| 日志 | loguru |
| 测试 | pytest |
| 爬虫 | httpx + bs4 + trafilatura；Playwright 兜底 |

## 4. 数据源

- **主源**：mcmod.cn（中文百科）
- **辅源**：Fandom 中文、模组官方文档 / CurseForge（手动补充少量关键模组）
- **模组清单**：从 mcmod.cn 热度榜抓取 Top 20，落地 `data/mod_list.json`，可人工编辑

## 4.5 支持的问答类型

| 类型 | 示例 | 走哪条路径 |
|---|---|---|
| 模组百科 | "机械动力的动力源是什么" | kb_query → Retriever |
| 合成表 | "黄铜锭怎么合成" | recipe_query → get_recipe |
| 模组元信息 | "Create 支持哪些 MC 版本" | mod_info_query → get_mod_info |
| **风格推荐** | "有没有恐怖点的模组" | **recommendation → recommend_mods** |
| **兼容性查询** | "Create 能和什么模组兼容" / "Create 和 AE2 兼容吗" | **compatibility → get_compatible_mods / check_mod_compatibility** |
| 兜底实时搜索 | 知识库没命中时 | web_fallback → web_search_mcmod |
| 闲聊 | "你好" | chitchat → Answerer 直接答 |

## 5. 架构总览

### 5.1 在线问答流（Agent Workflow）

```
                       ┌─────────────┐
   用户问题 ──────────▶│  Gradio UI  │
                       └──────┬──────┘
                              ▼
                       ┌─────────────┐
                       │ Router Agent│
                       └──────┬──────┘
                ┌─────────────┼──────────────┐
                ▼             ▼              ▼
        ┌──────────────┐ ┌─────────┐ ┌──────────────────┐
        │Retriever Ag. │ │get_recipe│ │ web_search_mcmod │
        │+search_mcmod │ │  (工具) │ │   (兜底工具)     │
        │   _kb (工具) │ └────┬────┘ └────────┬─────────┘
        └──────┬───────┘     │                │
               └─────────────┴────────────────┘
                              ▼
                       ┌─────────────┐
                       │Answerer Ag. │
                       └──────┬──────┘
                              ▼
                       ┌─────────────┐
                       │ Critic Agent│ ──不通过──▶ Retriever 重试（最多2次）
                       └──────┬──────┘
                              ▼ 通过
                       返回用户（含引用 + 链接）
```

### 5.2 离线数据管线

```
mcmod.cn ──▶ 爬虫 ──▶ 原始 HTML 缓存
                          │
                          ▼
              清洗（trafilatura/bs4）
                          │
                          ▼
          结构化抽取（介绍/合成/物品/元信息）
                          │
        ┌─────────────────┼──────────────┬───────────────┐
        ▼                 ▼              ▼               ▼
  LlamaIndex 切分    合成表 → MySQL  alias表 → MySQL  ModInfo → MySQL
        │
        ▼
  BGE-M3 Embedding
        │
        ▼
  Qdrant 集合 mcmod_v1
```

### 5.3 关键决策

- Critic **每次都跑**（先质量优先，后续可优化为按置信度触发）
- Retriever 在 **top_score < 0.5** 时自动调 `web_search_mcmod` 兜底
- Router 路由层硬编码，不让 LLM 决策（确定性）
- Retriever Agent 内部允许 LLM 选择调用哪个检索工具

## 6. 数据管线详细设计

### 6.1 Top 20 模组清单

格式：
```json
{
    "mod_id": "create",
    "name_zh": "机械动力",
    "name_en": "Create",
    "mcmod_url": "https://www.mcmod.cn/class/2261.html",
    "mc_versions": ["1.18.2", "1.19.2", "1.20.1"]
}
```

### 6.2 抓取范围（每个模组）

| Tab | 抓取上限 | 方式 |
|---|---|---|
| 简介 | 全量 | httpx + bs4 |
| 物品列表 | 全量（翻页） | httpx + bs4 |
| 教程 | **每模组最多 30 篇**（按热度/收藏排序） | 列表 → 详情 |
| 合成表 | 全量（来自物品页） | bs4 解析合成框 DOM |

反爬：UA 轮换、1~2 秒随机间隔、本地 HTML 缓存避免重爬、Playwright 兜底 JS 渲染页面。

### 6.3 清洗与结构化

- **正文**：trafilatura 提取主体 → Markdown
- **物品/合成**：bs4 解析 mcmod 合成框 DOM → 结构化 JSON
- **图片**：保留 URL，不下载

### 6.4 切分

| 类型 | 策略 | 参数 |
|---|---|---|
| 介绍 / 教程 | SentenceSplitter | chunk_size=512, overlap=64 |
| 物品 / 合成 | 单条一个 chunk | 携带完整 metadata |

统一 metadata：`mod_id, mod_name_zh, section, mc_version, source_url, title`

### 6.5 入库

- **Qdrant 集合**：`mcmod_v1`
- **去重**：按 `mod_id + source_url + content_hash`
- **更新**：按 `mod_id` 删旧插新
- **MySQL 表**：
  - `recipes`：合成表（result_item, ingredients JSON, recipe_type, mod_id, source_url）
  - `item_aliases`：物品中英文 alias（item_id, name_zh, name_en, mod_id）
  - `mods`：模组元信息（作者、Loader、依赖、支持版本、**genres / themes / mood 标签**、**known_integrations 兼容/联动模组列表**）

### 6.6 模组标签与兼容性抽取

**标签（用于风格推荐）**
- 字段：`genres`（如 恐怖/魔法/科技/冒险/建筑/农业/RPG）、`themes`（如 黑暗/克苏鲁/蒸汽朋克/中世纪）、`mood`（如 治愈/紧张/探索）、`difficulty`（休闲/硬核）
- 流程：建索引时调 DeepSeek 基于"模组简介 + 教程摘要"为每个模组生成 3~6 个标签 → 写入 `mods.tags`（JSON）→ 人工 review Top 20（一次性工作，结果落 `data/tag_review.yaml`，下次重建优先采用人工标注）
- 入口：`python -m pipeline.tag_mods`

**兼容性 / 联动（用于兼容性查询）**
- 字段：`known_integrations`：`[{"mod_id": "ae2", "name_zh": "应用能源2", "evidence": "教程里提到...", "source_url": "..."}, ...]`
- 来源：方案 A —— LLM 从该模组的"简介/教程"文本中抽取明确提到的"兼容/联动/支持/依赖"段落，识别出涉及的其他模组
- 入口：`python -m pipeline.extract_integrations`
- 兼容性回答要附带 **MC 版本**：通过取两个模组 `mc_versions` 的交集得出"在哪些版本上同时可用"

### 6.6 CLI

```bash
python -m pipeline.crawl --top 20
python -m pipeline.crawl --mod create        # 单模组重爬
python -m pipeline.build_index
python -m pipeline.build_index --mod create  # 单模组重建
```

## 7. Agent 详细设计

### 7.1 Workflow 共享状态

```python
{
    "user_query": str,
    "chat_history": list,
    "intent": str,                 # kb_query | recipe_query | web_fallback | chitchat
    "extracted_entities": dict,    # mod_name, item_name, etc.
    "retrieved_docs": list,
    "tool_outputs": dict,
    "draft_answer": str,
    "critic_feedback": str | None,
    "retry_count": int,
}
```

### 7.2 Router Agent

- **输入**：user_query + chat_history
- **输出**：JSON `{intent, extracted_entities}`
- **实现**：DeepSeek + JSON mode + few-shot
- **意图集**：`kb_query | recipe_query | mod_info_query | recommendation | compatibility | web_fallback | chitchat`
- **entities 抽取**：mod_name、item_name、tags（推荐时）、mod_a/mod_b（兼容性时）、mc_version

### 7.3 Retriever Agent

- **输入**：query、intent、entities、critic_feedback（重试时）
- **输出**：retrieved_docs（top_k=8）
- **逻辑**：
  - 混合检索：BM25 + 向量 + RRF 融合（LlamaIndex 内置）
  - metadata filter（按 mod_id / section / mc_version）
  - top_score < 0.5 时自动调 web_search_mcmod 兜底
  - 重试：根据 critic_feedback 改写 query 或扩大 top_k

### 7.4 Answerer Agent

- **输入**：query、retrieved_docs / tool_outputs、chat_history
- **输出**：Markdown 草稿，含 `[来源N]` 引用标记
- **规则**：严格基于上下文；找不到答案直接说"未在知识库中找到"

### 7.5 Critic Agent

- **输入**：query、draft_answer、retrieved_docs
- **输出**：`{pass: bool, reason: str, suggestion: str}`
- **检查项**：
  1. 是否答到了问题（vs 答非所问）
  2. 关键事实是否在 docs 中有出处
  3. 是否有明显幻觉
- **不通过**：回到 Retriever 重试，最多 2 次；仍不通过 → 返回 draft + "⚠️ 此回答未通过自动校验，仅供参考"

### 7.6 多轮记忆

- LlamaIndex `ChatMemoryBuffer`，token 上限 8000
- Router 看到完整历史，用于消解"它/那个模组"等代词

## 8. 工具定义

### 8.1 `search_mcmod_kb`
```python
def search_mcmod_kb(
    query: str,
    mod_id: Optional[str] = None,
    section: Optional[str] = None,   # intro|tutorial|item|recipe
    mc_version: Optional[str] = None,
    top_k: int = 8,
) -> list[dict]
```

### 8.2 `get_recipe`
```python
def get_recipe(
    item_name: str,
    mod_id: Optional[str] = None,
    direction: Literal["how_to_craft", "used_in"] = "how_to_craft",
) -> list[dict]
```
基于 MySQL + item_aliases 模糊匹配。

### 8.3 `web_search_mcmod`
```python
def web_search_mcmod(query: str, top_k: int = 5) -> list[dict]
```
实时调 mcmod 站内搜索 + 即时抓取 top 3 摘要。

### 8.4 `get_mod_info`
```python
def get_mod_info(mod_name_or_id: str) -> dict
```
查模组元信息：作者、Loader、依赖、支持版本。

### 8.5 `recommend_mods`（风格推荐）
```python
def recommend_mods(
    tags: list[str],                  # 如 ["恐怖", "黑暗"]
    mc_version: Optional[str] = None,
    loader: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]
```
基于 MySQL `mods.tags` 字段匹配（命中标签数排序）。返回模组名、简短理由、tags 列表、mcmod 链接。

### 8.6 `get_compatible_mods` / `check_mod_compatibility`（兼容性）
```python
def get_compatible_mods(mod_id: str) -> list[dict]
# 返回 [{"mod_id", "name_zh", "evidence", "common_mc_versions": [...], "source_url"}, ...]

def check_mod_compatibility(mod_a: str, mod_b: str) -> dict
# 返回 {"compatible": bool, "common_mc_versions": [...], "common_loader": str|None,
#       "known_integration": bool, "evidence": str|None}
```
数据来源：MySQL `mods.known_integrations` + `mods.mc_versions` + `mods.loader`。
兼容性回答必须包含 **MC 版本交集**。

### 8.5 错误约定

工具内部 try/except，返回 `{"error": "..."}`，不抛异常。Agent 据此降级。

## 9. 目录结构

```
mc-mod-qa/
├── pyproject.toml
├── .env.example
├── README.md
├── docker-compose.yml
├── config/
│   ├── settings.py
│   └── prompts/{router,answerer,critic}.txt
├── pipeline/
│   ├── crawl.py, build_index.py
│   ├── tag_mods.py, extract_integrations.py
│   ├── crawlers/{mcmod_list,mcmod_mod,recipe_parser}.py
│   ├── clean.py, structure.py, alias_builder.py
│   └── storage/{raw_cache,qdrant_writer,mysql_writer}.py
├── kb/
│   ├── retriever.py, filters.py, schemas.py
├── agents/
│   ├── workflow.py, events.py, memory.py
│   ├── router.py, retriever_agent.py, answerer.py, critic.py
├── tools/
│   ├── search_mcmod_kb.py, get_recipe.py
│   ├── web_search_mcmod.py, get_mod_info.py
│   ├── recommend_mods.py
│   ├── get_compatible_mods.py, check_mod_compatibility.py
├── llm/
│   ├── deepseek_client.py, embeddings.py
├── app/
│   ├── gradio_app.py, chat_handler.py
├── data/{mod_list.json, raw/, logs/}
├── scripts/{init_db.sql, reset_index.py}
└── tests/
    ├── unit/, integration/, fixtures/sample_mcmod_html/, eval/qa_set.jsonl
```

## 10. 错误处理

| 层 | 策略 |
|---|---|
| 爬取 | 重试 3 次（指数退避）→ 落地 `failed.jsonl` 单独重跑 |
| 入库 | fail-fast；断点续跑按 content_hash 去重 |
| LLM | tenacity 重试 3 次；最终失败返回降级回答 |
| 工具 | 内部 catch 返回 `{"error": ...}`，Agent 降级 |
| Critic 死循环 | 重试 2 次后返回 draft + ⚠️ 标注 |
| 知识库未命中 | 明确告知"未找到相关信息"，不强行生成 |

## 11. 日志

- loguru → `data/logs/{date}.log`
- 每会话生成 `trace_id`
- INFO：Router intent、检索 top_k、Critic 结果、最终回答
- DEBUG：工具调用参数和返回摘要

## 12. 测试策略

### 12.1 单元测试
- `test_router.py`：意图分类（mocked LLM）
- `test_retriever.py`：混合检索 + RRF + filter
- `test_critic.py`：3 类样本（正确/错误/答非所问）
- `test_tools.py`：各工具正常 + 异常分支
- `test_recipe_parser.py`：离线 HTML fixtures

### 12.2 集成测试
- `test_workflow.py`：真 LLM + 小型测试库，端到端 5~10 题
- `test_pipeline.py`：离线 fixtures 跑全流程

### 12.3 评估集
- `tests/eval/qa_set.jsonl`：50 题手工标注（query + 期望 mod_id / 关键词）
- 后续可加 LLM-as-Judge 自动评分

## 13. 配置 & 可观测

- 所有阈值集中在 `config/settings.py`：top_k=8、相似度阈值=0.5、Critic 重试=2、chunk_size=512、overlap=64、教程上限=30、memory token=8000
- Gradio UI 加 **"显示调试信息"开关**：开启时右侧栏展示 router intent / 检索 doc 标题 / Critic 反馈

## 14. 分阶段交付

**阶段 1（MVP）**
- 3~5 个模组完整爬取入库
- Router + Answerer + `search_mcmod_kb`
- Gradio 单轮问答跑通

**阶段 2（本设计目标）**
- 扩到 Top 20
- 加入 Retriever Agent（混合检索 + 自动兜底）
- 加入 Critic
- 加入 `get_recipe` / `web_search_mcmod` / `get_mod_info`
- 加入 `recommend_mods`（风格推荐，需先跑 `tag_mods` 离线打标 + 人工 review）
- 加入 `get_compatible_mods` / `check_mod_compatibility`（需先跑 `extract_integrations`）
- 多轮对话记忆
- 评估集 + 调试侧栏

## 15. 未覆盖 / 后续可扩展

- 模组开发者向问答（API/Mixin/Mapping）
- 多模组横向对比
- 整合包级别问答（依赖图）
- Critic 性能优化（按置信度触发）
- LLM-as-Judge 自动评分
- 用户反馈闭环（点赞/点踩用于改进）

## 16. 开源发布与运营

目标：项目最终发布到 GitHub，他人 clone 后可一键启动并自行构建知识库。

### 16.1 LICENSE
**MIT**。在仓库根目录放 `LICENSE` 文件。

### 16.2 README（中英双语）
- 顶部 1 个演示 GIF（Gradio 问答效果）
- Quick Start：
  ```bash
  git clone ...
  cp .env.example .env  # 填入 DEEPSEEK_API_KEY
  docker-compose up -d
  make init             # 建表 + 拉 embedding 模型
  make crawl-demo       # 用 3 个示例模组跑通
  make run              # 启动 Gradio
  ```
- 架构图、支持的问答类型、配置项说明、FAQ、Disclaimer

### 16.3 仓库文件清单
- `LICENSE`（MIT）
- `README.md` / `README_EN.md`
- `CONTRIBUTING.md`：代码风格、PR 流程、如何加新工具/Agent
- `CHANGELOG.md`：semver 版本日志
- `.github/`
  - `workflows/ci.yml`：ruff lint + pytest（仅 unit + mock 集成；不跑爬虫和真 LLM）
  - `ISSUE_TEMPLATE/{bug_report.md, feature_request.md}`
  - `PULL_REQUEST_TEMPLATE.md`
- `.gitignore`：`.env`、`data/`、`__pycache__`、模型缓存、IDE 文件
- `.pre-commit-config.yaml`：ruff + detect-secrets

### 16.4 配置与启动
- 所有可调参数和密钥走 `.env`，`.env.example` 列全
- 启动时 `pydantic-settings` 校验必填项，缺失给清晰错误提示
- 提供 `Makefile`：`init / crawl-demo / crawl-full / build-index / tag / extract-integrations / run / test / lint`

### 16.5 数据合规
- **不上传**爬取的 mcmod 原始数据到 git（`data/` 入 .gitignore）
- README 声明：项目本身不含任何模组/百科内容，使用者需自行遵守 mcmod.cn 使用条款
- 爬虫默认遵守 robots.txt、设置 1~2 秒请求间隔、UA 标明用途
- Disclaimer 段落：本项目仅作技术展示，对使用产生的合规问题不负责

### 16.6 国际化考虑
- 代码中关键模块 docstring 用英文
- 用户面文档（README/CONTRIBUTING）中英双语
- Prompt 模板中文（因为面向中文 mcmod 数据），但保留可替换接口便于后续扩展英文

### 16.7 安全
- `.env` / `data/` 严格入 .gitignore
- `pre-commit` 接 `detect-secrets` 钩子，提交前自动扫密钥
- API key 不写入日志（loguru 配置过滤敏感字段）

### 16.8 发布流程
- semver，GitHub Release tag（v0.1.0 起）
- 每次发布更新 CHANGELOG.md
- 首个 release v0.1.0 = 阶段 1 MVP 完成；v1.0.0 = 阶段 2 完整版完成
