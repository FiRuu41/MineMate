"""Recipe lookup tool (placeholder until recipe data is available)."""


def get_recipe(
    item_name: str,
    mod_id: str | None = None,
    direction: str = "how_to_craft",
) -> list[dict]:
    return [
        {
            "status": "not_available",
            "message": (
                "合成表功能需要预先爬取 mcmod 物品页合成框数据并存入 MySQL recipes 表。"
                "当前 recipes 表为空。请先运行爬虫采集合成表数据。"
            ),
        }
    ]
