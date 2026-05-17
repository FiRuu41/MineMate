"""CLI: extract known mod integrations from descriptions via LLM."""
import argparse

from loguru import logger
from sqlalchemy import select

from config.logging import new_trace_id, setup_logging
from llm.deepseek_client import DeepSeekClient
from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod
from pipeline.storage.mysql_writer import update_mod_integrations

EXTRACT_PROMPT = """你是一个 Minecraft 模组专家。请从以下模组描述中，提取该模组明确提到的"兼容/联动/依赖/支持"的其他模组。

模组名称：{name}
模组描述：{description}

规则：
1. 只提取明确提到的其他模组名称（中文或英文）
2. 排除该模组自己的附属模组（如其 addon/extension）
3. 如果没有提到任何兼容/联动模组，返回空列表
4. 每个条目包含 mod_name_zh（如可知）、evidence（原文片段）、source_url

只返回 JSON：
{{"integrations": [{{"mod_name_zh": "应用能源2", "evidence": "与应用能源2完美兼容", "source_url": "{url}"}}]}}"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", help="single mod_id")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    setup_logging()
    new_trace_id()
    llm = DeepSeekClient()

    with SessionLocal() as session:
        q = select(Mod).where(Mod.description.isnot(None)).where(Mod.description != "")
        if args.mod:
            q = q.where(Mod.mod_id == args.mod)
        mods = session.execute(q).scalars().all()
        if args.limit:
            mods = mods[:args.limit]

    logger.info("extracting integrations for {} mods", len(mods))
    done = 0
    for m in mods:
        if not m.description or len(m.description) < 100:
            continue
        try:
            prompt = EXTRACT_PROMPT.format(
                name=m.name_zh, description=m.description[:2000], url=m.mcmod_url,
            )
            resp = llm.chat_json([{"role": "user", "content": prompt}])
            items = resp.get("integrations", [])
            if items:
                with SessionLocal() as s:
                    update_mod_integrations(s, m.mod_id, items)
                    s.commit()
                done += 1
        except Exception as e:
            logger.warning("[{}] extract failed: {}", m.mod_id, e)

    logger.info("extracted integrations for {} / {} mods", done, len(mods))


if __name__ == "__main__":
    main()
