"""瓦片世界 (GDD §10.1 / §9.4 分轴解算)。

瓦片 ID：
  0  空
  1  实心地形（16 掩码自动拼接，按主题换皮）
  2  墙 / 棱柱（静态实心障碍，**无重力**，砖石贴图）
  3  地刺
  4  梯子（可攀爬，不阻挡）
  5  绿宝石   6 黄宝石   12 金币
  7  终点门
  8  弹簧（可站立，落地反弹）
  9  传送门A(蓝)   10 传送门B(橙)
  11 单向平台（从上方可站、可从下方跳穿，横向不阻挡）

分层与实体：
  - `rows`   ：碰撞 / 交互层（玩家、怪物、箱子、道具都按它结算）。
  - `deco`   ：纯装饰层（草丛/灌木/岩石/路牌/火把…），只画不碰，
               同一格可以与碰撞层重叠，用来把界面和关卡做"厚"。
玩家/怪物/箱子出生点不进网格，加载时提取为实体。

关于重力（设计约束）：本作角色（玩家、地面怪）受重力；瓦片层（地形、墙、
梯子、弹簧、单向平台）是**静态**的，永远不下落——墙尤其如此，它是关卡的
"骨架"，用来做障碍、掩体和高台支柱。
"""
from __future__ import annotations

import pygame

# ---- 瓦片 ID ----
SOLID = 1
WALL = 2
SPIKE = 3
LADDER = 4
GEM_GREEN = 5
GEM_YELLOW = 6
DOOR = 7
SPRING = 8
PORTAL_A = 9
PORTAL_B = 10
ONEWAY = 11
COIN = 12

# 四面都挡的实心瓦片（含静态墙体与弹簧）
SOLID_TILES = frozenset({SOLID, WALL, SPRING})
# 可以站上去的顶面（单向平台只有顶面可用）
STANDABLE_TILES = frozenset({SOLID, WALL, SPRING, ONEWAY})
# 可收集物
ITEM_TILES = frozenset({GEM_GREEN, GEM_YELLOW, COIN})
# 威胁（关卡校验/净空判定用）
HAZARD_CHARS = "^"

_CHAR = {
    ".": 0, "#": SOLID, "W": WALL, "^": SPIKE, "L": LADDER,
    "g": GEM_GREEN, "y": GEM_YELLOW, "D": DOOR, "S": SPRING,
    "a": PORTAL_A, "b": PORTAL_B, "=": ONEWAY, "$": COIN,
}
_ID_CHAR = {v: k for k, v in _CHAR.items()}

# 出生点字符（先于瓦片映射判断）
SPAWN_CHARS = "1234MCF"


