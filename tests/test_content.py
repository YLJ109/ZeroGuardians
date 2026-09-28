# -*- coding: utf-8 -*-
"""内容层自检：关卡设计约束 / 音频素材完整性 / 字体合规 / 世界事件。

这些用例守护的是「用真实素材把游戏做扎实」这条线：
  - 关卡不是随手撒的：缺口宽度、可达性、净空区、要素不重叠都要可验证。
  - 音效名必须都能解析到真实文件（否则等于没接线）。
  - 默认字体必须是已登记 OFL 的随包字体（Q6 合规）。
  - 逻辑层通过事件队列与表现层解耦，事件必须真的产生。
"""
from __future__ import annotations

import os
import random

import pygame

from zero_brother.levels.generate import (
    BOSS_LEVELS, LEVEL_NAMES, ROWS, COLS, GROUND, SPAWN_ROW, DOOR_COL,
    generate_level, generate_all,
)
from zero_brother.world.level import Level, validate_level, level_facts, TIER_NAMES
from zero_brother.config.settings import Config
from zero_brother.resources.manifest import license_of
from zero_brother.systems.audio import SOUND_MAP

CFG = Config()


def _all_levels():
    return [generate_level(i, random.Random(1000 + i)) for i in range(1, 16)]


def _as_level(d) -> Level:
    return Level(id=d["id"], name=d["name"], theme=d["theme"],
                 rows=d["rows"], boss=d["boss"], deco=d.get("deco"))


# ---------------------------------------------------------------------------
# 关卡结构
# ---------------------------------------------------------------------------
def test_all_15_levels_pass_validator():
    for d in _all_levels():
        lv = Level(id=d["id"], name=d["name"], theme=d["theme"], rows=d["rows"], boss=d["boss"])
        errs = validate_level(lv, CFG)
        assert not errs, f"第 {d['id']} 关校验失败: {errs}"


def test_grid_shape_and_single_door():
    for d in _all_levels():
        rows = d["rows"]
        assert len(rows) == ROWS, f"第 {d['id']} 关行数 {len(rows)}"
        assert all(len(r) == COLS for r in rows), f"第 {d['id']} 关列数不齐"
        assert "".join(rows).count("D") == 1, f"第 {d['id']} 关终点门不唯一"


def test_thematic_unique_names():
    names = [generate_level(i, random.Random(1000 + i))["name"] for i in range(1, 16)]
    assert len(set(names)) == 15, "关卡名重复"
    for i in range(1, 16):
        if i in BOSS_LEVELS:
            assert names[i - 1] == BOSS_LEVELS[i]["name"]
        else:
            assert names[i - 1] == LEVEL_NAMES[i]


def test_gaps_are_jumpable():
    """单跳水平距离 ≈197px（≈3.9 格），因此任何缺口都不得超过 3 格。"""
    for d in _all_levels():
        if d["id"] in BOSS_LEVELS:
            continue
        ground = d["rows"][GROUND]
        run = 0
        for ch in ground + "#":
            if ch == ".":
                run += 1
                assert run <= 3, f"第 {d['id']} 关出现 {run} 格宽缺口（不可跳）"
            else:
                run = 0


def test_doors_have_clear_landing_zone():
    """门前 3 格必须净空，避免玩家落在刺上/被怪堵门。"""
    for d in _all_levels():
        row = d["rows"][SPAWN_ROW]
        for c in range(DOOR_COL - 3, DOOR_COL):
            assert row[c] == ".", f"第 {d['id']} 关门前第 {c} 列被 '{row[c]}' 占据"


def test_spawn_lane_is_clear():
    """出生点左侧必须净空，避免开局即死。"""
    for d in _all_levels():
        row = d["rows"][SPAWN_ROW]
        for c in range(1, 5):
            assert row[c] in "1234", f"第 {d['id']} 关出生点缺失"
        assert row[0] == ".", "出生点左侧应留空"


def test_no_element_stacking():
    """同一格不能同时是地刺 / 怪物 / 箱子 / 宝石（避免不公平叠加）。"""
    for d in _all_levels():
        grid = d["rows"]
        for r in range(ROWS):
            for c in range(COLS):
                ch = grid[r][c]
                if ch in "^MFCgy":
                    # 脚下不能是地刺
                    if r + 1 < ROWS and grid[r + 1][c] == "^":
                        raise AssertionError(f"第 {d['id']} 关 ({c},{r}) '{ch}' 悬在地刺上方")


def test_walkers_stand_on_solid_ground():
    for d in _all_levels():
        grid = d["rows"]
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == "M":
                    assert r + 1 < ROWS and grid[r + 1][c] == "#", \
                        f"第 {d['id']} 关地面怪 ({c},{r}) 脚下无地面"


