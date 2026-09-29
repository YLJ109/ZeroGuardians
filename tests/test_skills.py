"""技能回归测试：12 个技能必须能被真实按键触发、真的生效、且绝不崩。

真事故复盘
----------
v0.6 把「落脚标志」收敛到 Body 之后，skills.py 里残留了 3 处 ``player.grounded``
（正确写法是 ``player.body.grounded``）。因为测试对 skills 是**零覆盖**，
这个错误一路溜到了发布版：玩家在真实关卡里按 K（弓箭手·远跳）时直接

    AttributeError: 'Player' object has no attribute 'grounded'

崩溃。本文件用三道防线把这个洞焊死：

  1. 静态审计（治本）：skills.py 里出现的每个 ``player.<attr>`` 必须在真实
     Player 上存在 —— 属性改名后忘记同步技能层，这里立刻红。
  2. 注册表契约：HEROES 的 12 个技能必须互不重复、全部有实现、全部有中文名。
  3. 行为驱动：6 英雄 × 2 技能 ×（地面 / 空中）共 24 种组合真实按键跑一遍；
     并对远跳 / 二段跳 / 重踏做效果断言（不只是「不崩」）。
"""
import os
import re
from types import SimpleNamespace

import pygame

from zero_brother.config import Config
from zero_brother.heroes import skills as skills_mod
from zero_brother.heroes.registry import HEROES, HERO_ORDER, SKILL_NAMES
from zero_brother.input import InputManager
from zero_brother.levels.generate import generate_all, levels_dir
from zero_brother.world.level import load_level
from zero_brother.world.world import World

LEVELS = levels_dir()
KEY_A = pygame.K_j   # P1 技能一（默认键位）
KEY_B = pygame.K_k   # P1 技能二（默认键位）


def _key(code, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=code)


def _world(hero_id):
    cfg = Config.load()
    app = SimpleNamespace(config=cfg, input=InputManager(cfg))
    lvl = load_level(os.path.join(LEVELS, "level_1.json"))
    return World(app, lvl, [(0, hero_id)])


def _settle(world, frames=30):
    """让玩家落到地面站稳。"""
    for _ in range(frames):
        world.update(1 / 60)


def _put_in_air(player, dy=220):
    """把玩家抬到空中，并补满空中跳次数，确保「空中分支」真的会被执行。"""
    player.body.y -= dy
    player.body.vy = 0.0
    player.body.grounded = False
    player.air_jumps = player.max_air_jumps


def _zero_cooldowns(player):
    for k in player.cooldowns:
        player.cooldowns[k] = 0.0


def _press(world, key):
    world.input.poll([_key(key)])
    world.update(1 / 60)


# ---------------------------------------------------------------------------
# 1. 静态审计：治本
# ---------------------------------------------------------------------------
def test_skills_only_touch_attributes_that_exist():
    """skills.py 引用的每个 `player.<attr>` 都必须在真实 Player 上存在。

    这条是本事故的根治手段：属性改名后若忘了同步技能层，这里立刻失败，
    不会再等到玩家按键时才崩。
    """
    src = open(skills_mod.__file__, encoding="utf-8").read()
    attrs = set(re.findall(r"\bplayer\.([A-Za-z_][A-Za-z0-9_]*)", src))
    assert attrs, "未从 skills.py 解析出任何 player.<attr>（正则失效？）"

    world = _world("archer")
    _settle(world)                       # 跑一帧，让 player.game 等运行时属性就位
    p = world.players[0]

    missing = sorted(a for a in attrs if not hasattr(p, a))
    assert not missing, f"skills.py 访问了 Player 上不存在的属性: {missing}"


# ---------------------------------------------------------------------------
# 2. 注册表契约：12 = 6 × 2，不重不漏、有实现、有中文名
# ---------------------------------------------------------------------------
def test_twelve_skills_are_distinct_and_implemented():
    used = []
    for hid in HERO_ORDER:
        h = HEROES[hid]
        used += [h["skill_a"], h["skill_b"]]
    assert len(used) == 12, f"6 英雄 × 2 技能 应为 12 个槽位: {used}"
    assert len(set(used)) == 12, f"12 个技能不应重复: {sorted(used)}"

    impls = set(skills_mod.SKILLS)
    assert set(used) <= impls, f"有技能没有实现: {set(used) - impls}"
    assert impls == set(used), f"SKILLS 注册表与英雄分配不一致，多余: {impls - set(used)}"


