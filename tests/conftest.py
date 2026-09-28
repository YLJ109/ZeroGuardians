"""pytest 前置：无头环境初始化（CI / 无显示器）。"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
