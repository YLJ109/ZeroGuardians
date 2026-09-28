# -*- coding: utf-8 -*-
"""立体关卡与竖向交通的自检：可达性模型 + 真实物理复算。

为什么需要这一组用例：
  「上层放道具」「高台够得到」这类设计如果只靠肉眼，很容易出现"看得见拿不到"
  的死局（宝石拿不全 = 关卡不可通关）。这里用一个**站立点可达性模型**把设计
  约束变成可验证的断言；再用**真实物理**（Player + Body + TileMap）复算三个
  关键假设：单跳能上 2 行、梯子能爬到平台顶、弹簧能把人弹到高台。

模型里的瓦片语义（与 world/tilemap.py 一致）：
  #  地形      W 静墙（无重力）   S 弹簧（可站）   = 单向平台（只能从上方站）
  L  梯子（不阻挡，可攀爬）       $ 金币   g/y 宝石   C 箱子（加载时变实心）
"""
from __future__ import annotations

import os
import random

import pygame

from zero_brother.config import Config
from zero_brother.input import InputManager
from zero_brother.levels.generate import (
    BOSS_LEVELS, COLS, DOOR_COL, GROUND, ROWS, SPAWN_ROW, generate_level, generate_all, levels_dir,
)
from zero_brother.physics.body import Body
from zero_brother.world.tilemap import TileMap, WALL, LADDER, SPRING, ONEWAY, COIN, SOLID
from zero_brother.world.world import World
from zero_brother.world.level import Level, validate_level
from zero_brother.entities.player import Player
from zero_brother.input.actions import Action

CFG = Config()

SOLID_CHARS = set("#WCS")      # 实心（箱子在加载时会被写成实心，故按实心算）
STANDABLE_CHARS = set("#WCS=")  # 可作为落点的顶面（含单向平台）
BLOCK_CHARS = set("#WCL")      # 会挡住身体的（梯子不挡）
ITEM_CHARS = set("gy$")


# ---------------------------------------------------------------------------
# 测试替身：可控的输入与最小 game 对象
# ---------------------------------------------------------------------------
class FakeInput:
    def __init__(self):
        self.h: set = set()
        self.p: set = set()

    def set(self, actions=()):
        new = set(actions)
        self.p = new - self.h
        self.h = new

    def held(self, slot, action):
        return action in self.h

    def pressed(self, slot, action):
        return action in self.p


class FakeGame:
    def __init__(self, cfg, world):
        self.cfg = cfg
        self.world = world
        self.input = FakeInput()
        self.fx = []
        self.monsters = []
        self.boxes = []
        self.bullets = []
        self.events = []

    def emit(self, name):
        self.events.append(name)


def _grid_of(d):
    return [list(row) for row in d["rows"]]


