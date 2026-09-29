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
        # ---- 站立稳定性：脚底补探测 ----
        # 见 _settle_on_ground 的说明。缺了它，静止站立时 grounded 会逐帧抖动。
        if not self.grounded and self.vy >= 0:
            self._settle_on_ground(world)

    def _settle_on_ground(self, world) -> bool:
        """脚底正下方（≤0.5px 容差）若有可站立瓦片，则吸附上去并置 grounded。

        为什么必须有这一步
        ------------------
        下落碰撞用 ``int((y + h - 1) // t)`` 找"身体所占的最下一行"，这是为了避免
        把脚底当成包含端点。但落地解算 ``y = row*t - h`` 让脚底**恰好**压在瓦片
        顶边（bottom == row*t）：下一帧重力把脚底推进 0.5px，``(y+h-1)`` 又落回
        **上一行** → 检不到地面 → ``grounded`` 翻 False，要再掉 1px 才重新踩到。

        结果就是**静止站立时 grounded / vy / y 三者逐帧抖动**，副作用：
          - 只允许空中释放的技能（远跳 / 重踏）在地面上就能放；
          - ``draw()`` 里 ``not grounded → 跳跃帧``，站立角色在 idle/跳跃动画间闪帧；
          - 土狼时间与空中跳次数被反复重置，跳跃手感漂移。
        这里显式补一次地面探测，把静止状态钉死。
        """
        t = world.tile
        bottom = self.y + self.h
        row = int((bottom + 0.5) // t)          # 0.5 与单向平台判定同一容差口径
        if row * t > bottom + 0.5:
            return False
        c0 = int(self.x // t)
        c1 = int((self.x + self.w - 1) // t)
        for c in range(c0, c1 + 1):
            oneway = world.is_oneway_cell(c, row) and bottom <= row * t + 0.5
            if world.is_solid_cell(c, row) or oneway:
                self.y = row * t - self.h
                self.vy = 0.0
                self.grounded = True
                self.floor_cell = (c, row)
                return True
        return False