def test_every_skill_has_chinese_display_name():
    """UI 要求英文枚举一律汉化：每个技能都必须有中文名。"""
    missing = [s for s in skills_mod.SKILLS if s not in SKILL_NAMES]
    assert not missing, f"技能缺少中文显示名: {missing}"


# ---------------------------------------------------------------------------
# 3. 行为驱动：全组合真实按键
# ---------------------------------------------------------------------------
def test_all_skills_run_from_ground_and_air():
    """6 英雄 × 2 技能 ×（地面 / 空中）：真实按键后不得抛异常。"""
    generate_all(LEVELS)
    for hid in HERO_ORDER:
        for key in (KEY_A, KEY_B):
            for airborne in (False, True):
                world = _world(hid)
                p = world.players[0]
                _settle(world)
                if airborne:
                    _put_in_air(p)
                _zero_cooldowns(p)
                world.input.poll([_key(key)])
                # 技能本帧 + 后续若干帧都要能安全结算（AoE / 冷却衰减 / 分发生效）
                for _ in range(12):
                    world.update(1 / 60)
                assert world.players[0].body is not None


def test_long_jump_fires_in_air_and_costs_air_jump():
    """远跳（弓箭手 SKILL_B）：空中按 K 必须生效 —— 这正是当初崩游戏的路径。"""
    generate_all(LEVELS)
    world = _world("archer")
    p = world.players[0]
    _settle(world)
    _put_in_air(p)
    _zero_cooldowns(p)

    before = p.air_jumps
    assert before >= 1, "弓箭手应至少有 1 次空中跳"
    _press(world, KEY_B)

    assert p.long_jump_timer > 0, "空中按 K 应触发远跳"
    assert p.air_jumps == before - 1, "远跳应消耗一次空中跳"


def test_long_jump_does_nothing_on_the_ground():
    """地面按 K 不应触发远跳（保留空中跳次数）。"""
    generate_all(LEVELS)
    world = _world("archer")
    p = world.players[0]
    _settle(world)
    _zero_cooldowns(p)
    assert p.body.grounded, "前置条件：玩家应已站在地面"

    _press(world, KEY_B)
    assert p.long_jump_timer == 0, "地面上不应触发远跳"


def test_double_jump_applies_tuning_velocity():
    """二段跳（忍者 SKILL_A）：空中按 J 应把 vy 设为调参值并消耗空中跳。"""
    generate_all(LEVELS)
    world = _world("ninja")
    p = world.players[0]
    _settle(world)
    _put_in_air(p)
    _zero_cooldowns(p)

    before = p.air_jumps
    _press(world, KEY_A)

    assert p.air_jumps == before - 1, "二段跳应消耗一次空中跳"
    assert p.body.vy == world.cfg.GAMEPLAY["double_jump_vy"], (
        f"二段跳应使用调参初速: {p.body.vy}"
    )


def test_slam_arms_only_in_air():
    """重踏（重锤 SKILL_A）：地面按无效，空中按置 slam_armed。"""
    generate_all(LEVELS)

    world = _world("hammer")
    p = world.players[0]
    _settle(world)
    _zero_cooldowns(p)
    _press(world, KEY_A)
    assert not p.slam_armed, "地面上不应触发重踏"

    world = _world("hammer")
    p = world.players[0]
    _settle(world)
    _put_in_air(p)
    _zero_cooldowns(p)
    _press(world, KEY_A)
    assert p.slam_armed, "空中按技能键应进入重踏待落地状态"


def test_shoot_still_spawns_bullets_after_fix():
    """回归护栏：修复属性名不能顺手弄坏正常的技能分发（射击）。"""
    generate_all(LEVELS)
    world = _world("archer")
    _settle(world)
    _zero_cooldowns(world.players[0])
    _press(world, KEY_A)
    assert len(world.bullets) >= 1, "射击仍应生成子弹"
