"""世界容器：装配关卡实体、推进物理/触发、相机跟随、胜负判定。

作为"game"对象传给玩家与技能（skills.py 通过 game.* 访问世界状态）。
"""
from __future__ import annotations

import math

import pygame

from ..world.tilemap import (
    TileMap, GEM_GREEN, GEM_YELLOW, COIN, DOOR, SPIKE, PORTAL_A, PORTAL_B, SOLID, ITEM_TILES,
)
from ..core.camera import Camera
from ..entities.player import Player
from ..entities.monster import Monster
from ..entities.boss import Boss
from ..entities.box import Box
from ..entities.portal import Portal
from ..heroes.registry import hero as hero_def

# 关卡主题 -> 精灵主题（Kenney 地形/背景前缀）
THEME_MAP = {"grass": "grass", "sand": "sand", "stone": "stone",
             "purple": "purple", "snow": "snow",
             # 兼容旧主题名
             "cave": "stone", "desert": "sand", "tech": "purple"}
# 主题 -> 敌人种类池（先见后危，含飞行怪）
THEME_ENEMY = {
    "grass":  ["snail", "ladybug", "bee"],
    "sand":   ["worm", "frog", "bee"],
    "stone":  ["slime", "mouse", "fly"],
    "purple": ["slime", "bee", "worm"],
    "snow":   ["snail", "mouse", "fly"],
}
FLYERS = {"bee", "fly"}


