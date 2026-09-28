"""关卡生成器 —— 多层立体平台跳跃关卡（含竖向交通与上层道具）。

设计依据（网上调研 + 物理复算，结论都写进了 tests/test_content.py）：

【节奏】四段式：开场(0~20%) 引入 → 发展(20~80%) 构建 → 高潮(80~95%) 挑战
        → 收尾 安全落点。先安全引入跳跃，再加大缺口，最后组合；每屏 2~3 个
        决策点，之间留呼吸空间；敌人「先见后危」，放在决策点而非装饰。

【可达性硬约束（由物理复算，不是拍脑袋）】
  - 单跳升高 ≈130px（2.6 格）：GRAVITY=1800, JUMP_VELOCITY=-684。
  - 水平跳距 ≈197px（≈3.9 格）。
  - 结论：**台阶高差 ≤ 2 行（100px）**，**地面缺口 ≤ 3 格**。
  - ≥3 行的高差一律必须用「梯子」或「弹簧」连接，否则不可达。

【立体结构：对角线阶梯】
  地面(row17) → 一层(row15) → 二层(row13) → 三层(row11) → 顶层(row9)
  相邻跑台**横向错开 1 列、抬高 2 行**，于是"跑过去起跳"必然能上去；
  这条链就是主路径，所有必收集的宝石都挂在链上或其上方 1~2 行。

【竖向交通】
  - 梯子：从地面直插某一层跑台（该层所在列打孔），是"快捷通道"，也是
    上层道具的保险通道。玩家上爬到梯顶会被钳制，左右走一步即站上平台。
  - 弹簧：放在地面缺口/缺口旁，把玩家弹上 row10 的"金币台"（可选奖励）。

【墙体（无重力）】
  墙(WALL) 是**静态实心瓦片**，用于障碍、掩体、跑台支柱；永不坠落。
  地面上的 1~2 格高墙是可跳过的障碍，高台下方是"看得见的支撑柱"。

【上层道具】
  宝石 / 金币 / 箱子 / 走怪都会出现在一层以上的跑台上，而不是只堆在地面。

关卡校验走 world.level.validate_level（§11.4）；主流程首跑自动写出。
"""
from __future__ import annotations

import json
import os
import random

ROWS, COLS = 18, 32
GROUND = 17          # 地面所在行
SPAWN_ROW = 16       # 出生/道具所在行（贴地）
DOOR_COL = 30
SAFE_END = DOOR_COL - 3   # 门前净空区起点：>= 此列之后不允许放置任何威胁/障碍
SAFE_START = 6            # 出生净空区终点
BUILD_END = SAFE_END - 1  # 可建造的最右列（27/28/29 留给门前净空）
THEMES = ["grass", "sand", "snow", "stone", "purple"]

# 阶梯行：每级抬高 2 行 = 100px < 单跳 130px → 单跳必然可达
TIER_ROWS = (15, 13, 11, 9)
# 高台/秘密层（弹簧或梯子到达，放可选金币）
SKY_ROW = 10

# 主题化关卡名（避免 HUD 出现「第 7 关 / 第 7 关」的重复）
LEVEL_NAMES = {
    1: "翠谷启程", 2: "流沙回廊", 3: "霜原足迹", 4: "磐岩裂谷",
    5: "幽孢之巢", 6: "藤蔓深林", 7: "驼铃沙丘", 8: "冰湖栈道",
    9: "熔岩石阶", 10: "菌王殿堂", 11: "云顶绿野", 12: "烈日迷宫",
    13: "暴雪尖塔", 14: "巨岩守望", 15: "终焉之门",
}