class TileMap:
    def __init__(self, grid: list[list[int]], tile: int, deco: list[list[str]] | None = None):
        self.grid = grid
        self.tile = tile
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0
        self.deco = deco or []
        self.sprites = None
        self.theme = "grass"

    # ---- 工厂：从字符串行解析 ----
    @classmethod
    def from_rows(cls, rows: list[str], tile: int, spawns: dict,
                  deco: list[list[str]] | None = None) -> "TileMap":
        grid = []
        for r, line in enumerate(rows):
            row = []
            for c, ch in enumerate(line):
                if ch in SPAWN_CHARS:  # 出生点：清空为空格，记录坐标（必须先于瓦片映射判断）
                    row.append(0)
                    if ch.isdigit():
                        spawns.setdefault("players", []).append((int(ch) - 1, c, r))
                    elif ch == "M":
                        spawns.setdefault("monsters", []).append((c, r))
                    elif ch == "F":
                        spawns.setdefault("flyers", []).append((c, r))
                    elif ch == "C":
                        spawns.setdefault("crates", []).append((c, r))
                else:
                    row.append(_CHAR.get(ch, 0))
            grid.append(row)
        return cls(grid, tile, deco)

    # ---- 查询 ----
    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def value(self, c: int, r: int) -> int:
        if not self.in_bounds(c, r):
            return -1
        return self.grid[r][c]

    def is_solid_cell(self, c: int, r: int) -> bool:
        """全实心（地形 / 墙 / 弹簧）：四个方向都阻挡。"""
        if not self.in_bounds(c, r):
            return False  # 边界外不阻挡（掉落即出界由 World._check_pit 处理）
        return self.grid[r][c] in SOLID_TILES

    def is_standable_cell(self, c: int, r: int) -> bool:
        """能作为落点的顶面（含单向平台）。"""
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] in STANDABLE_TILES

    def is_oneway_cell(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] == ONEWAY

    def is_wall_cell(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] == WALL

    def is_ladder_cell(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] == LADDER

    def is_spring_cell(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r):
            return False
        return self.grid[r][c] == SPRING

    def solid_pixel(self, px: float, py: float) -> bool:
        return self.is_solid_cell(int(px // self.tile), int(py // self.tile))

    def standable_pixel(self, px: float, py: float) -> bool:
        return self.is_standable_cell(int(px // self.tile), int(py // self.tile))

    def cell_at(self, px: float, py: float) -> int:
        c, r = int(px // self.tile), int(py // self.tile)
        if not self.in_bounds(c, r):
            return -1
        return self.grid[r][c]

    def set_cell(self, c: int, r: int, val: int) -> None:
        if self.in_bounds(c, r):
            self.grid[r][c] = val

    def remove_item(self, c: int, r: int) -> None:
        if self.in_bounds(c, r) and self.grid[r][c] in ITEM_TILES:
            self.grid[r][c] = 0

    # ---- 便捷构造（生成器 / 测试共用） ----
    def ladder_span(self, col: int, top_row: int, bottom_row: int) -> None:
        for r in range(top_row, bottom_row + 1):
            self.set_cell(col, r, LADDER)

    # ------------------------------------------------------------------
    # 渲染（地形 16 掩码自动拼接 + Kenney 道具）
    # ------------------------------------------------------------------
    def _solid_for_mask(self, c: int, r: int) -> bool:
        # 边界外视作实心：地面/边界不露出断面（仅用于自动拼接视觉，不影响物理）
        # 只把地形算进掩码：墙/弹簧走各自贴图，让接缝保留（视觉上"人造物"更清楚）
        if not self.in_bounds(c, r):
            return True
        return self.grid[r][c] == SOLID

    def _solid_mask(self, c: int, r: int) -> int:
        m = 0
        if self._solid_for_mask(c, r - 1):
            m |= 1
        if self._solid_for_mask(c + 1, r):
            m |= 2
        if self._solid_for_mask(c, r + 1):
            m |= 4
        if self._solid_for_mask(c - 1, r):
            m |= 8
        return m

    def _ladder_part(self, c: int, r: int) -> str:
        above = self.is_ladder_cell(c, r - 1)
        below = self.is_ladder_cell(c, r + 1)
        if not above and below:
            return "top"
        if above and not below:
            return "bottom"
        return "middle"

    def draw_deco(self, surface: pygame.Surface, cam) -> None:
        """装饰层：只画不碰，画在地形之后、实体之前。"""
        sp = self.sprites
        if not sp or not self.deco:
            return
        t = self.tile
        left, top = cam.world_left, cam.world_top
        c0, r0 = max(0, int(left // t)), max(0, int(top // t))
        c1 = min(self.cols, int((left + cam.view_w) // t) + 2)
        r1 = min(self.rows, int((top + cam.view_h) // t) + 2)
        for r in range(r0, r1):
            row = self.deco[r] if r < len(self.deco) else None
            if row is None:
                continue
            for c in range(c0, c1):
                name = row[c]
                if not name or name == ".":
                    continue
                img = sp.deco(name, t)
                if img:
                    surface.blit(img, (c * t - left, r * t - top))

    def draw(self, surface: pygame.Surface, cam) -> None:
        t = self.tile
        sp = self.sprites
        left, top = cam.world_left, cam.world_top
        c0, r0 = max(0, int(left // t)), max(0, int(top // t))
        c1, r1 = min(self.cols, int((left + cam.view_w) // t) + 1), min(self.rows, int((top + cam.view_h) // t) + 1)
        for r in range(r0, r1):
            for c in range(c0, c1):
                x, y = c * t - left, r * t - top
                idv = self.grid[r][c]
                if idv == SOLID:
                    img = sp.tile(self.theme, self._solid_mask(c, r), t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    pygame.draw.rect(surface, (70, 80, 96), (x, y, t, t))
                elif idv == WALL:
                    img = sp.wall(self.theme, t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        # 顶面高光：说明"这是一堵站得上去的静墙"
                        if not self.is_solid_cell(c, r - 1):
                            pygame.draw.rect(surface, (255, 255, 255, 60), (x, y, t, 3))
                        continue
                    pygame.draw.rect(surface, (150, 118, 82), (x, y, t, t))
                    pygame.draw.rect(surface, (188, 152, 108), (x + 3, y + 3, t - 6, t - 6))
                elif idv == LADDER:
                    img = sp.ladder(t, self._ladder_part(c, r)) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    pygame.draw.rect(surface, (170, 128, 76), (x + t * 0.16, y, t * 0.12, t))
                    pygame.draw.rect(surface, (170, 128, 76), (x + t * 0.72, y, t * 0.12, t))
                    pygame.draw.rect(surface, (206, 164, 106), (x + t * 0.16, y + t * 0.42, t * 0.68, t * 0.1))
                elif idv == ONEWAY:
                    img = sp.bridge(t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    pygame.draw.rect(surface, (140, 98, 56), (x, y, t, t * 0.26), border_radius=4)
                    pygame.draw.rect(surface, (182, 130, 74), (x, y, t, t * 0.12), border_radius=4)
                elif idv == SPRING:
                    img = sp.spring(t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    pygame.draw.rect(surface, (92, 104, 126), (x + 4, y + t * 0.55, t - 8, t * 0.4), border_radius=4)
                    pygame.draw.rect(surface, (86, 176, 232), (x + 2, y + t * 0.34, t - 4, t * 0.24), border_radius=6)
                elif idv == SPIKE:
                    img = sp.spike(t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    pygame.draw.polygon(surface, (200, 70, 80), [(x, y + t), (x + t / 2, y + t * 0.35), (x + t, y + t)])
                elif idv == COIN:
                    img = sp.coin(t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    cx, cy = x + t / 2, y + t / 2
                    pygame.draw.circle(surface, (246, 200, 62), (cx, cy), t * 0.28)
                    pygame.draw.circle(surface, (255, 236, 150), (cx, cy), t * 0.16)
                elif idv in (GEM_GREEN, GEM_YELLOW):
                    img = sp.gem("green" if idv == GEM_GREEN else "yellow", t) if sp else None
                    if img:
                        surface.blit(img, (int(x), int(y)))
                        continue
                    col = (90, 220, 120) if idv == GEM_GREEN else (240, 210, 80)
                    cx, cy = x + t / 2, y + t / 2
                    pygame.draw.polygon(surface, col, [(cx, cy - 14), (cx + 12, cy), (cx, cy + 14), (cx - 12, cy)])
                elif idv == DOOR:
                    # 两格高终点门：上格门楣 + 下格门体
                    if sp:
                        topimg = sp.door(True, False, t)
                        bodyimg = sp.door(False, False, t)
                        if bodyimg:
                            surface.blit(bodyimg, (int(x), int(y)))
                            if topimg and not self.is_solid_cell(c, r - 1):
                                surface.blit(topimg, (int(x), int(y - t)))
                            continue
                    pygame.draw.rect(surface, (120, 220, 255), (x, y, t, t), border_radius=6)
                elif idv in (PORTAL_A, PORTAL_B):
                    col = (90, 160, 255) if idv == PORTAL_A else (255, 160, 70)
                    pygame.draw.circle(surface, col, (x + t / 2, y + t / 2), t * 0.42)
