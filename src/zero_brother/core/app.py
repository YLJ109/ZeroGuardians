"""应用入口与主循环 (M0 基建核心)。

职责：
  - 初始化 pygame / 显示表面
  - 持有 Config / ResourceManager / InputManager / SceneManager
  - 跑固定步长主循环（loop.FixedTimestep）
  - 分发事件到 InputManager 与当前场景
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from .loop import FixedTimestep
from .scene import SceneManager

if TYPE_CHECKING:
    from ..config.settings import Config
    from ..resources.manager import ResourceManager
    from ..input.manager import InputManager


class App:
    def __init__(self, config: "Config"):
        self.config = config
        self.running = True

        pygame.init()
        flags = pygame.FULLSCREEN if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode((config.LOGIC_W, config.LOGIC_H), flags)
        pygame.display.set_caption("零零守护者 · 重写版")

        self.clock = pygame.time.Clock()
        self.timestep = FixedTimestep(config.FIXED_DT)

        # 子系统延迟导入，避免循环依赖
        from ..resources.manager import ResourceManager
        from ..input.manager import InputManager

        self.resources: "ResourceManager" = ResourceManager(config)
        self.input: "InputManager" = InputManager(config, self.resources)

        from ..systems.audio import AudioManager
        self.audio: AudioManager = AudioManager(
            self.resources,
            enabled=bool(getattr(config, "AUDIO", True)),
        )
        self.audio.set_master(getattr(config, "AUDIO_MASTER", 0.85))

        self.scenes: SceneManager = SceneManager(self)

    # ------------------------------------------------------------------
    def run(self, first_scene, max_frames: int | None = None) -> None:
        self.scenes.switch(first_scene)
        cfg = self.config
        frames = 0
        while self.running:
            # 1) 收集事件
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self._toggle_fullscreen()
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                    # 全局静音开关（不传给场景，避免与「技能键」冲突）
                    muted = self.audio.toggle_mute()
                    if not muted:
                        self.audio.play("toggle")
                else:
                    self.scenes.handle_event(e)
            self.input.poll(events)

            # 2) 固定步长逻辑更新（绝不重入）
            self.timestep.advance(
                self.clock.tick(cfg.FPS) / 1000.0,
                self.scenes.fixed_update,
            )

            # 3) 渲染（可带插值 alpha）
            self.scenes.render(self.timestep._acc / self.timestep.step)
            pygame.display.flip()

            frames += 1
            if max_frames is not None and frames >= max_frames:
                self.running = False

        pygame.quit()

    # ------------------------------------------------------------------
    def _toggle_fullscreen(self) -> None:
        flags = self.screen.get_flags()
        if flags & pygame.FULLSCREEN:
            self.screen = pygame.display.set_mode(
                (self.config.LOGIC_W, self.config.LOGIC_H)
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.config.LOGIC_W, self.config.LOGIC_H), pygame.FULLSCREEN
            )
