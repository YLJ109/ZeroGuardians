"""零零守护者 · 重写版 —— 企业级 Pygame 游戏包。

包结构：
  zero_brother/
    config/    集中配置（GDD §12）
    core/      App、Scene、固定步长主循环（B2 根治）
    resources/ ResourceManager（B3 大小写 / B1 字体根治）
    input/     Action 抽象 + 键位映射 + 手柄（M1）
    scenes/    具体场景（splash / menu / gameplay...）
    systems/   跨场景系统（事件、相机…）

入口：python main.py  或  PYTHONPATH=src python -m zero_brother
"""
from .config import Config
from .core import App, Scene, SceneManager
from .scenes import SplashScene, MenuScene

__version__ = "0.1.0"


def main(max_frames: int | None = None, fullscreen: bool | None = None) -> None:
    """应用入口：载入配置 → 创建 App → 以启动动画为首场景运行。

    max_frames：仅用于无头冒烟测试，限制主循环帧数后自动退出。
    """
    cfg = Config.load()
    if fullscreen is not None:
        cfg.FULLSCREEN = fullscreen
    app = App(cfg)
    app.run(SplashScene(app), max_frames=max_frames)


__all__ = ["Config", "App", "Scene", "SceneManager", "SplashScene", "MenuScene", "main"]
