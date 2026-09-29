#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无头「键位冒烟」：在真实 App + GameplayScene 里把技能键都按一遍并逐帧渲染。

为什么需要它（真事故）
----------------------
v0.6 发布后，玩家进关按 K（弓箭手·远跳）直接崩：

    AttributeError: 'Player' object has no attribute 'grounded'

当时测试对 skills 零覆盖；而 ``main.py --headless --frames N`` **只跑开场 splash，
既不进关也不按键**，所以这个洞一路漏到了玩家手上。

本工具走**真实场景路径**：普通关 / 立体关 / 三个 Boss 关都进，6 个英雄各自在
地面与空中把 skill_a / skill_b 键按一遍，随后再跑一段「按住右 + 周期跳跃」，
全程逐帧 ``render()`` —— 任何属性错、渲染错、Boss 关逻辑错都会立刻抛出来。

用法：
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/play_smoke.py
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/play_smoke.py --frames 4
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
from zero_brother.config import Config  # noqa: E402
from zero_brother.core.app import App  # noqa: E402
from zero_brother.heroes.registry import HERO_ORDER  # noqa: E402
from zero_brother.levels.generate import generate_all, levels_dir  # noqa: E402
from zero_brother.scenes.gameplay import GameplayScene  # noqa: E402
from zero_brother.world.level import load_level  # noqa: E402

LEVELS = levels_dir()
# 覆盖：普通关 / 带梯子弹簧的立体关 / 三个 Boss 关（stone / snow / purple 主题）
SAMPLE = ["level_1.json", "level_4.json", "level_5.json", "level_11.json", "level_15.json"]
# P1 默认键位：J / K 分别是 skill_a / skill_b
SKILL_KEYS = [("skill_a", pygame.K_j), ("skill_b", pygame.K_k)]
MOVE_KEYS = {"right": pygame.K_d, "jump": pygame.K_w}


def _key(code, down=True):
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=code)


def _tick(app, scene, frames, render=True):
    for _ in range(frames):
        scene.fixed_update(1 / 60)
        if render:
            scene.render(0)


def _press(app, scene, code, settle_frames):
    """按下一个键（产生帧边沿），跑若干帧并渲染，再抬起。"""
    app.input.poll([_key(code)])
    _tick(app, scene, settle_frames)
    app.input.poll([_key(code, down=False)])
    _tick(app, scene, 1)


def _put_in_air(player, dy=220):
    player.body.y -= dy
    player.body.vy = 0.0
    player.body.grounded = False
    player.air_jumps = player.max_air_jumps


def main(argv=None):
    parser = argparse.ArgumentParser(description="无头键位冒烟（进关 + 按键 + 渲染）")
    parser.add_argument("--frames", type=int, default=8,
                        help="每次释放技能后结算的帧数（默认 8）")
    args = parser.parse_args(argv)

    generate_all(LEVELS)
    app = App(Config.load())

    checks = 0
    for hero_id in HERO_ORDER:
        for lvl_name in SAMPLE:
            path = os.path.join(LEVELS, lvl_name)
            if not os.path.exists(path):
                print(f"  skip {lvl_name}（关卡文件不存在）")
                continue
            lvl = load_level(path)
            # 双人进场：顺带覆盖多人 HUD / 相机 / 事件队列
            scene = GameplayScene(app, lvl, [(0, hero_id), (1, "builder")])
            app.scenes.switch(scene)
            world = scene.world
            p = world.players[0]

            _tick(app, scene, 45)                      # 先落到地面站稳

            for airborne in (False, True):
                if airborne:
                    _put_in_air(p)
                for skill_name, code in SKILL_KEYS:
                    for k in p.cooldowns:              # 清冷却，确保技能体真的执行
                        p.cooldowns[k] = 0.0
                    _press(app, scene, code, args.frames)
                    checks += 1
                    print(f"  ok  {hero_id:8s} {lvl_name:14s} "
                          f"air={str(airborne):5s} {skill_name}")

            # 再跑一段正常操作：按住右 + 周期跳跃（覆盖走/跳/碰撞/HUD 推进）
            app.input.poll([_key(MOVE_KEYS["right"])])
            for i in range(90):
                if i % 30 == 0:
                    app.input.poll([_key(MOVE_KEYS["right"]), _key(MOVE_KEYS["jump"])])
                elif i % 30 == 8:
                    app.input.poll([_key(MOVE_KEYS["right"]), _key(MOVE_KEYS["jump"], down=False)])
                _tick(app, scene, 1)
            app.input.poll([_key(MOVE_KEYS["right"], down=False)])
            _tick(app, scene, 1)

    pygame.quit()
    print(f"\n键位冒烟完成：{checks} 次技能释放 + {len(HERO_ORDER) * len(SAMPLE)} 段"
          f"常规操作，全部无异常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
