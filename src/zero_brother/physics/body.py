"""物理刚体：AABB + 分轴瓦片碰撞 (GDD §9.4)。

每步位移 < 瓦片尺寸（由固定步长 + 限速保证），故单格解算即可，不穿透。

瓦片语义（见 world/tilemap.py）：
  - 全实心（地形 / 静态墙 / 弹簧）：四面阻挡。
  - 单向平台（bridge）：**只有从上往下落时**才算实心 —— 可以跳穿、
    可以从下方顶穿、横向不阻挡（经典 4399 平台跳跃手感）。
  - 梯子：不阻挡，攀爬逻辑在 Player 里（本类只管位移与碰撞）。

`floor_cell` 记录本次落地所站的格子，供上层判断"是不是踩到弹簧"。
"""
from __future__ import annotations

import pygame


class Body:
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vx = 0.0
        self.vy = 0.0
        self.grounded = False
        self.touch_left = self.touch_right = False
        self.floor_cell: tuple[int, int] | None = None

    # 矩形工具
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def move_and_collide(self, world, dt: float) -> None:
        t = world.tile
        # ---- X 轴（单向平台横向不阻挡）----
        self.x += self.vx * dt
        self.touch_left = self.touch_right = False
        if self.vx != 0:
            r0 = int(self.y // t)
            r1 = int((self.y + self.h - 1) // t)
            if self.vx > 0:
                col = int((self.x + self.w - 1) // t)
                for r in range(r0, r1 + 1):
                    if world.is_solid_cell(col, r):
                        self.x = col * t - self.w
                        self.vx = 0
                        self.touch_right = True
                        break
            else:
                col = int(self.x // t)
                for r in range(r0, r1 + 1):
                    if world.is_solid_cell(col, r):
                        self.x = (col + 1) * t
                        self.vx = 0
                        self.touch_left = True
                        break
        # ---- Y 轴 ----
        prev_bottom = self.y + self.h          # 位移前的脚底（判定单向平台）
        self.y += self.vy * dt
        self.grounded = False
        self.floor_cell = None
        if self.vy != 0:
            c0 = int(self.x // t)
            c1 = int((self.x + self.w - 1) // t)
            if self.vy > 0:
                row = int((self.y + self.h - 1) // t)
                for c in range(c0, c1 + 1):
                    oneway = world.is_oneway_cell(c, row) and prev_bottom <= row * t + 0.5
                    if world.is_solid_cell(c, row) or oneway:
                        self.y = row * t - self.h
                        self.vy = 0
                        self.grounded = True
                        self.floor_cell = (c, row)
                        break
            else:
                row = int(self.y // t)
                for c in range(c0, c1 + 1):
                    if world.is_solid_cell(c, row):
                        self.y = (row + 1) * t
                        self.vy = 0
                        break
