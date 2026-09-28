"""启动动画场景 —— "信号（技术感）" 锁定版 (GDD §20 / 用户选定)。

纯程序化绘制（无外部图片依赖），便于在任意环境复现：
  - numpy 径向渐变深色科技底
  - "YIMU GAME" 逐字 stagger 浮现（宽字距 = 西式 premium）
  - 青色渐变下划线从中心擦入
  - "PRESENTS" 淡入
  - 5.2s 后淡出，7.2s 自动重播；任意键 / 点击跳过 → 进入主菜单
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from ..core.scene import Scene

if TYPE_CHECKING:
    from ..core.app import App


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


class SplashScene(Scene):
    def __init__(self, app: "App"):
        super().__init__(app)
        self.cfg = app.config.SPLASH
        self.t = 0.0
        self._skip = False
        self._bg = None
        self._letters = []
        self._rule = None
        self._presents = None

    # ------------------------------------------------------------------
    def on_enter(self) -> None:
        w, h = self.app.screen.get_size()
        self._bg = self._make_bg(w, h)
        font = self.app.resources.font(self.cfg["font_size"])
        self._letters = []
        for ch in "YIMU GAME":
            if ch == " ":
                adv = font.size(" ")[0] * 0.6
                self._letters.append((None, None, adv))
            else:
                surf = font.render(ch, True, self.cfg["word_color"])
                glow = font.render(ch, True, self.cfg["glow_color"])
                self._letters.append((surf, glow, surf.get_width()))
        self._rule = self._make_rule(420, 2, self.cfg["rule_color"])
        self._presents = self.app.resources.font(int(self.cfg["font_size"] * 0.34)) \
            .render("PRESENTS", True, self.cfg["presents_color"])

    def reset(self) -> None:
        self.t = 0.0
        self._skip = False

    # ------------------------------------------------------------------
    def fixed_update(self, dt: float) -> None:
        self.t += dt
        if self._skip or self.t > self.cfg["loop_end"]:
            from .menu import MenuScene
            self.app.scenes.switch(MenuScene(self.app))
            return
        # 任意键 / 点击跳过（首帧忽略，避免上一场景残留输入误触）
        if self.t > 0.3 and self.app.input.any_key_pressed():
            self._skip = True

    # ------------------------------------------------------------------
    def render(self, alpha: float) -> None:
        t = self.t
        screen = self.app.screen
        w, h = screen.get_size()

        # 背景淡入
        bg_a = _clamp01(t / 1.2)
        screen.blit(self._bg, (0, 0))
        if bg_a < 1.0:
            dark = pygame.Surface((w, h))
            dark.fill((0, 0, 0))
            dark.set_alpha(int((1 - bg_a) * 255))
            screen.blit(dark, (0, 0))

        total = sum(adv + 30 for _, _, adv in self._letters) - 30
        x = (w - total) / 2
        base_y = h * 0.44

        # 整体淡出
        g_alpha = _clamp01(1.0 - (t - self.cfg["hold_end"]) / self.cfg["fade_out"]) if t > self.cfg["hold_end"] else 1.0

        for i, (surf, glow, adv) in enumerate(self._letters):
            p = _clamp01((t - self.cfg["letter_start"] - i * self.cfg["letter_stagger"]) / self.cfg["letter_dur"])
            if surf is None:
                x += adv + 30
                continue
            if p <= 0:
                x += adv + 30
                continue
            a = int(p * g_alpha * 255)
            oy = (1 - p) * 16
            g1 = glow.copy(); g1.set_alpha(int(a * 0.35))
            g2 = glow.copy(); g2.set_alpha(int(a * 0.20))
            screen.blit(g1, (x - 2, base_y + oy))
            screen.blit(g2, (x + 2, base_y + oy))
            s = surf.copy(); s.set_alpha(a)
            screen.blit(s, (x, base_y + oy))
            x += adv + 30

        # 下划线擦入
        rp = _clamp01((t - self.cfg["rule_start"]) / self.cfg["rule_dur"])
        if rp > 0:
            rw = int(self._rule.get_width() * rp)
            rh = self._rule.get_height()
            src = pygame.Rect((self._rule.get_width() - rw) // 2, 0, rw, rh)
            dest = pygame.Rect((w - rw) // 2, base_y + self.cfg["font_size"] + 26, rw, rh)
            tmp = self._rule.subsurface(src).copy()
            tmp.set_alpha(int(g_alpha * 255))
            screen.blit(tmp, dest)

        # PRESENTS
        pa = int(_clamp01((t - self.cfg["presents_start"]) / self.cfg["presents_dur"]) * g_alpha * 255)
        if pa > 0:
            ps = self._presents.copy(); ps.set_alpha(pa)
            screen.blit(ps, ((w - ps.get_width()) // 2, base_y + self.cfg["font_size"] + 56))

    # ------------------------------------------------------------------
    @staticmethod
    def _make_bg(w: int, h: int):
        try:
            import numpy as np
            cx, cy = w / 2.0, h * 0.42
            ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
            d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
            maxd = math.hypot(w / 2, h / 2)
            tt = np.clip(1.0 - d / maxd, 0.0, 1.0)[:, :, None]
            c = np.array((4, 7, 11), np.float32) * (1 - tt) + np.array((6, 18, 26), np.float32) * tt
            return pygame.image.frombuffer(c.astype(np.uint8).tobytes(), (w, h), "RGB").convert()
        except Exception:
            s = pygame.Surface((w, h)); s.fill((4, 7, 11)); return s

    @staticmethod
    def _make_rule(width: int, height: int, color):
        import numpy as np
        xs = np.linspace(0, 1, width).astype(np.float32)
        a = np.clip(1.0 - abs(xs - 0.5) * 2.0, 0.0, 1.0)
        a = (a * 255).astype(np.uint8)[:, None]
        arr = np.zeros((height, width, 4), np.uint8)
        arr[:, :, 0] = color[0]; arr[:, :, 1] = color[1]; arr[:, :, 2] = color[2]
        arr[:, :, 3] = a[:, 0]
        return pygame.image.frombuffer(arr.tobytes(), (width, height), "RGBA").convert_alpha()