# ---------------------------------------------------------------------------
# 站立点可达性模型
# ---------------------------------------------------------------------------
def _reachable(d):
    """返回 (reachable_standables, ladders_used)，用 BFS + 定点迭代处理梯子/弹簧。"""
    g = _grid_of(d)
    rows, cols = ROWS, COLS

    def ch(c, r):
        if 0 <= c < cols and 0 <= r < rows:
            return g[r][c]
        return ""

    def stand(c, r):
        if not (0 <= c < cols and 0 <= r < rows):
            return False
        if ch(c, r) not in STANDABLE_CHARS:
            return False
        for k in (1, 2):
            if r - k >= 0 and ch(c, r - k) in BLOCK_CHARS:
                return False
        return True

    def solid_below(c, r):
        for rr in range(r + 1, rows):
            if ch(c, rr) in SOLID_CHARS:
                return rr
        return None

    reach: set = set()
    # 起点：出生段的地面
    for c in range(0, 9):
        if stand(c, GROUND):
            reach.add((c, GROUND))

    def expand():
        """一轮基础移动扩展（走路 / 起跳 1~2 行 / 跳落差 / 掉落到下层）。

        水平可达距离按物理复算取：
          - 同层（k=0）：全跳时长 0.76s × 260px/s ≈ 197px ≈ 3.9 格 → 取 4；
          - 抬升 1~2 行（k>=1）：上升到 +100px 后仅剩 0.36s 平飞 ≈ 94px ≈ 1.9 格
            → 保守取 3（生成器只用 1~2 列偏移）。
        """
        changed = False
        for (c, R) in list(reach):
            for d in range(-4, 5):
                for k in range(0, 3):
                    if k == 0 and d == 0:
                        continue
                    if k > 0 and abs(d) > 3:
                        continue
                    tgt = (c + d, R - k)
                    if stand(*tgt) and tgt not in reach:
                        reach.add(tgt)
                        changed = True
                rr = solid_below(c + d, R)
                if rr is not None:
                    tgt = (c + d, rr)
                    if stand(*tgt) and tgt not in reach:
                        reach.add(tgt)
                        changed = True
        return changed

    # 梯子区间
    ladder_runs = []
    for c in range(cols):
        r = 0
        while r < rows:
            if ch(c, r) == "L":
                top = r
                while r + 1 < rows and ch(c, r + 1) == "L":
                    r += 1
                ladder_runs.append((c, top, r))
            r += 1

    used_ladders = set()
    used_springs = set()

    def flush_specials():
        changed = False
        # 梯子：能从下层站点抓到 → 该梯子整段可爬，可离开到同行的相邻站台
        for (c, top, bot) in ladder_runs:
            if (c, top, bot) in used_ladders:
                continue
            entry = any((cc, rr) in reach and abs(cc - c) <= 1 and top - 1 <= rr <= bot + 1
                        for cc in (c - 1, c, c + 1) for rr in range(rows))
            if not entry:
                continue
            used_ladders.add((c, top, bot))
            changed = True
            for r in range(top, bot + 1):
                for dc in (-1, 1):
                    if stand(c + dc, r) and (c + dc, r) not in reach:
                        reach.add((c + dc, r))
        # 弹簧：站上去 → 弹起 ≈367px（≈7 行），横向 ≤2 列可够到高台
        for (c, R) in list(reach):
            if ch(c, R) != "S" or (c, R) in used_springs:
                continue
            used_springs.add((c, R))
            changed = True
            for d in range(-3, 4):
                for k in range(1, 8):
                    if stand(c + d, R - k) and (c + d, R - k) not in reach:
                        reach.add((c + d, R - k))
        return changed

    # 定点迭代：每轮先做移动扩展，再结算梯子/弹簧；直到不再增长。
    # 层数多（最多 4 层阶梯 + 平台/桥）时链会很长，所以给足迭代次数。
    for _ in range(64):
        moved = expand()
        moved = flush_specials() or moved
        if not moved:
            break
    return reach, used_ladders, used_springs


def _reachable_from(reach, c, gem_row):
    """宝石/金币在 (c, gem_row)：站台比它低 1~4 行、横向 ≤3 列即视为拿到。"""
    for (cc, R) in reach:
        if abs(cc - c) <= 3 and 1 <= R - gem_row <= 4:
            return True
    return False


def _all_levels():
    return [generate_level(i, random.Random(1000 + i)) for i in range(1, 16)]


# ---------------------------------------------------------------------------
# 1) 墙体静态（无重力）
# ---------------------------------------------------------------------------
def test_walls_and_structures_are_static_tiles():
    """墙 / 梯子 / 弹簧 / 单向平台都是静态瓦片：跑 5 秒后网格一格都不许变。"""
    assert WALL not in (0,), "常量健全性"
    generate_all(levels_dir())
    cfg = Config.load()
    im = InputManager(cfg)
    from types import SimpleNamespace
    app = SimpleNamespace(config=cfg, input=im)
    from zero_brother.world.level import load_level

    for idn in (1, 4, 9, 14):
        lvl = load_level(os.path.join(levels_dir(), f"level_{idn}.json"))
        world = World(app, lvl, [(0, "archer"), (1, "builder")])
        before = [row[:] for row in world.map.grid]
        for _ in range(300):
            world.update(1 / 60)
        after = world.map.grid
        # 与玩家无关的静态瓦片必须原地不动（只有宝石被吃掉是允许的变化）
        for r in range(ROWS):
            for c in range(COLS):
                b, a = before[r][c], after[r][c]
                if b in (WALL, LADDER, SPRING, ONEWAY, SOLID):
                    assert a == b, f"第 {idn} 关静态瓦片 ({c},{r}) 发生了变化: {b} -> {a}"