# Boss 关参数（§11.2）。主题固定为 stone / snow / purple，避免三关全落在同一主题；
# 关卡名与 HUD 里的 Boss 名（scenes/gameplay.BOSS_NAME）保持一致。
BOSS_THEME = {5: "stone", 10: "snow", 15: "purple"}
BOSS_LEVELS = {
    5:  {"name": "磐石魔像",   "phases": [3, 4],       "gems": 6,  "spikes": 2,  "boxes": 3},
    10: {"name": "霜牙守卫",   "phases": [3, 4, 5],    "gems": 10, "spikes": 4,  "boxes": 5},
    15: {"name": "幽孢女王",   "phases": [4, 5, 6, 7], "gems": 14, "spikes": 6,  "boxes": 6},
}
# Boss 悬浮中心（格）。取值经「站立射击线 y≈818」可达性校核：
# cy = 15.2 格 = 760px，命中盒 680~840 覆盖站立与多数跳跃射击高度。
BOSS_POS = {"x": 16, "y": 15.2}

# ---- 装饰层（纯视觉，无碰撞）----
DECO_CHARS = {
    "t": "tuft", "u": "bush", "r": "rock", "c": "cactus",
    "m": "mushroom", "z": "mushroom2", "w": "snowcap",
    "n": "sign", "o": "torch", "f": "fence", "h": "chain", "s": "star",
}
THEME_DECO = {
    "grass":  ["t", "t", "u", "m", "n", "r", "t"],
    "sand":   ["r", "c", "n", "t", "r"],
    "snow":   ["w", "r", "t", "n", "w"],
    "stone":  ["r", "t", "h", "n", "r"],
    "purple": ["m", "z", "u", "t", "n", "m"],
}


