"""玩家实体：基础移动（全英雄一致）+ 跳跃手感调校 + 技能分发。

跳跃：土狼时间 + 跳跃缓冲 + 可变跳高（§9.2）。技能仅在英雄的 skill_a / skill_b
上分发，逻辑层只读 Action（§7.2）。

竖向交通（v0.6 新增，支撑多层立体关卡）：
  - 梯子：身体与梯子格重叠时可攀爬。按住「上」(=JUMP 键) 上爬、「下」(=CROUCH)
    下爬；空中按住上即抓梯。攀爬到顶会被钳制在梯顶，此时左右移动即可**站上平台**
    （平台在梯子所在列留孔，梯子与平台同高 → 脚底恰好在平台顶面上，横向不碰撞）。
  - 弹簧：落到弹簧格上立刻获得一次高弹跳（远高于普通跳），用来够到上层金币台。
  - 坠落：掉出世界底部由 World 判定重生（见 world._check_pit）。
"""
from __future__ import annotations

import pygame

from ..input.actions import Action
from ..physics.body import Body
from ..heroes.registry import hero
from ..heroes.skills import SKILLS


class Player:
    def __init__(self, slot: int, hero_id: str, x: float, y: float, cfg):
        self.slot = slot
        self.hero_id = hero_id
        self.hero = hero(hero_id)
        self.cfg = cfg
        self.color = self.hero["color"]
        self.body = Body(x, y, cfg.PLAYER_HITBOX[0], cfg.PLAYER_HITBOX[1])
        self.facing = 1
        self.alive = True
        self.spawn = (x, y)

        gp = cfg.GAMEPLAY
        self.cooldowns = {k: 0.0 for k in ("shoot", "dash", "shockwave", "slam",
                                          "place_box", "recall_box", "portal")}
        self.dash_timer = 0.0
        self.long_jump_timer = 0.0
        self.hover_time = gp["hover_time"]
        self.max_air_jumps = 1 if hero_id in ("ninja", "archer") else 0
        self.air_jumps = 0
        self.slam_armed = False
        self.carry_box = None
        self.jump_buffer = 0.0
        self.coyote = 0.0
        self.prev_jump_held = False
        self.climbing = False
        self._anim_t = 0.0
        self._anim_frame = 0

    # ---- 输入辅助（技能用字符串名，这里映射到 Action 枚举）----
    def input_held(self, name: str) -> bool:
        return self.game.input.held(self.slot, Action[name])

    def input_pressed(self, name: str) -> bool:
        return self.game.input.pressed(self.slot, Action[name])

    # ------------------------------------------------------------------
    # 梯子工具
    # ------------------------------------------------------------------
    def ladder_overlap(self, world) -> bool:
        """身体是否与梯子格重叠（脚下那一格也算，便于站在梯底时抓梯）。"""
        b = self.body
        t = world.tile
        c0, c1 = int(b.x // t), int((b.x + b.w - 1) // t)
        r0, r1 = int(b.y // t), int((b.y + b.h - 1) // t)
        for c in range(c0, c1 + 1):
            for r in range(r0, r1 + 1):
                if world.is_ladder_cell(c, r):
                    return True
        return world.is_ladder_cell(int(b.cx // t), int((b.y + b.h + 2) // t))

    def ladder_run(self, world):
        """返回玩家所在梯子列的连续区间 (top_row, bottom_row)；不在梯子上返回 None。"""
        b = self.body
        t = world.tile
        col = int(b.cx // t)
        row = int((b.y + b.h - 1) // t)
        while row < world.rows and not world.is_ladder_cell(col, row):
            row += 1
        if row >= world.rows or not world.is_ladder_cell(col, row):
            return None
        top = row
        while world.is_ladder_cell(col, top - 1):
            top -= 1
        bot = row
        while world.is_ladder_cell(col, bot + 1):
            bot += 1
        return top, bot

    # ------------------------------------------------------------------
    def update(self, dt: float, game) -> None:
        self.game = game
        cfg = self.cfg
        gp = cfg.GAMEPLAY
        b = self.body
        world = game.world

        # 水平输入
        left = self.input_held("MOVE_LEFT")
        right = self.input_held("MOVE_RIGHT")
        target = (right - left) * cfg.MOVE_SPEED

        jump_held = self.input_held("JUMP")
        crouch_held = self.input_held("CROUCH")

        # ---- 攀爬状态机：重叠梯子 + 按上/下进入；离开梯子格自动脱离 ----
        on_ladder = self.ladder_overlap(world)
        was_climbing = self.climbing
        if self.climbing:
            self.climbing = on_ladder
        else:
            # 站在梯底按「下」= 抓梯；空中按「上」= 抓梯（地面上按上仍优先起跳）
            grab = crouch_held or (jump_held and not b.grounded)
            self.climbing = bool(on_ladder and grab and self._ladder_has_height(world))
        if self.climbing and not was_climbing:
            game.emit("ladder")

        if self.climbing:
            b.vx = target * gp["climb_speed_mult"]
            b.vy = (-gp["climb_speed"] if jump_held else
                    (gp["climb_speed"] if crouch_held else 0.0))
            if target != 0:
                self.facing = 1 if target > 0 else -1
            if abs(b.vy) > 1:
                self._anim_t += dt
                if self._anim_t >= 0.14:
                    self._anim_t = 0.0
                    self._anim_frame = (self._anim_frame + 1) % 2
            else:
                self._anim_frame = 0
            self.jump_buffer = 0.0
            b.move_and_collide(world, dt)
            self._clamp_ladder(world)
            self._post_motion(game, dt)
            return

        if self.dash_timer <= 0:
            b.vx = target
            if target != 0:
                self.facing = 1 if target > 0 else -1
        else:
            self.dash_timer -= dt

        # 长跳：限时水平加速 + 重力削弱
        if self.long_jump_timer > 0:
            self.long_jump_timer -= dt
            b.vx = self.facing * cfg.MOVE_SPEED * gp["long_jump_mult"]

        # 重力
        gravity = cfg.GRAVITY * (gp["long_jump_grav"] if self.long_jump_timer > 0 else 1.0)
        b.vy += gravity * dt
        b.vy = min(b.vy, 1500)

        # 跳跃：缓冲 + 土狼 + 可变跳高
        if self.input_pressed("JUMP"):
            self.jump_buffer = cfg.JUMP_BUFFER
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        if b.grounded:
            self.coyote = cfg.COYOTE_TIME
            self.air_jumps = self.max_air_jumps
            self.hover_time = gp["hover_time"]
        else:
            self.coyote = max(0.0, self.coyote - dt)
        if self.jump_buffer > 0 and self.coyote > 0:
            b.vy = cfg.JUMP_VELOCITY
            self.jump_buffer = 0.0
            self.coyote = 0.0
            if hasattr(game, "emit"):
                game.emit("jump")
        if self.prev_jump_held and not jump_held and b.vy < 0:
            b.vy *= cfg.JUMP_CUT
        self.prev_jump_held = jump_held

        # 行走动画状态
        if b.grounded and abs(b.vx) > 5:
            self._anim_t += dt
            if self._anim_t >= 0.12:
                self._anim_t = 0.0
                self._anim_frame = (self._anim_frame + 1) % 4
        else:
            self._anim_t = 0.0
            self._anim_frame = 0

        # 碰撞结算
        b.move_and_collide(world, dt)

        # 弹簧：落到弹簧上 → 高弹跳（可重复触发，像蹦床；左右走开即离开）
        if b.grounded and b.floor_cell is not None and world.is_spring_cell(*b.floor_cell):
            b.vy = gp["spring_vy"]
            b.grounded = False
            self.air_jumps = self.max_air_jumps
            self.hover_time = gp["hover_time"]
            self.jump_buffer = 0.0
            game.emit("spring")

        self._post_motion(game, dt)

    # ------------------------------------------------------------------
    def _ladder_has_height(self, world, need: int = 2) -> bool:
        """梯子必须在头顶方向还有格子，避免"站在单格梯子上被吸住"。"""
        b = self.body
        t = world.tile
        col = int(b.cx // t)
        head = int(b.y // t)
        run = self.ladder_run(world)
        if run is None:
            return False
        top, bot = run
        return (bot - top) >= need and (top < head or bot > head)

    def _clamp_ladder(self, world) -> None:
        """把玩家钳制在梯子区间内：脚底不低于梯顶，不高于梯底。"""
        run = self.ladder_run(world)
        if run is None:
            return
        top, bot = run
        t = world.tile
        b = self.body
        feet = b.y + b.h
        if feet < top * t:
            b.y = top * t - b.h
            if b.vy < 0:
                b.vy = 0.0
        elif feet > (bot + 1) * t:
            b.y = (bot + 1) * t - b.h
            if b.vy > 0:
                b.vy = 0.0

    def _post_motion(self, game, dt) -> None:
        """落地后的通用结算（重踏 AoE、冷却衰减、技能分发）。"""
        b = self.body
        gp = self.cfg.GAMEPLAY

        # 重踏落地：AoE
        if self.slam_armed and b.grounded:
            self.slam_armed = False
            game.fx.append({"type": "ring", "x": b.cx, "y": b.cy,
                            "r": gp["slam_radius"], "life": 0.4, "base_life": 0.4})
            game.emit("bump")
            for m in game.monsters:
                if abs(m.body.cx - b.cx) < gp["slam_radius"] and abs(m.body.cy - b.cy) < gp["slam_radius"]:
                    m.dead = True
            for bx in list(game.boxes):
                if abs(bx.body.cx - b.cx) < gp["slam_radius"] and abs(bx.body.cy - b.cy) < gp["slam_radius"]:
                    game.boxes.remove(bx)

        # 冷却 / 计时衰减
        for k in self.cooldowns:
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)

        # 技能分发
        a_name = self.hero["skill_a"]
        if a_name in SKILLS:
            SKILLS[a_name](self, game, dt)
        b_name = self.hero["skill_b"]
        if b_name in SKILLS:
            SKILLS[b_name](self, game, dt)

    # ------------------------------------------------------------------
    def respawn(self) -> None:
        self.body.x, self.body.y = self.spawn
        self.body.vx = self.body.vy = 0
        self.climbing = False
        self.carry_box = None
        self.alive = True

    def draw(self, surface: pygame.Surface, cam) -> None:
        b = self.body
        x, y = b.x - cam.world_left, b.y - cam.world_top
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        if sp:
            H = 64
            if self.climbing:
                img = sp.char_climb(self.hero_id, self._anim_frame, self.facing, H)
            elif not b.grounded:
                img = sp.char(self.hero_id, "jump", self.facing, H)
            elif abs(b.vx) > 5:
                img = sp.char_walk(self.hero_id, self._anim_frame, self.facing, H)
            else:
                img = sp.char(self.hero_id, "idle", self.facing, H)
            if img:
                iw, ih = img.get_size()
                bx = x + (b.w - iw) / 2
                by = y + (b.h - ih)
                surface.blit(img, (int(bx), int(by)))
                gem = sp.hero_gem(self.hero_id, 14)
                if gem:
                    surface.blit(gem, (int(x + b.w / 2 - 7), int(by - 16)))
                return
        # 回退图元（无精灵，如 headless 测试）
        pygame.draw.rect(surface, self.color, (x, y, b.w, b.h), border_radius=6)
        ex = x + (b.w * 0.7 if self.facing > 0 else b.w * 0.3)
        pygame.draw.circle(surface, (255, 255, 255), (ex, y + b.h * 0.35), 5)
        pygame.draw.circle(surface, (20, 20, 20), (ex, y + b.h * 0.35), 2)