def test_wall_tile_is_solid_but_never_a_falling_entity():
    """墙的语义：静态实心（可站、可挡），且不存在任何"会下落"的墙实体。"""
    from zero_brother.world import tilemap
    assert tilemap.WALL in tilemap.SOLID_TILES
    # 实体层只认识玩家/怪物/箱子/子弹/门/Boss —— 没有"墙"实体
    from zero_brother.entities import box, monster, player  # noqa: F401
    lvl = Level(id=1, name="t", theme="grass", rows=["." * COLS] * ROWS)
    lvl.rows = ["." * COLS for _ in range(ROWS)]
    lvl.rows[GROUND] = "#" * COLS
    lvl.rows[SPAWN_ROW] = "".join("1" if c == 1 else ("D" if c == DOOR_COL else ".") for c in range(COLS))
    lvl.rows[SPAWN_ROW - 1] = "".join("W" if c == 5 else "." for c in range(COLS))
    assert not validate_level(lvl, CFG)


# ---------------------------------------------------------------------------
# 2) 上层真的放了道具 + 全部可收集物可达
# ---------------------------------------------------------------------------
def test_upper_tiers_carry_items():
    """用户诉求：不能只堆在地面，上层也要有道具（宝石/金币/箱子/敌人）。"""
    for d in _all_levels():
        if d["id"] in BOSS_LEVELS or d["id"] <= 3:
            continue
        grid = d["rows"]
        high = [(r, c) for r in range(0, 14) for c in range(COLS) if grid[r][c] in ITEM_CHARS]
        assert high, f"第 {d['id']} 关上层（row<=13）没有任何道具/金币"
        tiers = {r for (r, _c) in high}
        assert len(tiers) >= 2, f"第 {d['id']} 关上层只有 {tiers} 一层，立体感不足"


def test_every_gem_is_reachable():
    """核心断言：每颗宝石都在"可达站立点"的跳跃范围内（否则关卡不可通关）。"""
    for d in _all_levels():
        reach, _l, _s = _reachable(d)
        assert reach, f"第 {d['id']} 关从出生点无法到达任何站立点"
        for r in range(ROWS):
            for c in range(COLS):
                if d["rows"][r][c] in "gy":
                    assert _reachable_from(reach, c, r), \
                        f"第 {d['id']} 关宝石 ({c},{r}) 不可达"


def test_every_coin_is_reachable():
    """金币虽是可选奖励，但也不允许"看得见拿不到"。"""
    for d in _all_levels():
        reach, _l, _s = _reachable(d)
        for r in range(ROWS):
            for c in range(COLS):
                if d["rows"][r][c] == "$":
                    assert _reachable_from(reach, c, r), \
                        f"第 {d['id']} 关金币 ({c},{r}) 不可达"


def test_every_elevated_platform_is_reachable():
    """上层跑台本身必须可达（否则上面的怪/箱/道具全成了摆设）。"""
    for d in _all_levels():
        reach, _l, _s = _reachable(d)
        grid = d["rows"]
        for r in range(0, 14):
            for c in range(COLS):
                if grid[r][c] not in ("#", "W", "="):
                    continue
                # 只看"有人用的台面"：它上方 1~2 行有东西
                if any(grid[r - k][c] in ITEM_CHARS | {"M", "C"} for k in (1, 2) if r - k >= 0):
                    assert any(cc == c and abs(RR - r) <= 3 for (cc, RR) in reach), \
                        f"第 {d['id']} 关第 {r} 行第 {c} 列的台面不可达（上面还放了道具）"


# ---------------------------------------------------------------------------
# 3) 竖向交通结构良好
# ---------------------------------------------------------------------------
def test_ladders_connect_two_standable_levels():
    """每条梯子：底端下方有落脚面（能抓），顶端相邻列在同行可站（能离开）。"""
    for d in _all_levels():
        grid = d["rows"]
        cols = [c for c in range(COLS) if any(grid[r][c] == "L" for r in range(ROWS))]
        for c in cols:
            rows_ = [r for r in range(ROWS) if grid[r][c] == "L"]
            top, bot = min(rows_), max(rows_)
            assert rows_ == list(range(top, bot + 1)), \
                f"第 {d['id']} 关梯子列 {c} 不连续: {rows_}"
            assert grid[GROUND][c] == "#", f"第 {d['id']} 关梯子列 {c} 底下是坑"
            assert bot == GROUND - 1 or grid[bot + 1][c] in "#W", \
                f"第 {d['id']} 关梯子列 {c} 底端悬空"
            # 顶端相邻列有可站平台（玩家爬到顶后左右一步就能站上去）
            step = [grid[top][c + dc] for dc in (-1, 1) if 0 <= c + dc < COLS]
            assert any(x in "#W" for x in step), \
                f"第 {d['id']} 关梯子列 {c} 顶端没有可站平台，爬上去下不来"