def test_early_levels_teach_without_enemies():
    """L1-L3 作为教学关：不设任何敌人（introduce 阶段）。"""
    for i in (1, 2, 3):
        flat = "".join(generate_level(i, random.Random(1000 + i))["rows"])
        assert flat.count("M") == 0 and flat.count("F") == 0, f"第 {i} 关不应有敌人"


def test_difficulty_ramps_up():
    """发展关的敌人数量随进度上升（Boss 关不含小怪，不参与比较）。"""
    def enemy_count(i):
        flat = "".join(generate_level(i, random.Random(1000 + i))["rows"])
        return flat.count("M") + flat.count("F")

    counts = [enemy_count(i) for i in (4, 6, 8, 9, 11, 14)]
    assert counts == sorted(counts), f"难度曲线非单调不降: {counts}"
    assert counts[-1] > counts[0], f"后期关卡敌人未增多: {counts}"


def test_every_level_has_gems_and_is_winnable_shape():
    for d in _all_levels():
        flat = "".join(d["rows"])
        assert flat.count("g") + flat.count("y") >= 1, f"第 {d['id']} 关没有宝石"
        assert flat.count("D") == 1


def test_boss_levels_have_arena_and_phases():
    for i, spec in BOSS_LEVELS.items():
        d = generate_level(i, random.Random(1000 + i))
        assert d["boss"] and d["boss"]["phases"] == spec["phases"]
        assert d["name"] == spec["name"]
        # 左右高台（走位空间）
        assert "".join(d["rows"][14][5:9]) == "####"


def test_boss_is_hittable_from_standing_shot():
    """Boss 悬浮时不能跑出「站在地面的射击线」，否则关卡无法通关。"""
    import math
    from zero_brother.entities.boss import Boss
    from zero_brother.levels.generate import BOSS_POS

    tile = CFG.BLOCK_SIZE
    body_y = SPAWN_ROW * tile + (tile - CFG.PLAYER_HITBOX[1])
    shot_y = body_y + CFG.PLAYER_HITBOX[1] / 2 - 4          # 弓箭手子弹高度
    boss = Boss(BOSS_POS["x"] * tile, BOSS_POS["y"] * tile, CFG,
                BOSS_LEVELS[15]["phases"], theme="purple")
    for _ in range(600):
        boss.t += 1 / 60
        boss.y = boss.home_y + math.sin(boss.t * (1.2 + 0.35 * boss.phase)) * boss.bob_amp
        r = boss.rect()
        assert r.top <= shot_y <= r.bottom, \
            f"Boss 脱离射击线 top={r.top} shot={shot_y} bottom={r.bottom}"


def test_boss_minion_pool_matches_theme():
    from zero_brother.world.world import THEME_ENEMY, FLYERS
    for i in BOSS_LEVELS:
        d = generate_level(i, random.Random(1000 + i))
        walkers = [k for k in THEME_ENEMY[d["theme"]] if k not in FLYERS]
        assert walkers, f"第 {i} 关主题 {d['theme']} 没有可用地面小怪"


def test_generation_is_deterministic():
    a = generate_level(7, random.Random(1007))["rows"]
    b = generate_level(7, random.Random(1007))["rows"]
    assert a == b, "同种子生成结果不一致"


def test_generate_all_writes_15_files(tmp_path):
    generate_all(str(tmp_path))
    files = sorted(os.listdir(str(tmp_path)))
    assert len(files) == 15, files
    assert "level_15.json" in files


# ---------------------------------------------------------------------------
# level_facts：HUD 高度计 / 选关预览共用的结构统计契约
# ---------------------------------------------------------------------------
def test_level_facts_counts_match_bruteforce():
    """counts 必须等于逐字符统计，否则 HUD 计数/图例会骗人。"""
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        flat = "".join(d["rows"])
        c = facts["counts"]
        assert c["ladder"] == flat.count("L")
        assert c["spring"] == flat.count("S")
        assert c["bridge"] == flat.count("=")
        assert c["wall"] == flat.count("W")
        assert c["coin"] == flat.count("$")
        assert c["gem"] == flat.count("g") + flat.count("y")
        assert c["spike"] == flat.count("^")
        assert c["crate"] == flat.count("C")
        assert c["enemy"] == flat.count("M") + flat.count("F")


def test_level_facts_tiers_are_bottom_up_starting_at_ground():
    """tiers[0] 必须是地面，随后逐层升高（row 递减）—— 消费方靠这个顺序画高度计。"""
    for d in _all_levels():
        lv = _as_level(d)
        facts = level_facts(lv)
        tiers = facts["tiers"]
        assert tiers, f"第 {d['id']} 关没有解析出任何层"
        assert tiers[0]["stand"] == facts["ground_row"] == GROUND, f"第 {d['id']} 关首层不是地面"
        stands = [t["stand"] for t in tiers]
        assert stands == sorted(stands, reverse=True), f"第 {d['id']} 关层序不是自下而上: {stands}"
        assert all(0 <= s < ROWS for s in stands), f"第 {d['id']} 关层行越界: {stands}"


