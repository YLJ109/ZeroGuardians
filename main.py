#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零零守护者 · 重写版 —— 根启动器。

运行方式（无需安装包）：
    python main.py                  # 窗口模式
    python main.py --fullscreen     # 全屏
    python main.py --headless --frames 500   # 无显示器冒烟测试（SDL 虚拟驱动）

无头模式会在不创建真实窗口的情况下跑完整主循环，用于 CI / 自检。
"""
import os
import sys

# 无头模式：在 import pygame 之前设置虚拟视频驱动
if "--headless" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# 把 src/ 加入搜索路径，使 `import zero_brother` 可用（src 布局最佳实践）
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))

from zero_brother import main as _main


def _parse():
    fullscreen = None
    max_frames = None
    if "--fullless" in sys.argv:
        pass
    if "--fullscreen" in sys.argv:
        fullscreen = True
    if "--headless" in sys.argv:
        fullscreen = False
    if "--frames" in sys.argv:
        i = sys.argv.index("--frames")
        if i + 1 < len(sys.argv):
            try:
                max_frames = int(sys.argv[i + 1])
            except ValueError:
                pass
    return fullscreen, max_frames


if __name__ == "__main__":
    fullscreen, max_frames = _parse()
    _main(max_frames=max_frames, fullscreen=fullscreen)
