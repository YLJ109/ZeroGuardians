"""传送门对（门师技能）。成对存在：踏入一端传送到另一端，带冷却防乒乓。"""
from __future__ import annotations

import pygame

from ..config.settings import DEFAULTS


class Portal:
    def __init__(self, x: float, y: float, is_blue: bool):
        self.x, self.y = x, y
        self.is_blue = is_blue
        self.size = 40
        self.cooldown = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.size / 2), int(self.y - self.size / 2), self.size, self.size)

    def update(self, dt, game):
        self.game = game
        self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self, surface, cam):
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        if sp:
            s = int(self.size * 1.8)
            img = sp.portal(self.is_blue, s)
            if img:
                x = self.x - cam.world_left
                y = self.y - cam.world_top
                surface.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
                return
        c = (90, 160, 255) if self.is_blue else (255, 160, 70)
        x, y = self.x - cam.world_left, self.y - cam.world_top
        pygame.draw.circle(surface, c, (x, y), self.size / 2)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), self.size / 4)