def test_level_facts_tier_items_cover_every_item():
    """每件道具都必须归属到某一层（含缺口上方的悬空跳跃弧），一件都不能漏。"""
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        total = facts["counts"]["gem"] + facts["counts"]["coin"]
        got = sum(t["items"] for t in facts["tiers"])
        assert got == total, f"第 {d['id']} 关层道具合计 {got} != 实际 {total}"


def test_level_facts_tier_item_row_sits_above_the_platform():
    """平台行 R 上的道具约定摆在 R-1，层记录必须与之一致。"""
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        for t in facts["tiers"]:
            assert t["item_row"] == max(0, t["stand"] - 1), f"第 {d['id']} 关道具行错位"


def test_level_facts_ground_tier_items_match_ground_row():
    """地面的道具就摆在 row GROUND-1 上，两者必须相等（不允许漏挂到别层）。"""
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        ground_tier = facts["tiers"][0]
        assert ground_tier["stand"] == GROUND
        row = d["rows"][GROUND - 1]
        n = row.count("g") + row.count("y") + row.count("$")
        assert ground_tier["items"] == n, \
            f"第 {d['id']} 关地面道具 {ground_tier['items']} != 实测 {n}"


def test_every_level_really_is_multi_tier():
    """用户要求「上面也要放道具」：每关至少 3 层，且高难关卡达到 5 层以上。"""
    layer_counts = []
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        assert facts["layers"] >= 3, f"第 {d['id']} 关层数 {facts['layers']} 太少"
        assert facts["has_vertical"], f"第 {d['id']} 关没有立体结构"
        assert facts["layers"] <= len(TIER_NAMES), \
            f"第 {d['id']} 关层数 {facts['layers']} 超出层名表，HUD 会退化成数字"
        layer_counts.append(facts["layers"])
    assert max(layer_counts) >= 5, f"没有任何关卡达到 5 层: {layer_counts}"
    assert sum(1 for n in layer_counts if n >= 5) >= 5, \
        f"达到 5 层的关卡太少: {layer_counts}"


def test_upper_tiers_actually_carry_items_in_facts():
    """高度计要显示「上层道具」，所以至少要有几关的高层真的挂了道具。"""
    rich = 0
    for d in _all_levels():
        facts = level_facts(_as_level(d))
        upper = [t for t in facts["tiers"] if t["stand"] < facts["ground_row"]]
        if len(upper) >= 2 and sum(t["items"] for t in upper) >= 3:
            rich += 1
    assert rich >= 10, f"只有 {rich}/15 关的高层有足量道具"


# ---------------------------------------------------------------------------
# 资源 / 音频 / 字体
# ---------------------------------------------------------------------------
def _assets_root():
    from zero_brother.resources.manager import ResourceManager
    return ResourceManager(CFG).assets_root


def test_every_sound_maps_to_existing_file():
    root = _assets_root()
    missing = []
    for name, (rel, _vol) in SOUND_MAP.items():
        if not os.path.exists(os.path.join(root, *rel.split("/"))):
            missing.append(f"{name} -> {rel}")
    assert not missing, "音效缺失: " + "; ".join(missing)


def test_audio_manager_survives_headless():
    """无音频设备时必须静默降级，绝不抛异常。"""
    from zero_brother.systems.audio import AudioManager
    from zero_brother.resources.manager import ResourceManager
    a = AudioManager(ResourceManager(CFG), enabled=True)
    a.play("jump")           # 不崩即可
    a.play("__nonexistent__")  # 未知音效只告警
    assert a.toggle_mute() is True
    a.play("jump")
    assert a.toggle_mute() is False


def test_default_font_is_bundled_and_ofl():
    from zero_brother.resources.manager import DEFAULT_FONT
    root = _assets_root()
    path = os.path.join(root, *DEFAULT_FONT.split("/"))
    assert os.path.exists(path), f"随包字体缺失: {DEFAULT_FONT}"
    lic = license_of(DEFAULT_FONT)
    assert lic.startswith("SIL"), f"字体许可未登记为 OFL: {lic}"


def test_bundled_font_renders_chinese_uniformly():
    """中文字形宽度必须一致（等宽推进），这是排版不拥挤的前提。"""
    from zero_brother.resources.manager import DEFAULT_FONT
    root = _assets_root()
    path = os.path.join(root, *DEFAULT_FONT.split("/"))
    f = pygame.font.Font(path, 32)
    widths = {f.size(ch)[0] for ch in "零零守护者选择英雄"}
    assert len(widths) == 1, f"中文字宽不一致: {widths}"


def test_font_license_file_shipped():
    root = _assets_root()
    lic = os.path.join(root, "vendor", "noto_sans_sc", "LICENSE.txt")
    assert os.path.exists(lic), "缺少 OFL 许可全文"
    text = open(lic, encoding="utf-8").read()
    assert "SIL OPEN FONT LICENSE" in text
