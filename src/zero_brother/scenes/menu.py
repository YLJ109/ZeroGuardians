"""主菜单场景：视差背景 + 标题 + 可选择按钮 + 吉祥物，进入角色选择 / 快速开始 / 退出。"""
from __future__ import annotations

import os

import pygame

from ..core.scene import Scene, blit_letterbox
from ..world.level import load_level
from ..world.sprites import Sprites
from ..levels.generate import generate_all, levels_dir
from ..ui import theme as T


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self._ensure_levels()
        self.logic = pygame.Surface((app.config.LOGIC_W, app.config.LOGIC_H))
        self.sprites = Sprites(app.resources, app.config) if getattr(app, "resources", None) else None
        self.t = 0.0
        self.index = 0
        self.items = [
            {"label": "开始冒险", "sub": "1-4 人 · 选择英雄与关卡", "action": "select", "art": ("flag", "green")},
            {"label": "快速开始", "sub": "单人 · 第 1 关（弓箭手）", "action": "quick", "art": ("gem", "yellow")},
            {"label": "选关挑战", "sub": "直达 1-15 关（L5/L10/L15 为 Boss）", "action": "levels", "art": ("portal", None)},
            {"label": "退出游戏", "sub": "ESC 亦可退出", "action": "quit", "art": ("door", None)},
        ]

    # ------------------------------------------------------------------
    def _icon(self, spec):
        """把 (类型, 参数) 描述解析成一张 40px 图标；失败返回 None。"""
        if not spec or not self.sprites:
            return None
        kind, arg = spec
        try:
            if kind == "flag":
                return self.sprites.flag(arg, 0, 40)
            if kind == "gem":
                return self.sprites.gem(arg, 36)
            if kind == "portal":
                return self.sprites.portal(True, 38)
            if kind == "door":
                return self.sprites.door(False, False, 40)
        except Exception:
            return None
        return None

    # ------------------------------------------------------------------
    def _ensure_levels(self) -> None:
        d = levels_dir()
        if not os.path.exists(os.path.join(d, "level_1.json")):
            generate_all(d)

    def fixed_update(self, dt: float) -> None:
        self.t += dt

    # ------------------------------------------------------------------
    def handle_event(self, event) -> None:
        audio = getattr(self.app, "audio", None)
        if event.type == pygame.MOUSEMOTION:
            before = self.index
            self._hover(event.pos)
            if self.index != before and audio:
                audio.play("hover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hover(event.pos):
                self._activate(self.index)
        elif event.type == pygame.KEYDOWN:
            k = event.key
            if k in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.items)
                if audio:
                    audio.play("scroll")
            elif k in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.items)
                if audio:
                    audio.play("scroll")
            elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j):
                self._activate(self.index)
            elif k == pygame.K_ESCAPE:
                self.app.running = False
            # 数字键快速直开
            elif pygame.K_1 <= k <= pygame.K_9:
                self._quick(k - pygame.K_0)
            elif k == pygame.K_0:
                self._quick(15)

    def _hover(self, pos) -> bool:
        mx, my = pos
        for i in range(len(self.items)):
            if self._item_rect(i).collidepoint(mx, my):
                self.index = i
                return True
        return False

    def _item_rect(self, i) -> pygame.Rect:
        w = 460
        return pygame.Rect(150, 300 + i * 108, w, 84)

    def _activate(self, i) -> None:
        audio = getattr(self.app, "audio", None)
        action = self.items[i]["action"]
        if action == "quit":
            if audio:
                audio.play("back")
            self.app.running = False
        elif action == "quick":
            if audio:
                audio.play("confirm")
            self._quick(1)
        elif action == "levels":
            if audio:
                audio.play("confirm")
            from .select import CharacterSelectScene
            sc = CharacterSelectScene(self.app)
            sc.phase = "level"
            self.app.scenes.switch(sc)
        else:
            if audio:
                audio.play("confirm")
            from .select import CharacterSelectScene
            self.app.scenes.switch(CharacterSelectScene(self.app))

    def _quick(self, idn: int) -> None:
        path = os.path.join(levels_dir(), f"level_{idn}.json")
        if not os.path.exists(path):
            if getattr(self.app, "audio", None):
                self.app.audio.play("deny")
            return
        from .gameplay import GameplayScene
        self.app.scenes.switch(GameplayScene(self.app, load_level(path), [(0, "archer")]))

    # ------------------------------------------------------------------
    def render(self, alpha: float) -> None:
        cfg = self.app.config
        g = self.logic
        scroll = self.t * 40
        T.parallax_bg(g, self.sprites, "grass", scroll, factor=0.18)
        # 左侧渐变遮罩：保证标题/按钮可读，同时保留右侧彩色背景
        T.left_scrim(g, (8, 12, 22), 205, int(cfg.LOGIC_W * 0.68))
        T.vignette(g, 110)

        # 标题
        T.text(g, self.app.resources, "零零守护者", 96, T.PALETTE["text"], topleft=(150, 96), shadow_=True)
        pygame.draw.rect(g, T.PALETTE["accent"], (152, 210, 420, 5), border_radius=3)
        T.text(g, self.app.resources, "ZERO GUARDIANS  ·  重写版", 26, T.PALETTE["accent"], topleft=(154, 228))
        T.text(g, self.app.resources, "双人协作 · 六位英雄 · 十五道关卡", 22, T.PALETTE["muted"], topleft=(154, 262))

        # 菜单项
        for i, it in enumerate(self.items):
            T.button(g, self.app.resources, self._item_rect(i), it["label"],
                     selected=(i == self.index), sub=it["sub"], icon=self._icon(it.get("art")))

        # 吉祥物（右侧，行走动画）
        if self.sprites:
            frame = int(self.t * 6) % 2
            img = self.sprites.char_walk("archer", frame, 1, 168)
            if img:
                g.blit(img, (cfg.LOGIC_W - 380, cfg.LOGIC_H - 300))
            img2 = self.sprites.char_walk("builder", frame, -1, 150)
            if img2:
                g.blit(img2, (cfg.LOGIC_W - 240, cfg.LOGIC_H - 282))

        # 页脚
        muted = getattr(getattr(self.app, "audio", None), "muted", False)
        T.text(g, self.app.resources, "↑↓/WS 选择 · Enter 确认 · 1-9 快速跳关 · M 静音 · Esc 退出 · F11 全屏",
               20, T.PALETTE["muted"], center=(cfg.LOGIC_W // 2, cfg.LOGIC_H - 34))
        T.text(g, self.app.resources, "v0.5 · assets by Kenney (CC0) · font Noto Sans SC (OFL)",
               18, T.PALETTE["line"], topleft=(20, cfg.LOGIC_H - 28))
        if muted:
            T.pill(g, self.app.resources, (cfg.LOGIC_W - 84, cfg.LOGIC_H - 36), "已静音", active=False, w=110)
        blit_letterbox(self.app.screen, g, cfg)
