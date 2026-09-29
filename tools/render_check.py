#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无头渲染自检：把各场景渲染成 PNG，便于人工/自动比对。

用法：
    # 全量自检（默认输出 .workbuddy/tmp_shots/）
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/render_check.py

    # 只出 README 用的封面图（8 张，默认直接写进 docs/screenshots/）
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/render_check.py --readme
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import pygame  # noqa: E402
from zero_brother.config.settings import Config  # noqa: E402
from zero_brother.core.app import App  # noqa: E402

OUT = os.path.join(_ROOT, ".workbuddy", "tmp_shots")
README_OUT = os.path.join(_ROOT, "docs", "screenshots")


def _shot(app: App, scene, name: str, ticks: int = 20, alpha: float = 0.0):
    app.scenes.switch(scene)
    for _ in range(ticks):
        scene.fixed_update(1 / 60)
    scene.render(alpha)
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))
    print("[shot]", name)


def _select_level(app: App, cursor: int, name: str, ticks: int = 30):
    from zero_brother.scenes.select import CharacterSelectScene
    sel = CharacterSelectScene(app)
    sel.phase = "level"
    sel.level_cursor = cursor
    _shot(app, sel, name, ticks=ticks)


# ---------------------------------------------------------------------------
# README 封面图：8 张，覆盖「启动动画 → 菜单 → 选人 → 选关 → 玩法 → 立体关卡 → Boss → 暂停」
# ---------------------------------------------------------------------------
def _readme_set(app: App, d: str) -> None:
    from zero_brother.scenes.menu import MenuScene
    from zero_brother.scenes.select import CharacterSelectScene
    from zero_brother.scenes.splash import SplashScene
    from zero_brother.scenes.gameplay import GameplayScene
    from zero_brother.world.level import load_level

    _shot(app, SplashScene(app), "01-splash", ticks=175)
    _shot(app, MenuScene(app), "02-menu", ticks=30)

    sel = CharacterSelectScene(app)
    sel.count = 3
    _shot(app, sel, "03-heroes", ticks=30)
    _select_level(app, 10, "04-levels")

    # 玩法：L1（入门，3 层）+ L11（满配，7 层）
    for idn, name, ticks in ((1, "05-gameplay", 300), (11, "06-vertical", 300)):
        sc = GameplayScene(app, load_level(os.path.join(d, f"level_{idn}.json")),
                           [(0, "archer"), (1, "ninja")])
        _shot(app, sc, name, ticks=ticks)

    # Boss：L15 幽孢女王
    boss = GameplayScene(app, load_level(os.path.join(d, "level_15.json")),
                         [(0, "archer"), (1, "warlock")])
    _shot(app, boss, "07-boss", ticks=420)

    # 暂停面板（操作 + 立体机制速查）
    scp = GameplayScene(app, load_level(os.path.join(d, "level_11.json")),
                        [(0, "archer"), (1, "builder")])
    for _ in range(300):
        scp.fixed_update(1 / 60)
    scp.paused = True
    _shot(app, scp, "08-paused", ticks=1)


# ---------------------------------------------------------------------------
def _full_set(app: App, d: str) -> None:
    from zero_brother.scenes.menu import MenuScene
    from zero_brother.scenes.select import CharacterSelectScene
    from zero_brother.scenes.splash import SplashScene
    from zero_brother.scenes.gameplay import GameplayScene
    from zero_brother.world.level import load_level

    # 启动动画分帧取样（逐字浮现 / 下划线 / PRESENTS）
    for tag, ticks in (("a", 70), ("b", 130), ("c", 175), ("d", 290)):
        _shot(app, SplashScene(app), f"00_splash_{tag}", ticks=ticks)

    _shot(app, MenuScene(app), "01_menu", ticks=30)

    sel = CharacterSelectScene(app)
    sel.count = 3
    _shot(app, sel, "02_select_heroes", ticks=30)
    # 选关预览：L1（入门 3 层）/ L11（7 层满配）/ L15（Boss 三台）
    _select_level(app, 0, "03_select_level_L1")
    _select_level(app, 10, "03_select_level_L11")
    _select_level(app, 14, "03_select_level_L15")

    for idn, tag in [(1, "L1"), (2, "L2"), (4, "L4"), (7, "L7"), (9, "L9"),
                     (11, "L11"), (5, "L5_boss"), (10, "L10_boss"), (15, "L15_boss")]:
        path = os.path.join(d, f"level_{idn}.json")
        if not os.path.exists(path):
            continue
        # ticks=90：开场横幅正处于停留期 → 检查横幅排版
        sc = GameplayScene(app, load_level(path), [(0, "archer"), (1, "ninja")])
        _shot(app, sc, f"04_game_{tag}_intro", ticks=90)
        # ticks=300：横幅已淡出 → 检查常态 HUD（计数胶囊 / 高度计 / 队伍牌）
        sc2 = GameplayScene(app, load_level(path), [(0, "archer"), (1, "ninja")])
        _shot(app, sc2, f"05_game_{tag}_hud", ticks=300)

    # 暂停面板（操作 + 立体机制速查）
    scp = GameplayScene(app, load_level(os.path.join(d, "level_11.json")),
                        [(0, "archer"), (1, "builder")])
    for _ in range(300):
        scp.fixed_update(1 / 60)
    scp.paused = True
    _shot(app, scp, "06_game_paused", ticks=1)


def main(argv=None):
    global OUT
    parser = argparse.ArgumentParser(description="无头渲染自检 / README 封面图生成")
    parser.add_argument("--out", default=None,
                        help="PNG 输出目录（默认：--readme 时 docs/screenshots/，否则 .workbuddy/tmp_shots/）")
    parser.add_argument("--readme", action="store_true", help="只出 README 封面图（8 张）")
    args = parser.parse_args(argv)
    # --readme 的产物是给 README 引用的，必须落到 docs/screenshots/，否则截图会
    # 静默写进 .workbuddy/ 而被 .gitignore 吃掉，README 里的图就再不更新。
    default_out = README_OUT if args.readme else OUT
    OUT = os.path.abspath(args.out or default_out)
    os.makedirs(OUT, exist_ok=True)

    app = App(Config())
    from zero_brother.levels.generate import levels_dir, generate_all

    d = levels_dir()
    if not os.path.exists(os.path.join(d, "level_1.json")):
        generate_all(d)

    if args.readme:
        _readme_set(app, d)
    else:
        _full_set(app, d)

    pygame.quit()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