class World:
    def __init__(self, app, level, hero_picks: list[tuple]):
        self.app = app
        self.cfg = app.config
        self.level = level
        self.tile = self.cfg.BLOCK_SIZE
        spawns: dict = {}
        self.map = TileMap.from_rows(level.rows, self.tile, spawns,
                                     deco=getattr(level, "deco", None))
        self.world = self.map  # 别名：技能/玩家通过 game.world 访问瓦片世界
        self.input = app.input

        # 精灵资源层（真实 PNG 资产）；无 resources 时回退到图元绘制（headless 测试）
        self.theme = THEME_MAP.get(getattr(level, "theme", "grass"), "grass")
        self.map.theme = self.theme
        self.sprites = None
        res = getattr(app, "resources", None)
        if res is not None:
            from .sprites import Sprites
            self.sprites = Sprites(res, self.cfg)
        self.map.sprites = self.sprites

        self.players: list[Player] = []
        self.monsters: list[Monster] = []
        self.bullets: list = []
        self.boxes: list[Box] = []
        self.portals: list[Portal] = []
        self.bosses: list[Boss] = []
        self.boss_minion_kinds: list[str] = []
        self.fx: list[dict] = []
        # 语义事件队列：实体/触发逻辑只 emit，由场景层统一消费（播放音效/震动等）
        self.events: list[str] = []
        self.crates = self.cfg.TEAM_CRATES
        self.gems_total = self._count_tiles(GEM_GREEN, GEM_YELLOW)
        self.coins_total = self._count_tiles(COIN)
        self.gems_collected = 0
        self.coins = 0
        self.won = False
        self.pending_respawn: list[tuple[Player, float]] = []
        # 关卡底部死亡线：掉出世界（掉进深坑）即判定阵亡并重生，避免无限下坠
        self.pit_y = self.map.rows * self.tile + self.cfg.PLAYER_HITBOX[1] * 2

        # 玩家（按槽位号取出生格；缺失则贴地兜底，避免多人生成悬空）
        player_spawns = {s: (c, r) for (s, c, r) in spawns.get("players", [])}
        for slot, hid in hero_picks:
            c, r = player_spawns.get(slot, (1 + slot, 15))
            x = c * self.tile + (self.tile - self.cfg.PLAYER_HITBOX[0]) / 2
            y = r * self.tile + (self.tile - self.cfg.PLAYER_HITBOX[1])
            self.players.append(Player(slot, hid, x, y, self.cfg))

        # 怪物（按主题选型）：地面走怪 + 飞行怪
        kinds = THEME_ENEMY.get(self.theme, THEME_ENEMY["grass"])
        walk_kinds = [k for k in kinds if k not in FLYERS] or ["snail"]
        fly_kinds = [k for k in kinds if k in FLYERS] or ["bee"]
        for i, (c, r) in enumerate(spawns.get("monsters", [])):
            self.monsters.append(Monster(c * self.tile, r * self.tile, self.cfg,
                                         kind=walk_kinds[i % len(walk_kinds)], flyer=False))
        for i, (c, r) in enumerate(spawns.get("flyers", [])):
            self.monsters.append(Monster(c * self.tile, r * self.tile, self.cfg,
                                         kind=fly_kinds[i % len(fly_kinds)], flyer=True))
        # 关卡自带箱子：写入网格为实心（可站立），并生成渲染实体
        for c, r in spawns.get("crates", []):
            self.map.set_cell(c, r, SOLID)
            bx = Box(c * self.tile, r * self.tile, self.tile)
            bx.game = self
            self.boxes.append(bx)

        if level.boss:
            bx = level.boss.get("x", 16) * self.tile
            by = level.boss.get("y", 6) * self.tile
            self.bosses.append(Boss(bx, by, self.cfg, level.boss["phases"], theme=self.theme))
            # Boss 召唤用的小怪池（与主题一致，保证美术统一）
            self.boss_minion_kinds = walk_kinds

        self.camera = Camera(self.cfg.LOGIC_W, self.cfg.LOGIC_H,
                             self.map.cols * self.tile, self.map.rows * self.tile)
        self._follow_target = self.players[0].body if self.players else None

    # ------------------------------------------------------------------
    def _count_tiles(self, *values: int) -> int:
        want = set(values)
        n = 0
        for row in self.map.grid:
            for v in row:
                if v in want:
                    n += 1
        return n

    def _count_gems(self) -> int:
        return self._count_tiles(GEM_GREEN, GEM_YELLOW)

    # ------------------------------------------------------------------
    def emit(self, name: str) -> None:
        """登记一个语义事件（同名事件同帧只记一次，避免重复播放）。"""
        if name not in self.events:
            self.events.append(name)

    def drain_events(self) -> list[str]:
        out = self.events
        self.events = []
        return out

    def kill_player(self, p: Player) -> None:
        if not p.alive:
            return
        p.alive = False
        self.emit("hurt")
        self.pending_respawn.append((p, self.cfg.GAMEPLAY["respawn_time"]))

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        # 重生计时
        new_pending = []
        for p, t in self.pending_respawn:
            t -= dt
            if t <= 0:
                p.respawn()
            else:
                new_pending.append((p, t))
        self.pending_respawn = new_pending

        # 实体更新
        for p in self.players:
            if p.alive:
                p.update(dt, self)
        for m in self.monsters:
            if m.alive:
                m.update(dt, self)
        self.monsters = [m for m in self.monsters if not m.dead]
        for b in self.bullets:
            b.update(dt, self)
        self.bullets = [b for b in self.bullets if not b.dead]
        for pr in self.portals:
            pr.update(dt, self)
        for boss in self.bosses:
            if boss.alive:
                boss.update(dt, self)
        self.bosses = [bs for bs in self.bosses if not bs.dead]
        if self.bosses and all(not b.alive for b in self.bosses):
            # boss 全灭标记（bosses 列表已清空，用 won 判定复用）
            pass

        # 触发：宝石 / 金币 / 地刺 / 坠落 / 传送门 / 胜负
        self._triggers()

        # 相机：多人取存活玩家中点（单人即本人）
        alive = [p for p in self.players if p.alive]
        if alive:
            cx = sum(p.body.cx for p in alive) / len(alive)
            cy = sum(p.body.cy for p in alive) / len(alive)
            self.camera.follow(cx, cy)

        # FX
        for f in self.fx:
            f["life"] -= dt
        self.fx = [f for f in self.fx if f["life"] > 0]

    # ------------------------------------------------------------------
    def _triggers(self) -> None:
        for p in self.players:
            if not p.alive:
                continue
            b = p.body
            # 坠落出界：掉进深坑/出界 → 阵亡重生（否则会无限下坠，关卡无法通关）
            if b.y > self.pit_y:
                self.kill_player(p)
                continue
            # 宝石 / 金币：采样中心与脚下
            for (sx, sy) in [(b.cx, b.cy), (b.cx, b.y + b.h - 2)]:
                c, r = int(sx // self.tile), int(sy // self.tile)
                cell = self.map.cell_at(sx, sy)
                if cell == COIN:
                    self.map.remove_item(c, r)
                    self.coins += 1
                    self.emit("coin")
                    self.fx.append({"type": "pop", "x": sx, "y": sy, "life": 0.35})
                elif cell in (GEM_GREEN, GEM_YELLOW):
                    color = "green" if cell == GEM_GREEN else "yellow"
                    aff = p.hero["gem"]
                    if aff == "any" or aff == color:
                        self.map.remove_item(c, r)
                        self.gems_collected += 1
                        self.emit("gem")
                        self.fx.append({"type": "pop", "x": sx, "y": sy, "life": 0.4})
            # 地刺
            for (sx, sy) in [(b.cx, b.y + b.h - 6), (b.x + 4, b.y + b.h - 2), (b.x + b.w - 4, b.y + b.h - 2)]:
                if self.map.cell_at(sx, sy) == SPIKE:
                    self.kill_player(p)
                    break
            # 传送门
            if len(self.portals) >= 2:
                for i, pr in enumerate(self.portals):
                    if pr.cooldown == 0 and pr.rect().colliderect(b.rect):
                        other = self.portals[1 - i]
                        p.body.x = other.x
                        p.body.y = other.y - b.h / 2
                        p.body.vx = p.body.vy = 0
                        pr.cooldown = self.cfg.TELEPORT_COOLDOWN
                        other.cooldown = self.cfg.TELEPORT_COOLDOWN
                        self.emit("magic")
                        break
            # 终点门
            door_hit = self.map.cell_at(b.cx, b.cy) == DOOR or self.map.cell_at(b.cx, b.y + b.h - 2) == DOOR
            if door_hit:
                remaining = self._count_gems()
                boss_ok = (not self.bosses) or all(not bo.alive for bo in self.bosses)
                if remaining == 0 and boss_ok:
                    if not self.won:
                        self.emit("win")
                    self.won = True

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self.map.draw(surface, self.camera)
        self.map.draw_deco(surface, self.camera)
        for bx in self.boxes:
            bx.draw(surface, self.camera)
        for pr in self.portals:
            pr.draw(surface, self.camera)
        for m in self.monsters:
            m.draw(surface, self.camera)
        for bo in self.bosses:
            bo.draw(surface, self.camera)
        for bl in self.bullets:
            bl.draw(surface, self.camera)
        for p in self.players:
            if p.alive:
                p.draw(surface, self.camera)
        for f in self.fx:
            self._draw_fx(surface, f)

    def _draw_fx(self, surface, f):
        cam = self.camera
        cx = int(f["x"] - cam.world_left)
        cy = int(f["y"] - cam.world_top)
        life = max(0.0, f.get("life", 0.0))
        if f["type"] == "ring":
            base = max(1e-3, f.get("base_life", 0.4))
            t = 1.0 - min(1.0, life / base)         # 0 → 1 扩散
            r = int(f["r"] * (0.35 + 0.65 * t))
            w = max(2, int(6 * (1.0 - t)))
            layer = pygame.Surface((r * 2 + w * 2, r * 2 + w * 2), pygame.SRCALPHA)
            pygame.draw.circle(layer, (150, 240, 255, int(220 * (1.0 - t))),
                               (r + w, r + w), r, w)
            surface.blit(layer, (cx - r - w, cy - r - w))
        elif f["type"] == "pop":
            r = int(10 + 12 * (1.0 - min(1.0, life / 0.4)))
            layer = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(layer, (255, 244, 170, int(220 * min(1.0, life / 0.4))),
                               (r + 4, r + 4), r, 3)
            surface.blit(layer, (cx - r - 4, cy - r - 4))
        elif f["type"] == "deny":
            a = int(220 * min(1.0, life / 0.5))
            layer = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.line(layer, (255, 92, 92, a), (10, 10), (34, 34), 5)
            pygame.draw.line(layer, (255, 92, 92, a), (34, 10), (10, 34), 5)
            surface.blit(layer, (cx - 22, cy - 22))
