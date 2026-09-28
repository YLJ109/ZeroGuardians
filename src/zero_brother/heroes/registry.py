"""英雄注册表 (GDD §8.2 / §8.3)。

6 英雄 × 2 技能 = 12 独立技能。基础移动对所有英雄一致（§8.1 #2），
技能只加额外能力。skill_a / skill_b 映射到 skills.py 中的实现函数名。
"""
from __future__ import annotations

HEROES: dict[str, dict] = {
    "archer":   {"name": "弓箭手·零零", "color": (90, 200, 120),  "gem": "green", "skill_a": "shoot",      "skill_b": "long_jump",  "unlock": 0},
    "builder":  {"name": "搬运工·砖哥", "color": (220, 170, 70),  "gem": "yellow", "skill_a": "place_box",   "skill_b": "recall_box", "unlock": 0},
    "ninja":    {"name": "忍者·影",     "color": (150, 150, 170), "gem": "any",    "skill_a": "double_jump", "skill_b": "dash",       "unlock": 4},
    "doormage": {"name": "门师·隙",     "color": (120, 170, 255), "gem": "any",    "skill_a": "portal_place","skill_b": "portal_swap", "unlock": 7},
    "warlock":  {"name": "术士·烬",     "color": (180, 120, 220), "gem": "green",  "skill_a": "hover",       "skill_b": "shockwave",  "unlock": 10},
    "hammer":   {"name": "重锤·岩",     "color": (200, 110, 90),  "gem": "yellow", "skill_a": "slam",        "skill_b": "lift_throw", "unlock": 13},
}

HERO_ORDER = ["archer", "builder", "ninja", "doormage", "warlock", "hammer"]

# 技能函数名 -> 中文显示名（UI 用；英文枚举一律汉化）
SKILL_NAMES = {
    "shoot": "射击", "long_jump": "远跳", "place_box": "放箱", "recall_box": "收箱",
    "double_jump": "二段跳", "dash": "冲刺", "portal_place": "布门", "portal_swap": "换门",
    "hover": "悬停", "shockwave": "冲击波", "slam": "重踏", "lift_throw": "举投",
}


def hero(id_: str) -> dict:
    return HEROES[id_]
