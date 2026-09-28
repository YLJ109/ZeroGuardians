"""箱子（搬运工建造 / 重锤投掷）。

实现要点：放置的箱子直接写入瓦片网格为实心（id=1），因此**可被站立**，
天然满足"搭台阶过 5 格缺口"的解谜（§8.5 约束 1）。回收时把该格还原为空。
"""
from __future__ import annotations

import pygame

from ..world.tilemap import SOLID


class Box:
    def __init__(self, px: float, py: float, size: int):
        self.x, self.y, self.size = px, py, size
        self.col = int(px // size)
        self.row = int(py // size)

    def body_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    def draw(self, surface, cam):
        x, y = self.x - cam.world_left, self.y - cam.world_top
        sp = getattr(self, "game", None) and getattr(self.game, "sprites", None)
        if sp:
            img = sp.crate(self.size)
            if img:
                surface.blit(img, (int(x), int(y)))
                return
        pygame.draw.rect(surface, (180, 130, 70), (x, y, self.size, self.size))
        pygame.draw.rect(surface, (220, 170, 100), (x + 4, y + 4, self.size - 8, self.size - 8))
