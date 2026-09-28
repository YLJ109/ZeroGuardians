"""场景基类与场景管理器 (GDD B2 根治：主循环永不重入)。

旧版在死亡/通关时递归调用 game_star() 重启，每次死亡栈 +1，最终 RecursionError。
新架构：主循环只跑一次，切换场景靠 SceneManager.switch()，死亡/重生靠场景内部
状态重置 (scene.reset())，绝不重新进入游戏函数。这是 §19.1 B2 的正式修复。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pygame

if TYPE_CHECKING:
    from .app import App


def blit_letterbox(screen: pygame.Surface, logic_surface: pygame.Surface, cfg) -> None:
    """把固定逻辑分辨率的画面等比缩放居中贴到实际屏幕（全屏/窗口通用）。"""
    sw, sh = screen.get_size()
    scale = min(sw / cfg.LOGIC_W, sh / cfg.LOGIC_H)
    dw, dh = int(cfg.LOGIC_W * scale), int(cfg.LOGIC_H * scale)
    ox, oy = (sw - dw) // 2, (sh - dh) // 2
    screen.fill((0, 0, 0))
    if (dw, dh) != (cfg.LOGIC_W, cfg.LOGIC_H):
        logic_surface = pygame.transform.smoothscale(logic_surface, (dw, dh))
    screen.blit(logic_surface, (ox, oy))


class Scene:
    """所有游戏场景的基类。"""

    def __init__(self, app: "App"):
        self.app = app

    # ---- 生命周期 ----
    def on_enter(self) -> None: ...

    def on_exit(self) -> None: ...

    def reset(self) -> None:
        """场景内部状态重置（用于死亡重生 / 重玩），不重建场景对象。"""

    # ---- 每帧 ----
    def fixed_update(self, dt: float) -> None: ...

    def render(self, alpha: float) -> None: ...

    def handle_event(self, event) -> None: ...


class SceneManager:
    def __init__(self, app: "App"):
        self.app = app
        self._current: Optional[Scene] = None

    @property
    def current(self) -> Optional[Scene]:
        return self._current

    def switch(self, scene: Scene) -> None:
        """原子切换：退出旧场景、进入新场景。主循环不重入。"""
        if self._current is not None:
            self._current.on_exit()
        self._current = scene
        scene.on_enter()

    def fixed_update(self, dt: float) -> None:
        if self._current is not None:
            self._current.fixed_update(dt)

    def render(self, alpha: float) -> None:
        if self._current is not None:
            self._current.render(alpha)

    def handle_event(self, event) -> None:
        if self._current is not None:
            self._current.handle_event(event)

    def quit(self) -> None:
        self.app.running = False
