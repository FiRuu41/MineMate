# mc-mod-qa

基于 mcmod.cn 的 Minecraft 模组智能体问答系统（阶段 1 MVP）。

## Quick Start

```bash
cp .env.example .env  # 填入 DEEPSEEK_API_KEY
docker-compose up -d
uv sync
make init
make crawl-demo
make build-index
make run
```

详细文档见 `docs/superpowers/specs/`。
