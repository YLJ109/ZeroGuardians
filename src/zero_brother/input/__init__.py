"""输入子包：Action 抽象、键位映射、键盘/手柄设备、管理器。"""
from .actions import Action, ALL_ACTIONS, REQUIRED_ACTIONS
from .mapping import load_input_config, save_input_config, parse_source, format_source
from .device import GamepadReader, DEFAULT_GAMEPAD
from .manager import InputManager

__all__ = [
    "Action", "ALL_ACTIONS", "REQUIRED_ACTIONS",
    "load_input_config", "save_input_config", "parse_source", "format_source",
    "GamepadReader", "DEFAULT_GAMEPAD", "InputManager",
]
