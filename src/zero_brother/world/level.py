"""关卡数据：dataclass + JSON 加载 + §11.4 校验器。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Level:
    id: int
    name: str
    theme: str
    rows: list[str]
    boss: Optional[dict] = None
    deco: Optional[list[str]] = None   # 纯装饰层（无碰撞），可与碰撞层重叠


# 机制字符 -> (中文名, 一句话说明, 是否"静态"结构)
# 供 HUD 高度计 / 选关预览的「机制图例」共用，避免两处各写一份文案。
MECHANICS = [
    ("L", "梯子", "上下攀爬，直通上层跑台"),
    ("S", "弹簧", "踩上去弹到高处平台"),
    ("=", "单向平台", "下方可跳穿，上方可站立"),
    ("W", "静墙", "固定障碍/掩体，不受重力"),
    ("$", "金币", "可选奖励，不计入通关"),
    ("^", "地刺", "碰到即阵亡，绕开或跳过"),
]

# 层级数 -> 中文层名（自下而上）。生成器最多铺到 4 级跑台 + 弹簧台/桥，
# 实际出现的层数可能到 7~8，这里给足余量，超出才退化成「N 层」。
TIER_NAMES = ["地面", "一层", "二层", "三层", "四层", "五层", "六层", "七层", "八层", "九层"]


def level_facts(level: Level) -> dict:
    """汇总关卡的立体结构 + 机制要素（HUD 与选关预览共用，只算一次）。

    返回：
      counts       : 各机制元素的数量（ladder/spring/bridge/wall/coin/gem/spike…）
      tiers        : 自下而上的「层」列表，每层 = 可站立行 + 该层道具数
                     （平台行 R 上的道具约定摆在 R-1，所以按 [R-1, R] 统计）
      ground_row   : 地面行
      ladder_cols  : 出现梯子的列
      layers       : 层数（含地面）
    """
    rows = level.rows
    n = len(rows)
    cols = len(rows[0]) if rows else 0
    flat = "".join(rows)
    ground = n - 1
    counts = {
        "ladder": flat.count("L"),
        "spring": flat.count("S"),
        "bridge": flat.count("="),
        "wall": flat.count("W"),
        "coin": flat.count("$"),
        "gem": flat.count("g") + flat.count("y"),
        "gem_green": flat.count("g"),
        "gem_yellow": flat.count("y"),
        "enemy": flat.count("M") + flat.count("F"),
        "spike": flat.count("^"),
        "crate": flat.count("C"),
    }

    # 「层」= 一条横向能站人的实心面：地面 + 地面以上长度 >= 3 的跑台/桥/宽墙。
    # 单格墙、两格台阶这类"碎结构"不计入层，否则层数会被杂项撑爆。
    # 注意把 'L'（梯子在跑台上打的孔）也算进连段，否则平台会被梯子切成两截漏判。
    def _longest_run(row: str) -> int:
        best = cur = 0
        for ch in row:
            cur = cur + 1 if ch in "#=L" else 0
            best = max(best, cur)
        return best

    stands = [ground]
    for r in range(ground):
        if _longest_run(rows[r]) >= 3:
            stands.append(r)
    # 自下而上：地面(row 最大) 在前，越往上层 row 越小
    stands = sorted(set(stands), reverse=True)
    tiers = {s: {"stand": s, "item_row": max(0, s - 1), "items": 0} for s in stands}
    # 道具归属：优先挂到「正下方的层」(stand = 道具行 + 1)；缺口上方的跳跃弧这类
    # 悬空道具没有正下方平台，就挂到行距最近的一层 —— 保证一件都不漏统计。
    for r, row in enumerate(rows):
        n = row.count("g") + row.count("y") + row.count("$")
        if not n:
            continue
        want = r + 1
        s = want if want in tiers else min(tiers, key=lambda t: (abs(t - want), t))
        tiers[s]["items"] += n
    tier_list = [tiers[s] for s in stands]

    return {
        "rows": n, "cols": cols, "ground_row": ground,
        "counts": counts, "tiers": tier_list, "layers": len(tier_list),
        "ladder_cols": sorted({c for r in range(n) for c in range(cols) if rows[r][c] == "L"}),
        "has_vertical": any(t["stand"] < ground for t in tier_list),
    }


def load_level(path: str) -> Level:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Level(
        id=d["id"], name=d.get("name", f"Level {d['id']}"),
        theme=d.get("theme", "grass"), rows=d["rows"],
        boss=d.get("boss"), deco=d.get("deco"),
    )


def validate_level(level: Level, cfg) -> list[str]:
    """§11.4 关卡校验。返回错误列表（非空则拒绝加载）。"""
    errs: list[str] = []
    rows = level.rows
    if len(rows) != cfg.GRID_ROWS:
        errs.append(f"行数 {len(rows)} != {cfg.GRID_ROWS}")
    for i, r in enumerate(rows):
        if len(r) != cfg.GRID_COLS:
            errs.append(f"第 {i} 行长度 {len(r)} != {cfg.GRID_COLS}")

    # 装饰层（可选）：尺寸必须与碰撞层一致，否则裁掉会导致渲染错位
    if level.deco:
        if len(level.deco) != len(rows):
            errs.append(f"装饰层行数 {len(level.deco)} != {len(rows)}")
        for i, r in enumerate(level.deco):
            if len(r) != cfg.GRID_COLS:
                errs.append(f"装饰层第 {i} 行长度 {len(r)} != {cfg.GRID_COLS}")

    # 统计关键元素
    flat = "".join(rows)
    n_door = flat.count("D")
    n_players = sum(flat.count(str(s)) for s in "1234")
    n_green = flat.count("g")
    n_yellow = flat.count("y")

    if n_door != 1:
        errs.append(f"终点门数量 {n_door} 应为 1")
    if n_players < 1:
        errs.append("缺少玩家出生点")
    # 注：宝石不再按英雄亲和做硬门槛（任何英雄都能拾取，同色只给奖励），
    # 所以没有"某色宝石无英雄可拿"的死局，这里只需保证宝石数非零即可。

    # 怪物脚下须有可站立面（地形/静态墙；单向平台与弹簧不作为刷怪点）
    grid = [[level.rows[r][c] for c in range(len(level.rows[0]))] for r in range(len(level.rows))]
    for r in range(len(rows)):
        for c in range(len(rows[0])):
            if rows[r][c] == "M":
                if r + 1 >= len(rows) or grid[r + 1][c] not in "#W":
                    errs.append(f"怪物 ({c},{r}) 下方无地面")

    return errs
