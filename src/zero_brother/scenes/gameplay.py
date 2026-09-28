"""游戏场景：装配 World，Kenney 视差背景 + 图标化 HUD + 暂停/通关覆盖层。

HUD 结构（三层信息带，避免"界面太简单"）：
  左上 资源计数  宝石 / 金币 / 建造箱（玻璃胶囊 + Kenney 像素数字）
  右上 关卡徽标  第 N 关 · 名称
  右侧 立体高度计 逐层显示「地面 / 一层 / 二层 …」+ 玩家所在层标记 + 推进进度条
  左下 队伍牌    头像 / 名字 / 状态（阵亡倒计时用色条呼吸提示）
  居中 开场横幅  关卡名 + 主题 + 本关机制图例（梯子/弹簧/单向平台/金币/静墙）
  底部 情境提示  攀爬中 / 暂停 / 操作提示

设计约束：所有 HUD 都是「表现层」，只读取 World 的公开状态（gems_total/coins/
players[].climbing…），不参与逻辑判定，因此 headless 测试（无 sprites/resources）
时依然按图元回退绘制，不会崩溃。
"""
from __future__ import annotations

import pygame

from ..core.scene import Scene, blit_letterbox
from ..world.world import World
from ..world.level import level_facts, TIER_NAMES
from ..world.sprites import HERO_COLOR
from ..ui import theme as T

BOSS_NAME = {
    "grass": "腐根巨像", "sand": "黄沙暴君", "snow": "霜牙守卫",
    "stone": "磐石魔像", "purple": "幽孢女王",
}
THEME_CN = {"grass": "草原", "sand": "沙漠", "snow": "雪原",
            "stone": "岩地", "purple": "菌林"}