# ---------------------------------------------------------------------------
def project_root() -> str:
    """从本文件向上查找项目根（含 pyproject.toml 或 src/ 的目录）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.exists(os.path.join(cur, "pyproject.toml")) or os.path.isdir(os.path.join(cur, "src")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.normpath(os.path.join(here, "..", "..", ".."))


def levels_dir() -> str:
    """关卡 JSON 所在目录（<项目根>/data/levels）。"""
    return os.path.join(project_root(), "data", "levels")


# ---------------------------------------------------------------------------
# 网格基元
# ---------------------------------------------------------------------------
def _empty_grid():
    return [["." for _ in range(COLS)] for _ in range(ROWS)]


def _set(grid, c, r, ch):
    if 0 <= r < ROWS and 0 <= c < COLS:
        grid[r][c] = ch


def _get(grid, c, r):
    if 0 <= r < ROWS and 0 <= c < COLS:
        return grid[r][c]
    return "#"          # 界外当作地形，简化判定


def _free(grid, c, r):
    return 0 <= r < ROWS and 0 <= c < COLS and grid[r][c] == "."


def _place(grid, c, r, ch):
    """仅当目标格为空时写入，返回是否成功（所有布置都必须走这里）。"""
    if _free(grid, c, r):
        _set(grid, c, r, ch)
        return True
    return False


def _free_run(grid, row, c0, w):
    return all(_free(grid, c0 + k, row) for k in range(w))


def _run(grid, row, c0, w, ch="#"):
    for k in range(w):
        _set(grid, c0 + k, row, ch)


def _solid_below(grid, c, r):
    """(c, r) 正下方是不是可站立瓦片（地形 / 静墙 / 单向平台）。"""
    return _get(grid, c, r + 1) in "#W="


def _clear_around(grid, c, r, radius=1, chars="^MFCgy$"):
    """判断 (c,r) 周围 radius 范围内是否无 chars 中的元素（避免堆叠造成不公平）。

    敌人布置时传 chars="^MFC"：金币/宝石不算冲突（怪走过宝石只是视觉重叠）。
    """
    for dc in range(-radius, radius + 1):
        for dr in range(-radius, radius + 1):
            cc, rr = c + dc, r + dr
            if 0 <= rr < ROWS and 0 <= cc < COLS and grid[rr][cc] in chars:
                return False
    return True


def _safe_ground_col(grid, c):
    """该列地面可安全站立（自身及左右一格都是实心地形、且当前格为空）。"""
    return (0 < c < COLS - 1 and grid[GROUND][c] == "#"
            and grid[GROUND][c - 1] == "#" and grid[GROUND][c + 1] == "#")


def _clear_lane(grid, c_from, c_to):
    """把 [c_from, c_to) 列的贴地行清空（仅清威胁/道具，不动地形与出生/门）。"""
    for c in range(c_from, c_to):
        if grid[SPAWN_ROW][c] not in "1234D":
            grid[SPAWN_ROW][c] = "."


# ---------------------------------------------------------------------------
# 立体结构：对角线阶梯
# ---------------------------------------------------------------------------
def _staircase(idn, rng, grid):
    """沿对角线向上铺 2~4 层跑台，返回 [(row, c0, w)] 从低到高。

    相邻跑台横向错开 1 列、抬高 2 行：站在这层的右端跑过去起跳，落点就在
    上一层的最左端 —— 这是"单跳必然可达"的构造性保证。
    """
    steps = 2 if idn <= 3 else (3 if idn <= 9 else 4)
    runs = []
    c0 = rng.randint(8, 10)
    prev_end = None
    for i in range(steps):
        row = TIER_ROWS[i]
        w = rng.randint(4, 5) if i == 0 else rng.randint(3, 4)
        if i:
            c0 = prev_end + 1
        if c0 + w - 1 > BUILD_END or not _free_run(grid, row, c0, w):
            break
        _run(grid, row, c0, w)
        runs.append((row, c0, w))
        prev_end = c0 + w - 1
    return runs


def _clear_above(grid, c, r=SPAWN_ROW, need=2):
    """(c, r) 上方 need 格是否有跑台/墙。

    角色身高 56px：站在 row17 时头顶会顶到 row15 —— 所以"上层有跑台的正下方"
    是死空间，任何道具/敌人放进去都拿不到。所有贴地摆放都必须先过这一关。
    """
    for k in range(1, need + 1):
        if _get(grid, c, r - k) in "#W":
            return False
    return True


def _ladder_to(grid, rng, runs):
    """从地面插一条梯子到第二层跑台（快捷通道 + 上层道具的保险）。

    梯子列必须在目标层打孔（覆盖成 L），且下方 1..GROUND-1 全是空的 ——
    否则会被别的跑台挡住，玩家爬不上去。
    优先选**最右列**：从下层跳上来时的落点在左端，孔开在右端才不会踩空。
    """
    if len(runs) < 2:
        return None
    row, c0, w = runs[1]
    order = [c0 + w - 1, c0] + list(range(c0 + 1, c0 + w - 1))
    for col in order:
        if grid[GROUND][col] != "#":
            continue
        if not all(_free(grid, col, r) for r in range(row + 1, GROUND)):
            continue
        for r in range(row, GROUND):
            _set(grid, col, r, "L")     # 覆盖目标层那一格 = 在跑台上打孔
        return (row, col)
    return None


def _spring_ledge(grid, rng, runs, used_cols):
    """在地面缺口旁放一个弹簧，上方 row10 放一条"金币台"（可选奖励）。

    竖向关系（复算）：弹簧初速 1150 → 升高 ≈367px，从地面(row17)起跳脚底可达
    row8.6，因此 row10 的台子是够得到的；台子横向偏开 1~2 列，避免顶头。
    """
    taken = set(used_cols)
    cand = [c for c in range(SAFE_START, 14)
            if _free(grid, c, SPAWN_ROW) and grid[GROUND][c] == "#" and c not in taken
            # 弹簧正上方必须一路空着，否则弹上去会撞到跑台
            and all(_free(grid, c, r) for r in range(8, SPAWN_ROW))]
    if not cand:
        return None
    col = cand[len(cand) // 2]
    ledge_c0 = col + 1          # 台子偏开 1 列，避免"顶头"
    w = 3
    if ledge_c0 + w - 1 > BUILD_END or not _free_run(grid, SKY_ROW, ledge_c0, w):
        return None
    if not _place(grid, col, SPAWN_ROW, "S"):
        return None
    _run(grid, SKY_ROW, ledge_c0, w)
    for k in range(w):
        _place(grid, ledge_c0 + k, SKY_ROW - 1, "$")
    return col


# ---------------------------------------------------------------------------
# 发展关
# ---------------------------------------------------------------------------
def _normal_level(idn, rng, grid, theme):
    """发展关：地面(带缺口) → 对角线阶梯(多层跑台) → 上层道具 → 门前净空。

    0-20%  开场   : 平地 + 出生点，零威胁（教学关 L1-L3 完全无敌人）
    20-80% 发展   : 缺口/跑台逐步加高，引入墙、梯子、弹簧、敌人与地刺
    80-95% 高潮   : 最宽缺口 + 最高跑台 + 组合威胁（上层宝石 = 风险奖励）
    95-100% 收尾  : 门前一段净空安全区，给玩家喘息
    """
    diff = idn

    # 1) 地面 + 三处设计缺口（宽度递增：2 → 2~3 → 3；最后一处离门前净空留 1 列）
    for c in range(COLS):
        _set(grid, c, GROUND, "#")
    gaps = [(6, 2),
            (rng.randint(10, 13), rng.randint(2, 3)),
            (rng.randint(19, 23), 3)]
    for gc, gw in gaps:
        for k in range(gw):
            _set(grid, gc + k, GROUND, ".")

    # 2) 出生点（左端净空）/ 终点门（右端，门前 SAFE_END 起净空）
    for i in range(4):
        _set(grid, 1 + i, SPAWN_ROW, str(i + 1))
    _set(grid, DOOR_COL, SPAWN_ROW, "D")

    # 3) 立体结构：对角线阶梯 + 梯子 + 弹簧台
    runs = _staircase(idn, rng, grid)
    ladder = _ladder_to(grid, rng, runs)
    spring_col = None
    if diff >= 2:
        spring_col = _spring_ledge(grid, rng, runs, [g[0] for g in gaps])

    # 4) 上层单向平台（桥）：薄跳台，增加"上方也有落脚点"的层次感
    bridges = []
    if runs and diff >= 4:
        for _ in range(1 + diff // 6):
            row = runs[-1][0] - 2
            c0 = rng.randint(max(4, runs[-1][1] - 5), max(5, runs[-1][1] - 2))
            w = 3
            if row <= 6 or c0 + w - 1 > BUILD_END or not _free_run(grid, row, c0, w):
                continue
            _run(grid, row, c0, w, "=")
            bridges.append((row, c0, w))

    # 5) 地面小墙：1~2 格高的静墙障碍（跳过即可，顺便当掩体）
    for _ in range(min(3, 1 + diff // 5)):
        c = rng.randint(SAFE_START + 2, BUILD_END - 2)
        if not _free(grid, c, SPAWN_ROW) or grid[GROUND][c] != "#":
            continue
        h = 1 if diff < 8 else 2
        ok = all(_free(grid, c, SPAWN_ROW - k) for k in range(h)) and _clear_above(grid, c, SPAWN_ROW, 3)
        if ok and _solid_below(grid, c, SPAWN_ROW + h - 1):
            for k in range(h):
                _set(grid, c, SPAWN_ROW - k, "W")

    # 6) 敌人：先于道具放置（否则地面被金币铺满后怪就没地方站了）
    #    地面走怪放在开阔路径（先见后危）+ 上层走怪（立体巡逻）+ 空中飞行怪
    walkers = min(max(0, (diff - 2) // 2), 5)
    wcand = [c for c in range(SAFE_START + 2, SAFE_END)
             if _free(grid, c, SPAWN_ROW) and _safe_ground_col(grid, c) and _clear_above(grid, c)
             and _clear_around(grid, c, SPAWN_ROW, 1, "^MFC")]
    rng.shuffle(wcand)
    for c in wcand[:walkers]:
        _set(grid, c, SPAWN_ROW, "M")
    # 上层走怪：站在跑台上巡逻（脚下是跑台，校验器接受）
    if diff >= 8:
        for (row, c0, w) in runs[:2]:
            cc = c0 + w // 2
            if (w >= 4 and _free(grid, cc, row - 1) and _solid_below(grid, cc, row - 1)
                    and _clear_around(grid, cc, row - 1, 1, "^MFC")):
                _set(grid, cc, row - 1, "M")
                break
    flyers = min(4, max(0, (diff - 4) // 2))
    want, tries = flyers, flyers * 8
    while want > 0 and tries > 0:
        tries -= 1
        c, r = rng.randint(SAFE_START + 3, SAFE_END - 1), rng.randint(8, 12)
        if _free(grid, c, r) and _clear_around(grid, c, r, 1, "^MFC"):
            _set(grid, c, r, "F")
            want -= 1

    # 7) 地刺：贴地、左右各留安全落点、**上方必须无物**（不堆叠 + 视觉可读），
    #    且远离出生 / 门前净空
    spikes = min(diff // 3, 4)
    cand = [c for c in range(SAFE_START + 3, SAFE_END)
            if _free(grid, c, SPAWN_ROW) and _safe_ground_col(grid, c)
            and _free(grid, c - 1, SPAWN_ROW) and _free(grid, c + 1, SPAWN_ROW)
            and _get(grid, c, SPAWN_ROW - 1) == "."
            and _get(grid, c - 1, SPAWN_ROW - 1) in ".="
            and _get(grid, c + 1, SPAWN_ROW - 1) in ".="]
    rng.shuffle(cand)
    for c in cand[:spikes]:
        _set(grid, c, SPAWN_ROW, "^")

    # 8) 宝石：目标数量随难度上升。来源（全部满足可达性约束）
    target = min(4 + diff, 16)
    gems = 0
    # 8a) 每层跑台顶部（站上去即得，最稳的口粮）
    for (row, c0, w) in runs:
        if gems >= target:
            break
        if _place(grid, c0 + w // 2, row - 1, "g" if gems % 2 == 0 else "y"):
            gems += 1
        if gems < target and w >= 4 and _place(grid, c0 + w - 1, row - 1, "y" if gems % 2 == 0 else "g"):
            gems += 1
    # 8b) 单向平台上方（跳穿再下来拿）
    for (row, c0, w) in bridges:
        if gems >= target:
            break
        if _place(grid, c0 + w // 2, row - 1, "g" if gems % 2 == 0 else "y"):
            gems += 1
    # 8c) 缺口上方的「跳跃弧」：风险奖励
    for gc, gw in gaps:
        if gems >= target:
            break
        mid = gc + gw // 2
        if _place(grid, mid, SPAWN_ROW - 2, "g" if gems % 2 == 0 else "y"):
            gems += 1
        if gw >= 3 and gems < target and _place(grid, mid, SPAWN_ROW - 3, "y" if gems % 2 == 0 else "g"):
            gems += 1
    # 8d) 地面主路径（必须踩在实地上，且不在上层跑台的正下方 —— 否则是"够不到的死空间"）
    ground_cols = [c for c in range(3, SAFE_END)
                   if _free(grid, c, SPAWN_ROW) and grid[GROUND][c] == "#" and _clear_above(grid, c)]
    rng.shuffle(ground_cols)
    for c in ground_cols:
        if gems >= max(1, target * 3 // 4):
            break
        if _free(grid, c - 1, SPAWN_ROW) and _free(grid, c + 1, SPAWN_ROW):
            _set(grid, c, SPAWN_ROW, "g" if gems % 2 == 0 else "y")
            gems += 1
    if gems == 0:
        _set(grid, 4, SPAWN_ROW, "g")

    # 9) 金币：上层台面 + 地面弧线（可选奖励，不参与通关判定）
    for (row, c0, w) in runs[1:]:
        for k in range(w):
            _place(grid, c0 + k, row - 1, "$")
    for c in range(SAFE_START - 2, SAFE_END, 3):
        if (_free(grid, c, SPAWN_ROW) and _free(grid, c - 1, SPAWN_ROW) and _free(grid, c + 1, SPAWN_ROW)
                and grid[GROUND][c] == "#" and _clear_above(grid, c)):
            _place(grid, c, SPAWN_ROW, "$")

    # 10) 箱子：优先贴近最低层跑台（可叠高/搭桥），其余散布在地面
    boxes = min(2 + diff // 3, 8)
    placed = 0
    for (row, c0, w) in runs[:1]:
        for cc in (c0 + w, c0 - 1):
            if placed >= boxes:
                break
            if (0 < cc < SAFE_END and grid[GROUND][cc] == "#" and _clear_above(grid, cc)
                    and _place(grid, cc, SPAWN_ROW, "C")):
                placed += 1
                break
    ccand = [c for c in range(SAFE_START - 2, SAFE_END)
             if _free(grid, c, SPAWN_ROW) and _clear_above(grid, c)]
    rng.shuffle(ccand)
    for c in ccand:
        if placed >= boxes:
            break
        _set(grid, c, SPAWN_ROW, "C")
        placed += 1

    # 11) 最终净空：门前 SAFE_END..DOOR_COL-1 一律清空（保底，防上面任一步漏判）
    _clear_lane(grid, SAFE_END, DOOR_COL)
    _clear_lane(grid, 0, 1)
    return {"runs": runs, "gaps": gaps, "ladder": ladder, "spring_col": spring_col,
            "bridges": bridges}


# ---------------------------------------------------------------------------
# Boss 关
# ---------------------------------------------------------------------------
def _boss_level(idn, rng, grid, theme):
    """Boss 关：立体竞技场。

    地面竞技场 + 左右高台(row14，各自配一格台阶 row15，制造 2 行内的可跳高差)
    + 中央跳台(row12，用梯子直上) + 静墙掩体 + 边缘地刺（只放在无人区）。
    立体走位是核心：地面躲弹、上台阶、爬梯上中央台。
    """
    spec = BOSS_LEVELS[idn]
    for c in range(COLS):
        _set(grid, c, GROUND, "#")
    for i in range(4):
        _set(grid, 1 + i, SPAWN_ROW, str(i + 1))
    _set(grid, DOOR_COL, SPAWN_ROW, "D")

    # 左右高台（测试依赖 row14 cols 5..8 == "####"）
    for c0 in (5, 23):
        _run(grid, 14, c0, 4)
    # 台阶：每侧一块 row15 跳台，把地面(row17) → 高台(row14) 的 3 行落差拆成 2+1
    for c0 in (10, 20):
        _run(grid, 15, c0, 2)
    # 中央跳台（row12）+ 梯子直上（梯子在 col16 打孔）
    _run(grid, 12, 15, 3)
    for r in range(12, GROUND):
        _set(grid, 16, r, "L")
    # 静墙掩体：中央两侧各一堵 1 格高墙（可站、可躲）
    for c in (12, 19):
        if _free(grid, c, SPAWN_ROW):
            _set(grid, c, SPAWN_ROW, "W")

    # 宝石：地面 / 台阶 / 高台 / 中央跳台 交错，避免一条直线
    spots = []
    for c in range(SAFE_START, SAFE_END):
        spots.append((c, SPAWN_ROW))
    for c0 in (10, 11, 20, 21):
        spots.append((c0, 14))
    for c0 in (5, 6, 7, 8, 23, 24, 25, 26):
        spots.append((c0, 13))
    for c0 in (15, 16, 17):
        spots.append((c0, 11))
    rng.shuffle(spots)
    gems = 0
    for (c, r) in spots:
        if gems >= spec["gems"]:
            break
        if r == 11 and c == 16:      # 梯子孔，跳过
            continue
        if _place(grid, c, r, "g" if gems % 2 == 0 else "y"):
            gems += 1
    # 金币：铺在左右高台上方，鼓励上台阶走位
    for c0 in (5, 23):
        for k in range(4):
            _place(grid, c0 + k, 13, "$")
    # 地刺：仅放在两侧「无人区」，中间留出安全走位带
    cand = [c for c in list(range(3, 9)) + list(range(24, SAFE_END))
            if _free(grid, c, SPAWN_ROW) and _free(grid, c - 1, SPAWN_ROW)
            and _free(grid, c + 1, SPAWN_ROW) and _safe_ground_col(grid, c)]
    rng.shuffle(cand)
    for c in cand[:spec["spikes"]]:
        _set(grid, c, SPAWN_ROW, "^")
    # 箱子：作为掩体/台阶，只放中间开阔带
    cand = [c for c in range(10, 22) if _free(grid, c, SPAWN_ROW)]
    rng.shuffle(cand)
    for c in cand[:min(spec["boxes"], 10)]:
        _set(grid, c, SPAWN_ROW, "C")
    # 门前净空保底
    _clear_lane(grid, SAFE_END, DOOR_COL)
    return {"runs": [(14, 5, 4), (14, 23, 4), (15, 10, 2), (15, 20, 2), (12, 15, 3)],
            "gaps": [], "ladder": (12, 16), "spring_col": None, "bridges": []}


# ---------------------------------------------------------------------------
# 装饰层（纯视觉）
# ---------------------------------------------------------------------------
def _deco_layer(rng, grid, theme, meta, boss):
    """在地面/跑台上撒装饰：只在碰撞层为空的位置放，绝不遮住道具。"""
    rows = [["." for _ in range(COLS)] for _ in range(ROWS)]
    palette = THEME_DECO.get(theme, THEME_DECO["grass"])

    def put(c, r):
        # 只在碰撞层为空（或单向平台）的位置放装饰：绝不遮挡道具/威胁
        if rows[r][c] != "." or grid[r][c] not in ".=":
            return False
        rows[r][c] = rng.choice(palette)
        return True

    # 地面上的自然物（出生段稀、发展段密）
    for c in range(2, SAFE_END + 1):
        if grid[GROUND][c] != "#" or not _free(grid, c, SPAWN_ROW):
            continue
        if c < SAFE_START:
            if c in (2, 5):
                put(c, SPAWN_ROW)
            continue
        if rng.random() < 0.45:
            put(c, SPAWN_ROW)
    # 跑台上的小装饰
    for (row, c0, w) in meta.get("runs", []):
        if rng.random() < 0.5:
            put(c0 + w - 1, row - 1)
    # 门前指引：路牌 + 火把
    for c in (SAFE_END - 1, SAFE_END + 1):
        if _free(grid, c, SPAWN_ROW) and rows[SPAWN_ROW][c] == ".":
            rows[SPAWN_ROW][c] = "n" if c == SAFE_END - 1 else "o"
    # 起点附近一面小旗当作"出发标记"
    if grid[SPAWN_ROW][0] in ".=":
        rows[SPAWN_ROW][0] = "n"
    # Boss 关：中央上方挂一个装饰星（呼应 Boss 光环）
    if boss and rows[9][16] == ".":
        rows[9][16] = "s"
    return ["".join(r) for r in rows]


# ---------------------------------------------------------------------------
def generate_level(idn: int, rng: random.Random) -> dict:
    grid = _empty_grid()
    theme = BOSS_THEME.get(idn) or THEMES[(idn - 1) % len(THEMES)]
    if idn in BOSS_LEVELS:
        meta = _boss_level(idn, rng, grid, theme)
        name = BOSS_LEVELS[idn]["name"]
        boss = {"phases": BOSS_LEVELS[idn]["phases"], "x": BOSS_POS["x"], "y": BOSS_POS["y"]}
    else:
        meta = _normal_level(idn, rng, grid, theme)
        name = LEVEL_NAMES.get(idn, f"第 {idn} 关")
        boss = None
    deco = _deco_layer(rng, grid, theme, meta, boss is not None)
    return {
        "id": idn, "name": name, "theme": theme,
        "rows": ["".join(r) for r in grid], "deco": deco, "boss": boss,
    }


def generate_all(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for idn in range(1, 16):
        rng = random.Random(1000 + idn)  # 确定性
        lvl = generate_level(idn, rng)
        with open(os.path.join(out_dir, f"level_{idn}.json"), "w", encoding="utf-8") as f:
            json.dump(lvl, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    generate_all(levels_dir())