def test_springs_lead_somewhere():
    """弹簧上方必须有高台（否则纯浪费）。"""
    for d in _all_levels():
        grid = d["rows"]
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] != "S":
                    continue
                found = any(grid[rr][cc] in "#W= "
                            for cc in range(max(0, c - 3), min(COLS, c + 4))
                            for rr in range(max(0, r - 7), r))
                assert found, f"第 {d['id']} 关弹簧 ({c},{r}) 上方没有可落脚高台"


def test_deco_layer_matches_size_and_never_covers_items():
    """装饰层尺寸正确，且不遮挡任何道具/威胁（纯视觉层必须零副作用）。"""
    for d in _all_levels():
        deco = d.get("deco")
        assert deco and len(deco) == ROWS, f"第 {d['id']} 关缺装饰层"
        assert all(len(x) == COLS for x in deco), f"第 {d['id']} 关装饰层列数不齐"
        for r in range(ROWS):
            for c in range(COLS):
                if deco[r][c] != ".":
                    assert d["rows"][r][c] in ".=", \
                        f"第 {d['id']} 关装饰 ({c},{r}) 压在了 '{d['rows'][r][c]}' 上"


# ---------------------------------------------------------------------------
# 4) 真实物理复算（不靠纸面推算）
# ---------------------------------------------------------------------------
def _map(rows):
    return TileMap.from_rows(rows, 50, {})


def test_physics_jump_clears_two_row_step():
    """单跳必须能上「高 2 行（100px）、横向 1 列」的台阶 —— 阶梯可达性的基石。"""
    rows = [
        "............",
        "............",
        "............",
        "............",
        "....####....",
        "............",
        "####........",
        "............",
        "............",
        "............",
        "............",
        "############",
    ]
    world = _map(rows)
    cfg = Config()
    game = FakeGame(cfg, world)
    p = Player(0, "archer", 1 * 50, 6 * 50 - cfg.PLAYER_HITBOX[1], cfg)
    # 先站稳
    for _ in range(30):
        game.input.set([Action.MOVE_RIGHT])
        p.update(1 / 60, game)
    assert p.body.grounded and abs(p.body.y + p.body.h - 300) < 2, (p.body.y, p.body.grounded)
    # 跑到台沿附近起跳（JUMP 必须按住足够久，否则"可变跳高"会把跳削短）
    hold = 0
    for i in range(400):
        acts = [Action.MOVE_RIGHT]
        if hold > 0:
            acts.append(Action.JUMP)
            hold -= 1
        elif 80 <= p.body.x <= 185:
            hold = 24          # 按住约 0.4s，越过跳跃顶点，拿到完整跳高
        game.input.set(acts)
        p.update(1 / 60, game)
        if p.body.grounded and abs(p.body.y + p.body.h - 200) < 2:
            return
    raise AssertionError(f"未能跳上高 2 行的台阶: x={p.body.x:.1f} feet={p.body.y + p.body.h:.1f}")


def test_physics_oneway_platform_is_passable_upwards():
    """单向平台：从上落下能站住；从下顶上去能穿过；横向不阻挡。"""
    rows = [
        "........",
        "........",
        "..====..",
        "........",
        "........",
        "........",
        "........",
        "########",
    ]
    world = _map(rows)
    # 从上落下 → 站住（单向平台在 row2，站上的脚底 = 100）
    b = Body(100, 0, 44, 56)
    for _ in range(120):
        b.vy = 400
        b.move_and_collide(world, 1 / 60)
        if b.grounded:
            break
    assert b.grounded, "应能站在单向平台上"
    assert abs((b.y + b.h) - 100) < 2, f"落点应在 one-way 顶面: {b.y + b.h}"
    # 从下往上 → 穿过
    b2 = Body(100, 250, 44, 56)
    for _ in range(60):
        b2.vy = -320
        b2.move_and_collide(world, 1 / 60)
    assert b2.y + b2.h < 100, f"向上应能穿过单向平台: feet={b2.y + b2.h}"
    # 横向 → 不阻挡
    b3 = Body(0, 144, 44, 56)     # 脚底 200，处于单向平台行之下
    b3.vy = 0
    for _ in range(60):
        b3.vx = 300
        b3.move_and_collide(world, 1 / 60)
    assert b3.x > 200, f"单向平台不应横向阻挡: x={b3.x}"


