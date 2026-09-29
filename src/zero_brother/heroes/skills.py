"""技能实现 (GDD §8.3)。

每个技能是一个函数 (player, game, dt) -> None。玩家更新时按 skill_a / skill_b
调用。函数内部读取 player 的输入边沿 / 持续状态与冷却计时器，决定是否生效。
"""
from __future__ import annotations

import math

from ..world.tilemap import SOLID, GEM_GREEN, GEM_YELLOW


def _edge(player, action):
    return player.input_pressed(action)


def _fx_ring(game, x, y, r, life=0.4):
    game.fx.append({"type": "ring", "x": x, "y": y, "r": r, "life": life, "base_life": life})


def _fx_deny(game, x, y, life=0.5):
    game.fx.append({"type": "deny", "x": x, "y": y, "life": life})


# ---------------------------------------------------------------------------
# 攻击类
# ---------------------------------------------------------------------------
def shoot(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_A"):
        return
    if player.cooldowns["shoot"] > 0:
        return
    if len(game.bullets) >= gp["bullet_max"]:
        return
    player.cooldowns["shoot"] = gp["bullet_cooldown"]
    from ..entities.bullet import Bullet
    bx = player.body.cx + player.facing * (player.body.w // 2)
    by = player.body.cy - 4
    game.bullets.append(Bullet(bx, by, player.facing * gp["bullet_speed"], gp["bullet_size"]))
    game.emit("throw")


def dash(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_B"):
        return
    if player.cooldowns["dash"] > 0:
        return
    player.cooldowns["dash"] = gp["dash_cooldown"]
    player.dash_timer = gp["dash_time"]
    player.body.vx = player.facing * gp["dash_speed"]
    # 突进路径上的怪物被击杀
    for m in game.monsters:
        if abs(m.body.cx - player.body.cx) < 90 and abs(m.body.cy - player.body.cy) < 50:
            m.dead = True
    game.emit("vanish")


def shockwave(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_B"):
        return
    if player.cooldowns["shockwave"] > 0:
        return
    player.cooldowns["shockwave"] = gp["shockwave_cooldown"]
    r = gp["shockwave_radius"]
    for m in game.monsters:
        if math.hypot(m.body.cx - player.body.cx, m.body.cy - player.body.cy) < r:
            m.dead = True
    _fx_ring(game, player.body.cx, player.body.cy, r)
    game.emit("magic")


def slam(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_A"):
        return
    if player.body.grounded or player.cooldowns["slam"] > 0:
        return
    player.cooldowns["slam"] = gp["slam_cooldown"]
    player.body.vy = gp["slam_vy"]
    player.slam_armed = True
    game.emit("vanish")


# ---------------------------------------------------------------------------
# 建造类
# ---------------------------------------------------------------------------
def place_box(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_A"):
        return
    if player.cooldowns["place_box"] > 0:
        return
    if game.crates <= 0:
        _fx_deny(game, player.body.cx, player.body.cy)
        game.emit("deny")
        return
    t = game.world.tile
    fx_cell = int((player.body.cx + player.facing * t) // t)
    foot_row = int((player.body.y + player.body.h + 2) // t)
    target_row = foot_row - 1
    # 面前必须有地面，且目标格为空
    if not game.world.is_solid_cell(fx_cell, foot_row):
        return
    if game.world.is_solid_cell(fx_cell, target_row):
        return
    game.map.set_cell(fx_cell, target_row, SOLID)   # 写入网格 → 可被站立
    game.crates -= 1
    player.cooldowns["place_box"] = 0.5
    from ..entities.box import Box
    b = Box(fx_cell * t, target_row * t, t)
    b.game = game
    game.boxes.append(b)
    game.emit("place")


def recall_box(player, game, dt):
    if not _edge(player, "SKILL_B"):
        return
    if player.cooldowns["recall_box"] > 0:
        return
    t = game.world.tile
    pc, pr = int(player.body.cx // t), int((player.body.y + player.body.h + 2) // t)
    for b in list(game.boxes):
        if (b.col, b.row) == (pc, pr):
            game.map.set_cell(pc, pr, 0)   # 还原网格
            game.boxes.remove(b)
            game.crates += 1
            player.cooldowns["recall_box"] = 0.3
            player.body.vy = min(player.body.vy, 0)  # 失去支撑立即下落
            game.emit("vanish")
            break


def lift_throw(player, game, dt):
    t = game.world.tile
    if not _edge(player, "SKILL_B"):
        return
    pc, pr = int(player.body.cx // t), int((player.body.y + player.body.h + 2) // t)
    if player.carry_box is None:
        for b in list(game.boxes):
            if abs(b.cx - player.body.cx) < t and abs(b.cy - player.body.cy) < t:
                game.map.set_cell(b.col, b.row, 0)
                game.boxes.remove(b)
                player.carry_box = (b.col, b.row)
                break
    else:
        col, row = player.carry_box
        player.carry_box = None
        fx_cell = int((player.body.cx + player.facing * t) // t)
        target_row = row  # 仍落在原高度附近（简化）
        if game.world.is_solid_cell(fx_cell, target_row + 1) and not game.world.is_solid_cell(fx_cell, target_row):
            game.map.set_cell(fx_cell, target_row, SOLID)
            from ..entities.box import Box
            b = Box(fx_cell * t, target_row * t, t)
            b.game = game
            game.boxes.append(b)
            game.emit("place")


# ---------------------------------------------------------------------------
# 机动类
# ---------------------------------------------------------------------------
def double_jump(player, game, dt):
    if not _edge(player, "SKILL_A"):
        return
    if player.body.grounded or player.air_jumps <= 0:
        return
    player.air_jumps -= 1
    player.body.vy = game.cfg.GAMEPLAY["double_jump_vy"]
    game.emit("jump_hi")


def long_jump(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not _edge(player, "SKILL_B"):
        return
    if player.body.grounded or player.air_jumps <= 0:
        return
    player.air_jumps -= 1
    player.long_jump_timer = gp["long_jump_time"]
    game.emit("jump_hi")


def hover(player, game, dt):
    gp = game.cfg.GAMEPLAY
    if not player.input_held("SKILL_A"):
        return
    if player.hover_time <= 0:
        return
    if player.body.vy > gp["hover_max_fall"]:
        player.body.vy = gp["hover_max_fall"]
    player.hover_time -= dt


def portal_place(player, game, dt):
    if not _edge(player, "SKILL_A"):
        return
    if player.cooldowns["portal"] > 0:
        return
    t = game.world.tile
    # 面前必须是实心墙
    fx = player.body.cx + player.facing * (player.body.w // 2 + 4)
    fy = player.body.cy
    if not game.world.solid_pixel(fx, fy):
        return
    wx = player.body.cx - player.facing * t * 0.5
    wy = player.body.cy
    if len(game.portals) < 2:
        from ..entities.portal import Portal
        pr = Portal(wx, wy, len(game.portals) == 0)
        pr.game = game
        game.portals.append(pr)
    else:
        # 第 3 次起覆盖蓝门（循环）
        game.portals[0].x, game.portals[0].y = wx, wy
    player.cooldowns["portal"] = game.cfg.GAMEPLAY["portal_cooldown"]
    game.emit("magic")


def portal_swap(player, game, dt):
    if not _edge(player, "SKILL_B"):
        return
    if len(game.portals) < 2:
        return
    game.portals[0].x, game.portals[1].x = game.portals[1].x, game.portals[0].x
    game.portals[0].y, game.portals[1].y = game.portals[1].y, game.portals[0].y
    game.emit("magic")


SKILLS = {
    "shoot": shoot, "dash": dash, "shockwave": shockwave, "slam": slam,
    "place_box": place_box, "recall_box": recall_box, "lift_throw": lift_throw,
    "double_jump": double_jump, "long_jump": long_jump, "hover": hover,
    "portal_place": portal_place, "portal_swap": portal_swap,
}
