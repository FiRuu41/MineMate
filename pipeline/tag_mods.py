"""CLI: tag mods via DeepSeek — concurrent version (10 workers)."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from sqlalchemy import select

from config.logging import new_trace_id, setup_logging
from llm.deepseek_client import DeepSeekClient
from pipeline.storage.db import SessionLocal
from pipeline.storage.models import Mod
from pipeline.storage.writer import update_mod_tags

VALID_GENRES = ["科技", "魔法", "冒险", "建筑", "农业", "RPG", "恐怖", "探索", "战斗", "交通",
                "存储", "装饰", "辅助", "优化", "生存", "奇幻", "科幻"]
VALID_THEMES = ["蒸汽朋克", "克苏鲁", "中世纪", "未来", "黑暗", "光明", "自然", "工业",
                "魔法", "龙与地下城", "日式", "中式", "北欧", "埃及", "太空"]
VALID_MOODS = ["治愈", "紧张", "探索", "放松", "硬核", "休闲", "搞笑", "恐怖", "温馨", "史诗"]
VALID_DIFFICULTIES = ["休闲", "普通", "硬核"]
VALID_POPULARITY = ["热门", "普通", "小众"]

TAG_PROMPT = (
    """你是一个 Minecraft 模组分类专家。请根据以下模组信息，为其打标签。

模组名称：{name}
模组描述：{description}

请从以下候选集中选择标签（可多选），并返回 JSON：

候选 genres（类型，必选1-3个）：{genres}
候选 themes（主题，可选0-2个）：{themes}
候选 mood（氛围，可选1个）：{moods}
候选 difficulty（难度，可选1个）：{difficulties}
候选 popularity（热度，1个）：{popularity}

popularity 判断标准：模组名气大、玩家众多、在各类整合包中常见 → "热门"；"""
    """一般模组 → "普通"；冷门小众 → "小众"。

只返回 JSON，格式：
{{"genres": ["科技"], "themes": ["蒸汽朋克"], "mood": "探索", """
    """"difficulty": "硬核", "popularity": "热门"}}"""
)


def build_tag_prompt(name: str, description: str) -> str:
    return TAG_PROMPT.format(
        name=name, description=description[:2000],
        genres=", ".join(VALID_GENRES), themes=", ".join(VALID_THEMES),
        moods=", ".join(VALID_MOODS), difficulties=", ".join(VALID_DIFFICULTIES),
        popularity=", ".join(VALID_POPULARITY),
    )


def parse_tags_response(resp) -> dict:
    if not isinstance(resp, dict):
        return {}
    tags: dict = {}
    for k in ("genres", "themes", "mood", "difficulty", "popularity"):
        v = resp.get(k)
        if v:
            tags[k] = v
    return tags


def _tag_one(m: Mod) -> tuple[str, dict | None]:
    """Tag a single mod. Returns (mod_id, tags_or_none)."""
    if not m.description or len(m.description) < 30:
        return (m.mod_id, None)
    try:
        llm = DeepSeekClient()
        prompt = build_tag_prompt(m.name_zh, m.description)
        resp = llm.chat_json([{"role": "user", "content": prompt}])
        tags = parse_tags_response(resp)
        return (m.mod_id, tags if tags else None)
    except Exception as e:
        logger.warning("[{}] tag failed: {}", m.mod_id, e)
        return (m.mod_id, None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mod", help="single mod_id")
    parser.add_argument("--limit", type=int, default=0, help="max mods to tag (0=all)")
    parser.add_argument("--workers", type=int, default=10, help="concurrent LLM calls")
    args = parser.parse_args()

    setup_logging()
    new_trace_id()

    with SessionLocal() as session:
        q = (
            select(Mod)
            .where(Mod.description.isnot(None))
            .where(Mod.description != "")
            .where(Mod.tags.is_(None))
        )
        if args.mod:
            q = q.where(Mod.mod_id == args.mod)
        mods = list(session.execute(q).scalars().all())
        if args.limit:
            mods = mods[:args.limit]

    logger.info("tagging {} mods with {} workers", len(mods), args.workers)

    tagged = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_tag_one, m): m for m in mods}
        for i, fut in enumerate(as_completed(futures)):
            mod_id, tags = fut.result()
            if tags:
                try:
                    with SessionLocal() as s:
                        update_mod_tags(s, mod_id, tags)
                        s.commit()
                    tagged += 1
                except Exception:
                    pass
            if (i + 1) % 100 == 0:
                logger.info("Progress: {}/{} tagged", tagged, i + 1)

    logger.info("tagged {} / {} mods", tagged, len(mods))


if __name__ == "__main__":
    main()
