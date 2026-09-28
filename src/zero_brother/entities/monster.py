"""怪物：地面巡逻怪（重力/悬崖转向）与飞行怪（水平往返 + 上下浮动）。

- kind  决定外观（Kenney 敌人素材：snail/slime/ladybug/worm/mouse/frog/bee/fly/saw）
- flyer 决定行为：True = 无重力、在出生点附近往返并轻微上下浮动。
被踩踏或技能击杀；侧碰玩家致死。两帧行走动画。
"""
from __future__ import annotations

import math

import pygame

from ..physics.body import Body


class Monster:
    def __init__(self, x: float, y: float, cfg, kind: str = "snail", flyer: bool = False):
        self.cfg = cfg
        self.kind = kind
        self.flyer = flyer
        self.body = Body(x, y, 40, 40)
        speed = cfg.GAMEPLAY["monster_speed"] * (1.3 if flyer else 1.0)
        self._speed = speed
        self.body.vx = speed
        self.home_x = x
        self.home_y = y
        self.range = 3.5 * cfg.BLOCK_SIZE
        self.anim_t = 0.0
        self.frame = 0
        self.alive = True
        self.dead = False

    def body_rect(self) -> pygame.Rect:
        return self.body.rect

    # ------------------------------------------------------------------
    def update(self, dt, game):
        if not self.alive:
            return
        self.game = game
        b = self.body
        self.anim_t += dt
        if self.anim_t >= 0.20:
            self.anim_t = 0.0
            self.frame ^= 1

        if self.flyer:
            # 水平往返（超出巡逻范围则折返）
            if b.x - self.home_x > self.range and b.vx > 0:
                b.vx = -abs(b.vx)
            elif self.home_x - b.x > self.range and b.vx < 0:
                b.vx = abs(b.vx)
            # 前方撞墙则折返
            ahead = b.x + (b.w + 2 if b.vx > 0 else -2)
            if game.world.solid_pixel(ahead, b.cy):
                b.vx = -b.vx
            b.vy = 0
            # 上下浮动
            b.y = self.home_y + math.sin((b.x * 0.02) + self.anim_t * 3) * 10
            b.move_and_collide(game.world, dt)
        else:
            b.vy = min(b.vy + self.cfg.GRAVITY * dt, 1500)
            # 悬崖检测：前方下方无地则转向
            t = game.world.tile
            ahead_x = b.x + (b.w if b.vx > 0 else -2)
            foot_r = int((b.y + b.h + 2) // t)
            ahead_c = int(ahead_x // t)
            if not game.world.is_solid_cell(ahead_c, foot_r):
                b.vx = -b.vx
            b.move_and_collide(game.world, dt)

        # 与玩家交互
        for p in game.players:
            if not p.alive:
                continue
            if self.rect_collides(p.body):
                # 踩踏：玩家下落且脚在怪物上半部
                if p.body.vy > 0 and p.body.y + p.body.h - b.y < 24:
                    self.alive = False
                    self.dead = True
                    p.body.vy = self.cfg.GAMEPLAY["monster_stomp_vy"]
                    game.emit("bump")
                else:
                    game.kill_player(p)

    def rect_collides(self, other) -> bool:
        return self.body.rect.colliderect(other.rect)

    def draw(self, surface, cam):
        x, y = self.body.x - cam.world_left, self.body.y - cam.world_top
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        if sp:
            s = self.body.w + 10
            img = sp.enemy(self.kind, self.frame, s, s)
            if img:
                surface.blit(img, (int(x + self.body.w / 2 - img.get_width() / 2),
                                   int(y + self.body.h - img.get_height())))
                return
        pygame.draw.rect(surface, (200, 80, 90), (x, y, self.body.w, self.body.h), border_radius=8)
        pygame.draw.circle(surface, (255, 255, 255), (x + 12, y + 14), 4)
        pygame.draw.circle(surface, (255, 255, 255), (x + 28, y + 14), 4)
