#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YIMU GAME · 启动动画（"信号 / 技术感" 风格，锁定版）
=================================================================
独立可运行原型，验证进入 Pygame 后的真实观感。后续并入游戏主工程时，
把 SplashScene 接进场景管理器即可（M0/M6）。

运行：
    常规窗口： python yimu_splash.py
    全屏：     python yimu_splash.py --fullscreen
    无头截图： python yimu_splash.py --frame 2.6 --out frame.png
              （用 SDL 虚拟驱动渲染单帧并保存，用于无显示器环境自检）

交互：任意键 / 鼠标点击 = 跳过；F11 = 全屏/窗口切换；ESC = 退出。
"""

import os
import sys
import math
import argparse

import pygame

# ----------------------------------------------------------------------------
# 配置（后续统一收进 config.py / Config，这里先本地常量，便于移植）
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 1600, 900
FPS = 60

WORDMARK = "YIMU GAME"
FONT_SIZE = 128
LETTER_SPACING = 30          # 模拟 CSS letter-spacing，宽字距 = 西式 premium 感
WORD_COLOR = (238, 243, 247) # #eef3f7 近白
GLOW_COLOR = (63, 208, 214)  # #3fd0d6 青色描边辉光（克制）
RULE_COLOR = (63, 208, 214)
PRESENTS_COLOR = (95, 169, 179)  # #5fa9b3 青灰

# 背景径向渐变（深色科技底）
BG_CENTER = (6, 18, 26)      # #06121a
BG_EDGE = (4, 7, 11)         # #04070b

# 时间线（秒），与 HTML 原型一致
BG_FADE = 1.2
LETTER_START = 0.85
LETTER_STAGGER = 0.06
LETTER_DUR = 0.8
RULE_START = 2.0
RULE_DUR = 1.0
PRESENTS_START = 2.35
PRESENTS_DUR = 1.0
HOLD_END = 5.2               # 之后淡出
FADE_OUT = 1.1
LOOP_END = 7.2               # 无操作自动重播（仅预览用）

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


# ----------------------------------------------------------------------------
# 资源构建
# ----------------------------------------------------------------------------
def make_background(w, h):
    """用 numpy 生成径向渐变背景（中心亮、边缘暗）。"""
    try:
        import numpy as np
        cx, cy = w / 2.0, h * 0.42
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        maxd = math.hypot(w / 2, h / 2)
        t = np.clip(1.0 - d / maxd, 0.0, 1.0)
        t = t[:, :, None]
        c = np.array(BG_EDGE, np.float32) * (1 - t) + np.array(BG_CENTER, np.float32) * t
        # 轻微提亮中心
        surf = pygame.image.frombuffer(c.astype(np.uint8).tobytes(), (w, h), "RGB").convert()
        return surf
    except Exception:
        surf = pygame.Surface((w, h))
        surf.fill(BG_EDGE)
        return surf


def make_letter_surfaces(font, text):
    """把每个字形单独渲染，返回 (surface, advance) 列表，便于逐字做动画。"""
    out = []
    for ch in text:
        if ch == " ":
            space_w = font.size(" ")[0]
            out.append((None, space_w * 0.6))
            continue
        surf = font.render(ch, True, WORD_COLOR)
        glow = font.render(ch, True, GLOW_COLOR)
        out.append(((surf, glow), surf.get_width()))
    return out


def make_rule_strip(width, height, color):
    """生成一条 透明→青→透明 的水平渐变条，用于擦入下划线。"""
    import numpy as np
    xs = np.linspace(0, 1, width).astype(np.float32)
    # 三角窗：中心 1，两端 0
    a = np.clip(1.0 - abs(xs - 0.5) * 2.0, 0.0, 1.0)
    a = (a * 255).astype(np.uint8)[:, None]
    arr = np.zeros((height, width, 4), np.uint8)
    arr[:, :, 0] = color[0]
    arr[:, :, 1] = color[1]
    arr[:, :, 2] = color[2]
    arr[:, :, 3] = a[:, 0]
    return pygame.image.frombuffer(arr.tobytes(), (width, height), "RGBA").convert_alpha()


# ----------------------------------------------------------------------------
# 场景
# ----------------------------------------------------------------------------
class SplashScene:
    def __init__(self, screen, font_path, fullscreen=False):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.bg = make_background(self.w, self.h)
        self.font = pygame.font.Font(font_path, FONT_SIZE) if font_path else pygame.font.Font(None, FONT_SIZE)
        self.letters = make_letter_surfaces(self.font, WORDMARK)
        self.rule_full = make_rule_strip(420, 2, RULE_COLOR)
        self.presents = self.font.render("PRESENTS", True, PRESENTS_COLOR)
        self.presents = pygame.transform.scale(
            self.presents, (int(self.presents.get_width() * 0.34), int(self.presents.get_height() * 0.34))
        )
        self.t = 0.0
        self.done = False

    def reset(self):
        self.t = 0.0
        self.done = False

    def update(self, dt, events):
        for e in events:
            if e.type == pygame.QUIT:
                self.done = True
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.done = True
                elif e.key == pygame.K_F11:
                    self._toggle_fullscreen()
                else:
                    self.done = True
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.done = True
        self.t += dt

    def _toggle_fullscreen(self):
        flags = self.screen.get_flags()
        if flags & pygame.FULLSCREEN:
            pygame.display.set_mode((WIDTH, HEIGHT))
        else:
            pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        self.screen = pygame.display.get_surface()
        self.w, self.h = self.screen.get_size()
        self.bg = make_background(self.w, self.h)

    def draw(self):
        t = self.t
        # 整体淡出
        if t > HOLD_END:
            global_alpha = clamp01(1.0 - (t - HOLD_END) / FADE_OUT)
        else:
            global_alpha = 1.0

        self.screen.blit(self.bg, (0, 0))
        # 背景淡入
        bg_a = clamp01(t / BG_FADE)
        if bg_a < 1.0:
            dark = pygame.Surface((self.w, self.h))
            dark.fill((0, 0, 0))
            dark.set_alpha(int((1 - bg_a) * 255))
            self.screen.blit(self.bg, (0, 0))
            self.screen.blit(dark, (0, 0))

        # 计算文字总宽并居中
        total = sum(adv + LETTER_SPACING for _, adv in self.letters) - LETTER_SPACING
        x = (self.w - total) / 2
        base_y = self.h * 0.44

        for i, (pair, adv) in enumerate(self.letters):
            # 逐字 reveal
            p = clamp01((t - LETTER_START - i * LETTER_STAGGER) / LETTER_DUR)
            if pair is None:
                x += adv + LETTER_SPACING
                continue
            surf, glow = pair
            a = int(p * global_alpha * 255)
            if a <= 0:
                x += adv + LETTER_SPACING
                continue
            oy = (1 - p) * 16
            # 辉光：在白字下层叠 2 层低透明青色，模拟克制描边辉光
            g = glow.copy()
            g.set_alpha(int(a * 0.35))
            self.screen.blit(g, (x - 2, base_y + oy))
            g2 = glow.copy()
            g2.set_alpha(int(a * 0.20))
            self.screen.blit(g2, (x + 2, base_y + oy))
            s = surf.copy()
            s.set_alpha(a)
            self.screen.blit(s, (x, base_y + oy))
            x += adv + LETTER_SPACING

        # 下划线擦入（从中心向两侧展开）
        rp = clamp01((t - RULE_START) / RULE_DUR)
        if rp > 0:
            rw = int(self.rule_full.get_width() * rp)
            rh = self.rule_full.get_height()
            src = pygame.Rect((self.rule_full.get_width() - rw) // 2, 0, rw, rh)
            dest = pygame.Rect((self.w - rw) // 2, base_y + FONT_SIZE + 26, rw, rh)
            tmp = self.rule_full.subsurface(src).copy()
            tmp.set_alpha(int(global_alpha * 255))
            self.screen.blit(tmp, dest)

        # PRESENTS
        pa = int(clamp01((t - PRESENTS_START) / PRESENTS_DUR) * global_alpha * 255)
        if pa > 0:
            ps = self.presents.copy()
            ps.set_alpha(pa)
            self.screen.blit(ps, ((self.w - ps.get_width()) // 2, base_y + FONT_SIZE + 56))

    def is_finished(self):
        return self.done or self.t > LOOP_END


# ----------------------------------------------------------------------------
# 启动
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--frame", type=float, default=None, help="无头模式：渲染到该秒数并保存")
    parser.add_argument("--out", type=str, default="frame.png")
    args = parser.parse_args()

    if args.frame is not None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    if args.fullscreen and args.frame is None:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("YIMU GAME")
    font_path = pick_font()

    scene = SplashScene(screen, font_path, fullscreen=args.fullscreen)

    if args.frame is not None:
        # 无头自检：把时间推到指定秒数，渲染一帧保存
        scene.t = args.frame
        scene.draw()
        pygame.image.save(screen, args.out)
        print(f"[headless] saved frame at t={args.frame}s -> {args.out}")
        return

    clock = pygame.time.Clock()
    while not scene.is_finished():
        dt = clock.tick(FPS) / 1000.0
        events = pygame.event.get()
        scene.update(dt, events)
        scene.draw()
        pygame.display.flip()
        if scene.is_finished() and scene.t > LOOP_END:
            scene.reset()  # 自动重播（预览用）

    pygame.quit()


if __name__ == "__main__":
    main()
