"""输入设备读取 (GDD §7.5 手柄规格)。

键盘在 InputManager 内基于事件维护；本模块负责手柄（pygame.joystick）：
  - 左摇杆 X / 十字键 → MOVE_LEFT/RIGHT
  - 左摇杆 Y 向下 / RT 扳机 → CROUCH
  - A/X/B/Y/Start → JUMP / SKILL_A / SKILL_B / SWAP / PAUSE
  - 死区 DEADZONE，热插拔由 InputManager 负责
"""
from __future__ import annotations

from typing import Iterable

import pygame

from .actions import Action


# 手柄默认映射（§7.5）
DEFAULT_GAMEPAD: dict[Action, list[tuple]] = {
    Action.MOVE_LEFT: [("axis", 0, -1), ("hat", 0, "x", -1)],
    Action.MOVE_RIGHT: [("axis", 0, 1), ("hat", 0, "x", 1)],
    Action.CROUCH: [("axis", 1, 1), ("trig", 5)],
    Action.JUMP: [("btn", 0)],
    Action.SKILL_A: [("btn", 2)],
    Action.SKILL_B: [("btn", 1)],
    Action.SWAP: [("btn", 3)],
    Action.PAUSE: [("btn", 9)],
}


class GamepadReader:
    """把一只 Joystick 的当前状态翻译成 Action 集合。"""

    def __init__(self, joystick: "pygame.joystick.Joystick", deadzone: float,
                 binding: dict[Action, list[tuple]] | None = None):
        self.joy = joystick
        self.deadzone = deadzone
        self.binding = binding or DEFAULT_GAMEPAD

    def read(self) -> set[Action]:
        held: set[Action] = set()
        for action, sources in self.binding.items():
            for src in sources:
                if self._source_active(src):
                    held.add(action)
                    break
        return held

    # ------------------------------------------------------------------
    def _source_active(self, src: tuple) -> bool:
        kind = src[0]
        if kind == "btn":
            return bool(self.joy.get_button(src[1]))
        if kind == "trig":
            try:
                return self.joy.get_axis(src[1]) > self.deadzone
            except Exception:
                return False
        if kind == "axis":
            idx, sign = src[1], src[2]
            try:
                val = self.joy.get_axis(idx)
            except Exception:
                return False
            if sign == 0:
                return abs(val) > self.deadzone
            return sign * val > self.deadzone
        if kind == "hat":
            idx, axis, sign = src[1], src[2], src[3]
            try:
                hx, hy = self.joy.get_hat(idx)
            except Exception:
                return False
            val = hx if axis == "x" else hy
            return sign * val > 0  # 帽子是离散 ±1
        return False