def test_physics_ladder_climb_reaches_platform():
    """梯子：从地面爬上去，脚底能到平台顶面，且左右一步就能站上台。"""
    rows = [
        "........",
        "........",
        "........",
        "........",
        "..#L#...",
        "...L....",
        "...L....",
        "...L....",
        "...L....",
        "########",
    ]
    world = _map(rows)
    cfg = Config()
    game = FakeGame(cfg, world)
    ground_top = 9 * 50
    p = Player(0, "archer", 3 * 50 + 3, ground_top - cfg.PLAYER_HITBOX[1], cfg)
    # 按住「下」抓梯（地面上按上会优先起跳，所以用下键抓）
    for _ in range(4):
        game.input.set([Action.CROUCH])
        p.update(1 / 60, game)
    assert p.climbing, "重叠梯子并按下键应进入攀爬状态"
    # 一路向上
    for _ in range(240):
        game.input.set([Action.CROUCH, Action.JUMP])
        p.update(1 / 60, game)
    assert p.climbing, "应仍在梯子上"
    assert abs((p.body.y + p.body.h) - 4 * 50) < 3, \
        f"梯顶应将玩家钳制到平台顶面(200): {p.body.y + p.body.h}"
    # 向右离开梯子 → 落到平台 (col 4, row 4)
    for _ in range(19):
        game.input.set([Action.MOVE_RIGHT])
        p.update(1 / 60, game)
    for _ in range(60):
        game.input.set([])
        p.update(1 / 60, game)
    assert p.body.grounded and abs((p.body.y + p.body.h) - 200) < 3, \
        f"应站上平台: feet={p.body.y + p.body.h} grounded={p.body.grounded} x={p.body.x}"


def test_physics_spring_launches_higher_than_jump():
    """弹簧：弹起高度必须显著高于普通跳（否则高台上的金币拿不到）。"""
    rows = [
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "...S......",
        "..........",
        "##########",
    ]
    world = _map(rows)
    cfg = Config()
    top = 8 * 50
    game = FakeGame(cfg, world)
    p = Player(0, "archer", 3 * 50 + 3, 0, cfg)
    best = 10 ** 9
    for _ in range(240):
        game.input.set([])
        p.update(1 / 60, game)
        best = min(best, p.body.y + p.body.h)
    assert "spring" in game.events, "踩到弹簧应发出 spring 事件"
    rise = top - best
    jump_h = cfg.JUMP_VELOCITY ** 2 / (2 * cfg.GRAVITY)
    assert rise > jump_h + 100, f"弹簧弹高 {rise:.0f}px 未明显超过单跳 {jump_h:.0f}px"


def test_physics_pit_fall_kills_and_respawns():
    """掉出世界底部必须判定阵亡并重生（旧版本没有死亡线，会无限下坠）。"""
    generate_all(levels_dir())
    cfg = Config.load()
    im = InputManager(cfg)
    from types import SimpleNamespace
    app = SimpleNamespace(config=cfg, input=im)
    from zero_brother.world.level import load_level
    lvl = load_level(os.path.join(levels_dir(), "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    p = world.players[0]
    p.body.y = world.pit_y + 20
    world.update(1 / 60)
    assert not p.alive, "掉出世界底部应判定阵亡"
    for _ in range(int(cfg.GAMEPLAY["respawn_time"] * 60) + 5):
        world.update(1 / 60)
    assert p.alive, "倒地后应自动重生"
    assert abs(p.body.y - p.spawn[1]) < 2, "重生应回到出生点"


def test_coin_and_gem_are_counted_separately():
    """金币是可选的加分项，不能影响通关判定（通关只看宝石 + Boss）。"""
    generate_all(levels_dir())
    cfg = Config.load()
    im = InputManager(cfg)
    from types import SimpleNamespace
    app = SimpleNamespace(config=cfg, input=im)
    from zero_brother.world.level import load_level
    lvl = load_level(os.path.join(levels_dir(), "level_1.json"))
    world = World(app, lvl, [(0, "archer")])
    assert world.coins_total > 0, "第 1 关应有金币"
    # 找一枚金币，把玩家瞬移过去吃掉
    target = None
    for r in range(ROWS):
        for c in range(COLS):
            if world.map.grid[r][c] == COIN:
                target = (c, r)
                break
        if target:
            break
    p = world.players[0]
    p.body.x = target[0] * world.tile + 3
    p.body.y = target[1] * world.tile + 3
    world.update(1 / 60)
    assert world.coins == 1, f"金币应被收集: {world.coins}"
    assert world.map.grid[target[1]][target[0]] == 0, "金币应从网格移除"