class GameplayScene(Scene):
    def __init__(self, app, level, hero_picks):
        super().__init__(app)
        self.level = level
        self.world = World(app, level, hero_picks)
        self.logic = pygame.Surface((app.config.LOGIC_W, app.config.LOGIC_H))
        self.paused = False
        self.win_timer = 0.0
        self.t = 0.0
        # 关卡结构统计（HUD 高度计 / 开场横幅共用）
        self.facts = level_facts(level)
        # 开场横幅计时：淡入 → 停留 → 淡出
        self.intro_t = 0.0
        self.intro_dur = 3.4
        # 横向推进基准线（出生列 → 终点门列）
        tile = self.world.tile
        door_c = next((row.find("D") for row in level.rows if "D" in row), 30)
        spawn_c = next((i for i, ch in enumerate(level.rows[16]) if ch in "1234"), 1) \
            if len(level.rows) > 16 else 1
        self.start_x = spawn_c * tile
        self.door_x = max(self.start_x + tile, door_c * tile)

    def fixed_update(self, dt: float) -> None:
        self.t += dt
        if self.world.won:
            self.win_timer += dt
            if self.win_timer > 2.2:
                from .menu import MenuScene
                self.app.scenes.switch(MenuScene(self.app))
            self._flush_events()
            return
        if self.paused:
            return
        self.intro_t += dt
        self.world.update(dt)
        self._flush_events()

    def _flush_events(self) -> None:
        """消费世界事件队列 → 播放音效（表现层职责，逻辑层不依赖音频）。"""
        audio = getattr(self.app, "audio", None)
        for name in self.world.drain_events():
            if audio is not None:
                audio.play(name)

    def handle_event(self, event) -> None:
        audio = getattr(self.app, "audio", None)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.paused = not self.paused
                if audio:
                    audio.play("confirm" if self.paused else "back")
            elif event.key == pygame.K_r and self.paused:
                self.paused = False
                if audio:
                    audio.play("back")
                from .menu import MenuScene
                self.app.scenes.switch(MenuScene(self.app))
            elif event.key == pygame.K_ESCAPE:
                if audio:
                    audio.play("back")
                from .menu import MenuScene
                self.app.scenes.switch(MenuScene(self.app))

    def render(self, alpha: float) -> None:
        cfg = self.app.config
        self.logic.fill((14, 18, 26))
        self._background()
        self.world.draw(self.logic)
        self._hud()

        if self.intro_t < self.intro_dur and not self.paused:
            self._intro()
        if self.paused:
            self._pause_panel()
        if self.world.won:
            self._overlay("通关！", "返回菜单中…")
        blit_letterbox(self.app.screen, self.logic, cfg)

    # ------------------------------------------------------------------
    def _background(self) -> None:
        T.parallax_bg(self.logic, getattr(self.world, "sprites", None),
                      self.world.theme, self.world.camera.world_left)

    # ------------------------------------------------------------------
    def _hud(self) -> None:
        cfg = self.app.config
        res = self.app.resources
        sp = getattr(self.world, "sprites", None)
        w = self.world

        # ---- 左上：资源计数（宝石 / 金币 / 建造箱）三个玻璃胶囊 ----
        cy = 16
        x = 16
        gem = sp.gem("green", 30) if sp else None
        box = self._count_chip(x, cy, 188, gem, w.gems_collected, w.gems_total,
                               done=(w.gems_total > 0 and w.gems_collected >= w.gems_total))
        x = box.right + 12
        coin = sp.coin(28) if sp else None
        box = self._count_chip(x, cy, 184, coin, w.coins, w.coins_total,
                               done=(w.coins_total > 0 and w.coins >= w.coins_total))
        x = box.right + 12
        crate = sp.crate(28) if sp else None
        self._count_chip(x, cy, 158, crate, max(0, w.crates), None, label="建造箱")

        # ---- 右上：关卡徽标 ----
        label = f"第 {self.level.id} 关"
        name = self.level.name or ""
        nw = res.font(24).size(name)[0]
        bw = max(176, nw + 40)
        rbox = (cfg.LOGIC_W - bw - 16, cy, bw, 50)
        T.glass(self.logic, rbox, radius=13, border=T.PALETTE["accent"])
        T.text(self.logic, res, label, 18, T.PALETTE["muted"], topleft=(rbox[0] + 18, rbox[1] + 6))
        T.text(self.logic, res, name, 24, T.PALETTE["text"], topleft=(rbox[0] + 18, rbox[1] + 22))

        # ---- 右侧：立体高度计（多层关卡的核心信息）----
        self._altitude_card()

        # ---- Boss 血条（顶部居中）----
        if w.bosses:
            boss = w.bosses[0]
            bar_w = 520
            bx = (cfg.LOGIC_W - bar_w) // 2
            by = cy + 62
            T.glass(self.logic, (bx - 16, by - 16, bar_w + 32, 74), radius=14,
                    border=T.PALETTE["danger"])
            T.text(self.logic, res, BOSS_NAME.get(self.world.theme, "守卫者"), 22, T.PALETTE["text"],
                   center=(cfg.LOGIC_W // 2, by - 2), shadow_=True)
            pygame.draw.rect(self.logic, (46, 22, 26), (bx, by + 16, bar_w, 22), border_radius=8)
            ratio = max(0.0, boss.hp / boss.max_hp) if boss.max_hp else 0.0
            if ratio > 0:
                pygame.draw.rect(self.logic, T.PALETTE["danger"], (bx, by + 16, int(bar_w * ratio), 22), border_radius=8)
                pygame.draw.rect(self.logic, (255, 170, 170), (bx, by + 16, int(bar_w * ratio), 7), border_radius=8)
            pygame.draw.rect(self.logic, T.PALETTE["line"], (bx, by + 16, bar_w, 22), 2, border_radius=8)
            T.text(self.logic, res, f"阶段 {boss.phase + 1} / {len(boss.phases)}",
                   18, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, by + 50))

        # ---- 左下：玩家队伍牌 ----
        y = cfg.LOGIC_H - 74
        for p in w.players:
            self._player_plate(p, 16 + p.slot * 224, y)

        # ---- 底部居中：情境提示（攀爬中 / 全部阵亡）----
        self._context_hint()

        # ---- 右下：操作提示 + 静音状态 ----
        muted = getattr(getattr(self.app, "audio", None), "muted", False)
        hint = "P 暂停 · M 静音 · ESC 返回菜单"
        hw = res.font(18).size(hint)[0]
        T.text(self.logic, res, hint, 18, T.PALETTE["line"],
               topleft=(cfg.LOGIC_W - hw - 20, cfg.LOGIC_H - 30))
        if muted:
            T.text(self.logic, res, "已静音", 18, T.PALETTE["danger"],
                   topleft=(cfg.LOGIC_W - hw - 20, cfg.LOGIC_H - 52))

    # ---- 资源计数胶囊：图标 + 当前 / 上限（或纯计数）----
    def _count_chip(self, x, y, width, icon, value, total=None, done=False, label=None):
        sp = self.world.sprites
        res = self.app.resources
        box = pygame.Rect(x, y, width, 50)
        border = T.PALETTE["ok"] if done else T.PALETTE["line"]
        T.glass(self.logic, box, radius=13, border=border)
        cx = x + 14
        if icon is not None:
            self.logic.blit(icon, (cx, y + (50 - icon.get_height()) // 2))
        cx += 40
        if sp is not None:
            nimg = sp.number(value, 24)
            self.logic.blit(nimg, (cx, y + 13))
            cx += nimg.get_width() + 5
            if total is not None:
                T.text(self.logic, res, "/", 22, T.PALETTE["line"], topleft=(cx, y + 12))
                cx += 10
                self.logic.blit(sp.number(total, 24), (cx, y + 13))
                cx += sp.number(total, 24).get_width() + 10
        else:
            txt = f"{value}" if total is None else f"{value}/{total}"
            T.text(self.logic, res, txt, 22, T.PALETTE["text"], topleft=(cx, y + 13))
            cx += res.font(22).size(txt)[0] + 10
        if label:
            T.text(self.logic, res, label, 18, T.PALETTE["muted"], topleft=(cx, y + 16))
        return box

    # ---- 立体高度计：逐层列出「地面 / 一层 / …」，并标注每层玩家与道具 ----
    def _altitude_card(self) -> None:
        cfg = self.app.config
        res = self.app.resources
        w = self.world
        tiers = self.facts["tiers"]
        if not tiers:
            return
        lane_h = 30 if len(tiers) <= 5 else (24 if len(tiers) == 6 else 20)
        head, foot = 38, 42
        cw = 236
        ch = head + lane_h * len(tiers) + foot
        x = cfg.LOGIC_W - cw - 16
        y = 78
        T.glass(self.logic, (x, y, cw, ch), radius=14, alpha=198, border=T.PALETTE["line"])
        T.text(self.logic, res, "立体高度计", 19, T.PALETTE["text"], topleft=(x + 16, y + 11))
        lv_txt = f"{self.facts['layers']} 层"
        T.text(self.logic, res, lv_txt, 17, T.PALETTE["accent"],
               topleft=(x + cw - 16 - res.font(17).size(lv_txt)[0], y + 12))

        # 玩家 → 所在层（脚底行就近吸附到某一层的站立行）
        tile = w.tile
        on_lane: dict[int, list] = {}
        for p in w.players:
            if not p.alive:
                continue
            r = int((p.body.y + p.body.h - 1) // tile)
            i = min(range(len(tiers)), key=lambda k: abs(tiers[k]["stand"] - r))
            on_lane.setdefault(i, []).append(p)
        any_climb = any(p.climbing for p in w.players if p.alive)

        ly = y + head
        for i, t in enumerate(tiers):
            # 自下而上：索引 0 = 地面 → 画在最下面
            ry = ly + (len(tiers) - 1 - i) * lane_h
            inner_h = lane_h - 6
            on = i in on_lane
            if on:
                fill, rail = (26, 54, 68), T.PALETTE["accent"]
            else:
                fill, rail = (15, 21, 34), T.PALETTE["line"]
            pygame.draw.rect(self.logic, fill, (x + 14, ry + 3, cw - 28, inner_h), border_radius=7)
            pygame.draw.rect(self.logic, rail, (x + 14, ry + 3, 5, inner_h), border_radius=2)
            tname = TIER_NAMES[i] if i < len(TIER_NAMES) else f"{i} 层"
            T.text(self.logic, res, tname, 17,
                   T.PALETTE["text"] if on else T.PALETTE["muted"],
                   topleft=(x + 24, ry + (inner_h - 17) // 2))
            # 离地高度（格）
            alt = self.facts["ground_row"] - t["stand"]
            if alt:
                T.text(self.logic, res, f"+{alt}", 15, T.PALETTE["line"],
                       topleft=(x + 62, ry + (inner_h - 15) // 2 + 1))
            # 该层道具数
            if t["items"]:
                T.text(self.logic, res, f"道具{t['items']}", 15, T.PALETTE["muted"],
                       topleft=(x + 98, ry + (inner_h - 15) // 2 + 1))
            # 玩家色点（攀爬中加一圈白环）
            for k, p in enumerate(on_lane.get(i, [])):
                col = HERO_COLOR.get(p.hero_id, (200, 200, 200)) or p.color
                cxp = x + cw - 20 - k * 16
                cyp = ry + lane_h // 2
                pygame.draw.circle(self.logic, (8, 12, 22), (cxp, cyp), 8)
                pygame.draw.circle(self.logic, col, (cxp, cyp), 7)
                if p.climbing:
                    pygame.draw.circle(self.logic, (255, 255, 255), (cxp, cyp), 7, 2)

        # ---- 底部：横向推进度 ----
        fy = y + head + lane_h * len(tiers) + 6
        T.text(self.logic, res, "推进", 16, T.PALETTE["muted"], topleft=(x + 16, fy + 1))
        bx = x + 52
        bw = cw - 52 - 46
        pygame.draw.rect(self.logic, (15, 21, 34), (bx, fy + 3, bw, 13), border_radius=6)
        alive = [p for p in w.players if p.alive]
        span = max(1.0, self.door_x - self.start_x)
        prog = min(1.0, max(0.0, (max((p.body.cx for p in alive), default=self.start_x)
                                  - self.start_x) / span))
        if prog > 0:
            pygame.draw.rect(self.logic, T.PALETTE["accent"], (bx, fy + 3, int(bw * prog), 13),
                             border_radius=6)
        pygame.draw.rect(self.logic, T.PALETTE["line"], (bx, fy + 3, bw, 13), 1, border_radius=6)
        pct = f"{int(prog * 100)}%"
        T.text(self.logic, res, pct, 16, T.PALETTE["text"],
               topleft=(bx + bw + 6, fy + 1))

    # ---- 底部居中情境提示 ----
    def _context_hint(self) -> None:
        res = self.app.resources
        w = self.world
        if w.won or self.paused:
            return
        alive = [p for p in w.players if p.alive]
        text = None
        color = T.PALETTE["accent"]
        if alive and any(p.climbing for p in alive):
            text = "攀爬中 · 上/下 移动 · 左右 可脱离梯子"
            color = HERO_COLOR.get(alive[0].hero_id, T.PALETTE["accent"])
        elif w.players and not alive:
            text = "全队阵亡 · 复活中…"
            color = T.PALETTE["danger"]
        if not text:
            return
        f = res.font(19)
        tw = f.size(text)[0]
        box = pygame.Rect(0, 0, tw + 40, 36)
        # 放在队伍牌上方，避免 4 人时与左下角牌位重叠
        box.center = (self.app.config.LOGIC_W // 2, self.app.config.LOGIC_H - 104)
        T.glass(self.logic, box, radius=18, alpha=200, border=color)
        T.text(self.logic, res, text, 19, T.PALETTE["text"], center=box.center)

    # ---- 开场横幅：关卡名 + 主题 + 本关机制图例 ----
    def _intro(self) -> None:
        cfg = self.app.config
        res = self.app.resources
        sp = getattr(self.world, "sprites", None)
        t, dur = self.intro_t, self.intro_dur
        if t < 0.35:
            a = t / 0.35
        elif t > dur - 0.6:
            a = max(0.0, (dur - t) / 0.6)
        else:
            a = 1.0
        if a <= 0.01:
            return
        # 与 HUD 元素避让：放在 Boss 血条之下、角色之上
        w, h = 780, 296
        x, y = (cfg.LOGIC_W - w) // 2, (cfg.LOGIC_H - h) // 2 - 40
        lay = pygame.Surface((cfg.LOGIC_W, cfg.LOGIC_H), pygame.SRCALPHA)
        # 轻微上浮入场
        y += int((1.0 - a) * 16)
        T.glass(lay, (x, y, w, h), radius=20, alpha=214, border=T.PALETTE["accent"], border_w=3)
        T.gradient_h(lay, (x + 2, y + 2, w - 4, 6), T.PALETTE["accent"], T.PALETTE["accent2"])

        boss = bool(self.level.boss)
        tag = "BOSS 关" if boss else THEME_CN.get(self.level.theme, self.level.theme)
        head = f"第 {self.level.id} 关 · {tag}"
        T.text(lay, res, head, 20, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, y + 34))
        T.text(lay, res, self.level.name, 54, T.PALETTE["text"],
               center=(cfg.LOGIC_W // 2, y + 82), shadow_=True)
        pygame.draw.line(lay, T.PALETTE["line"], (x + 60, y + 122), (x + w - 60, y + 122), 2)

        # 机制图例（只列出本关真实存在的）
        items = self._intro_items(sp)
        if items:
            chip_w, gap = 152, 10
            total = chip_w * len(items) + gap * (len(items) - 1)
            cx = (cfg.LOGIC_W - total) // 2
            cyy = y + 146
            for icon, name, num in items:
                box = pygame.Rect(cx, cyy, chip_w, 52)
                T.glass(lay, box, radius=12, alpha=150, border=T.PALETTE["line"])
                ix = box.x + 12
                if icon is not None:
                    lay.blit(icon, (ix, box.y + (52 - icon.get_height()) // 2))
                    ix += 34
                T.text(lay, res, name, 17, T.PALETTE["muted"], topleft=(ix, box.y + 9))
                T.text(lay, res, f"×{num}", 20, T.PALETTE["text"], topleft=(ix, box.y + 27))
                cx += chip_w + gap

        goal = (f"目标：集齐 {self.facts['counts']['gem']} 颗宝石 → 穿过终点门"
                if boss is False else "目标：击败 Boss 的全部阶段")
        T.text(lay, res, goal, 22, T.PALETTE["gold"],
               center=(cfg.LOGIC_W // 2, y + h - 62))
        T.text(lay, res, f"本关共 {self.facts['layers']} 层立体结构 · 上层也有道具，记得爬梯/踩弹簧上去",
               18, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, y + h - 32))

        lay.set_alpha(int(255 * a))
        self.logic.blit(lay, (0, 0))

    def _intro_items(self, sp):
        """本关有哪些机制（图标, 名称, 数量）；梯子按「条数」而不是格数统计。"""
        c = self.facts["counts"]
        raw = [
            ("L", "梯子", len(self.facts["ladder_cols"])),
            ("S", "弹簧", c["spring"]),
            ("=", "单向平台", c["bridge"]),
            ("W", "静墙", c["wall"]),
            ("$", "金币", c["coin"]),
            ("^", "地刺", c["spike"]),
        ]
        out = []
        for key, name, num in raw:
            if not num:
                continue
            icon = None
            if sp is not None:
                icon = {"L": lambda: sp.ladder(30),
                        "S": lambda: sp.spring(30),
                        "=": lambda: sp.bridge(30),
                        "W": lambda: sp.wall(self.world.theme, 30),
                        "$": lambda: sp.coin(26),
                        "^": lambda: sp.spike(28)}[key]()
            out.append((icon, name, num))
        return out[:6]

    def _player_plate(self, p, x, y) -> None:
        res = self.app.resources
        sp = getattr(self.world, "sprites", None)
        col = HERO_COLOR.get(p.hero_id, (200, 200, 200)) or p.color
        w, h = 208, 58
        T.glass(self.logic, (x, y, w, h), radius=13, alpha=190 if p.alive else 120,
                border=col if p.alive else T.PALETTE["line"])
        # 头像框
        pygame.draw.rect(self.logic, (10, 16, 28,), (x + 7, y + 7, 44, 44), border_radius=10)
        if sp:
            por = sp.portrait(p.hero_id, 40)
            if por:
                self.logic.blit(por, (x + 9, y + 9))
            g = sp.hero_gem(p.hero_id, 18)
            if g:
                self.logic.blit(g, (x + 180, y + 20))
        name = res.font(23).render(p.hero["name"], True, col if p.alive else (150, 160, 175))
        self.logic.blit(name, (x + 60, y + 7))
        if p.alive:
            T.text(self.logic, res, "就绪", 17, T.PALETTE["ok"], topleft=(x + 60, y + 34))
        else:
            T.text(self.logic, res, "阵亡 · 复活中", 17, T.PALETTE["danger"], topleft=(x + 60, y + 34))
        # 左侧玩家色条
        pygame.draw.rect(self.logic, col, (x + 2, y + 10, 4, h - 20), border_radius=2)

    def _overlay(self, title: str, hint: str) -> None:
        cfg = self.app.config
        ov = pygame.Surface((cfg.LOGIC_W, cfg.LOGIC_H), pygame.SRCALPHA)
        ov.fill((4, 8, 16, 165))
        self.logic.blit(ov, (0, 0))
        box_w, box_h = 560, 208
        bx, by = (cfg.LOGIC_W - box_w) // 2, (cfg.LOGIC_H - box_h) // 2
        T.panel(self.logic, (bx, by, box_w, box_h), radius=20,
                fill=T.PALETTE["panel2"], border=T.PALETTE["accent"], border_w=3)
        T.text(self.logic, self.app.resources, title, 64, T.PALETTE["text"],
               center=(cfg.LOGIC_W // 2, by + 78), shadow_=True)
        T.text(self.logic, self.app.resources, hint, 22, T.PALETTE["muted"],
               center=(cfg.LOGIC_W // 2, by + 142))

    # ---- 暂停面板：左「操作」右「立体机制」，让玩家随时能查怎么爬梯/踩弹簧 ----
    def _pause_panel(self) -> None:
        cfg = self.app.config
        res = self.app.resources
        sp = getattr(self.world, "sprites", None)
        ov = pygame.Surface((cfg.LOGIC_W, cfg.LOGIC_H), pygame.SRCALPHA)
        ov.fill((4, 8, 16, 180))
        self.logic.blit(ov, (0, 0))
        box_w, box_h = 900, 468
        bx, by = (cfg.LOGIC_W - box_w) // 2, (cfg.LOGIC_H - box_h) // 2
        T.panel(self.logic, (bx, by, box_w, box_h), radius=22,
                fill=T.PALETTE["panel2"], border=T.PALETTE["accent"], border_w=3)
        T.gradient_h(self.logic, (bx + 3, by + 3, box_w - 6, 6),
                     T.PALETTE["accent"], T.PALETTE["accent2"])
        T.text(self.logic, res, "已暂停", 46, T.PALETTE["text"],
               center=(cfg.LOGIC_W // 2, by + 44), shadow_=True)

        col_w = (box_w - 96) // 2
        lx, rx = bx + 36, bx + 60 + col_w
        top = by + 92
        # 左：本局玩家操作（默认键位：A/D 移动 · W 跳 · S 下蹲/下梯 · J/K 技能）
        T.text(self.logic, res, "操作", 22, T.PALETTE["accent"], topleft=(lx, top))
        controls = [
            ("A / D", "左右移动"),
            ("W / 空格", "跳跃（可长按跳更高）"),
            ("S", "下蹲 · 站在梯子上按下抓梯"),
            ("W", "站在梯子上按住上爬"),
            ("J / K", "技能 A / 技能 B"),
            ("P", "暂停 / 继续"),
        ]
        cyy = top + 34
        for key, desc in controls:
            T.pill(self.logic, res, (lx + 60, cyy + 14), key, active=True, w=110)
            T.text(self.logic, res, desc, 18, T.PALETTE["text"], topleft=(lx + 128, cyy + 4))
            cyy += 38

        # 右：立体机制速查（按本关实际存在的机制列出）
        T.text(self.logic, res, "立体机制", 22, T.PALETTE["accent"], topleft=(rx, top))
        cyy = top + 34
        mechs = self._intro_items(sp)[:6]
        for icon, name, _num in mechs:
            ix = rx
            if icon is not None:
                self.logic.blit(icon, (ix, cyy + 2))
                ix += 34
            T.text(self.logic, res, name, 19, T.PALETTE["text"], topleft=(ix, cyy))
            T.text(self.logic, res, self._mech_tip(name), 16, T.PALETTE["muted"],
                   topleft=(ix + 90, cyy + 3))
            cyy += 34
        if not mechs:
            T.text(self.logic, res, "本关没有特殊机制，专心跳跃与收集即可",
                   18, T.PALETTE["muted"], topleft=(rx, cyy))

        hint = "P 继续 · R / ESC 返回菜单 · M 静音"
        T.text(self.logic, res, hint, 20, T.PALETTE["muted"],
               center=(cfg.LOGIC_W // 2, by + box_h - 28))

    @staticmethod
    def _mech_tip(name: str) -> str:
        return {
            "梯子": "按上/下攀爬，可脱离",
            "弹簧": "踩上去自动高弹",
            "单向平台": "下方可跳穿",
            "静墙": "固定障碍，不受重力",
            "金币": "可选奖励",
            "地刺": "碰到即阵亡",
        }.get(name, "")
