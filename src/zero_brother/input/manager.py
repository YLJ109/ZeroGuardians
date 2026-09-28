"""输入管理器 (GDD §7 输入系统落地，M1)。

- 键盘：基于事件维护按下键集，按键按 §7.6 ② **广播**到所有绑定了该键的 Slot
  （不同 Slot 允许共用同一键，例如 P1 与 P3 共用 J/K）。
- 手柄：每帧读取 Joystick 状态（§7.5），与键盘结果合并；热插拔不崩（§7.5）。
- 每帧计算 held（持续）与 pressed（边沿=本帧刚按下），逻辑层只消费 Action。
"""
from __future__ import annotations

import os
from typing import Iterable

import pygame

from .actions import Action
from .mapping import load_input_config, save_input_config, parse_source
from .device import GamepadReader


class InputManager:
    def __init__(self, config, resources=None):
        self.cfg = config
        self.resources = resources
        path = self._input_path()
        if not os.path.exists(path):
            # 首次运行：写出默认键位，满足"持久化"要求（§7.6）
            save_input_config(path, load_input_config(None))
        data = load_input_config(path)
        self.slots = data["slots"]
        for s in self.slots:
            s["parsed"] = {
                Action(a): [parse_source(x) for x in srcs]
                for a, srcs in s["bindings"].items()
            }
        self.n = len(self.slots)

        # 键盘广播表：键码 -> [(slot_idx, action), ...]
        self._key_map: dict[int, list[tuple]] = {}
        for si, s in enumerate(self.slots):
            for action, srcs in s["parsed"].items():
                for src in srcs:
                    if src[0] == "key":
                        self._key_map.setdefault(src[1], []).append((si, action))

        self._key_down: set[int] = set()
        self._held: list[set] = [set() for _ in range(self.n)]
        self._prev: list[set] = [set() for _ in range(self.n)]
        self._pressed: list[set] = [set() for _ in range(self.n)]

        self._gamepads: dict[int, tuple[int, GamepadReader]] = {}  # instance_id -> (slot, reader)
        self._init_gamepads()

    # ------------------------------------------------------------------
    def _input_path(self) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(here, "..", "..", "..", "config", "input.json"))

    def _init_gamepads(self) -> None:
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                self._open_joystick(i)
        except Exception:
            pass

    def _open_joystick(self, device_index: int) -> None:
        try:
            joy = pygame.joystick.Joystick(device_index)
            joy.init()
            slot = min(device_index, self.n - 1)
            reader = GamepadReader(joy, self.cfg.DEADZONE)
            self._gamepads[joy.get_instance_id()] = (slot, reader)
        except Exception:
            pass

    def _detach_gamepad(self, instance_id: int) -> None:
        self._gamepads.pop(instance_id, None)

    # ------------------------------------------------------------------
    def poll(self, events: Iterable) -> None:
        for e in events:
            if e.type == pygame.KEYDOWN:
                self._key_down.add(e.key)
            elif e.type == pygame.KEYUP:
                self._key_down.discard(e.key)
            elif e.type == pygame.JOYDEVICEADDED:
                self._open_joystick(getattr(e, "device_index", 0))
            elif e.type == pygame.JOYDEVICEREMOVED:
                self._detach_gamepad(getattr(e, "instance_id", -1))

        # 键盘 held（广播）
        kb = [set() for _ in range(self.n)]
        for keycode in self._key_down:
            for si, action in self._key_map.get(keycode, []):
                kb[si].add(action)

        # 手柄 held
        gp = [set() for _ in range(self.n)]
        for slot, reader in self._gamepads.values():
            gp[slot] |= reader.read()

        # 合并 + 边沿
        for i in range(self.n):
            new = kb[i] | gp[i]
            self._pressed[i] = new - self._prev[i]
            self._held[i] = new
            self._prev[i] = set(new)

    # ------------------------------------------------------------------
    def held(self, slot: int, action: Action) -> bool:
        return action in self._held[slot]

    def pressed(self, slot: int, action: Action) -> bool:
        return action in self._pressed[slot]

    def any_key_pressed(self) -> bool:
        return bool(self._key_down) or any(self._pressed)

    def slot_count(self) -> int:
        return self.n
