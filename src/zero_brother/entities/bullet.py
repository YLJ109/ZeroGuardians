"""子弹（弓箭手技能）。命中实心瓦片 / 箱子 / 怪物即消失；命中怪物击杀。"""
from __future__ import annotations

import pygame


class Bullet:
    def __init__(self, x: float, y: float, vx: float, size: tuple):
        self.x, self.y, self.w, self.h = x, y, size[0], size[1]
        self.vx = vx
        self.dead = False

    def update(self, dt, game) -> None:
        self.game = game
        self.x += self.vx * dt
        # 出界 / 撞墙
        if game.world.solid_pixel(self.x + (self.w if self.vx > 0 else 0), self.y + self.h / 2):
            self.dead = True
            return
        for b in game.boxes:
            if b.body_rect().collidepoint(self.x + (self.w if self.vx > 0 else 0), self.y + self.h / 2):
                self.dead = True
                return
        for m in game.monsters:
            if m.alive and m.body_rect().colliderect(pygame.Rect(self.x, self.y, self.w, self.h)):
                m.dead = True
                self.dead = True
                game.emit("bump")
                return
        for boss in game.bosses:
            if boss.alive and boss.rect().colliderect(pygame.Rect(self.x, self.y, self.w, self.h)):
                boss.take_damage(1)
                self.dead = True
                game.emit("boss_down" if boss.dead else "boss_hit")
                return

    def draw(self, surface, cam):
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        if sp:
            s = 30
            img = sp.projectile(s)
            if img:
                bx = self.x - cam.world_left + (self.w - s) / 2
                by = self.y - cam.world_top + self.h / 2 - s / 2
                surface.blit(img, (int(bx), int(by)))
                return
        pygame.draw.rect(surface, (255, 230, 120),
                        (self.x - cam.world_left, self.y - cam.world_top, self.w, self.h))
