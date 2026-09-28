"""输入系统测试 (GDD §7, M1)。"""
import pygame

from zero_brother.config import Config
from zero_brother.input import (
    InputManager, Action, load_input_config, save_input_config,
    parse_source, format_source,
)


def test_default_four_slots():
    data = load_input_config(None)
    assert len(data["slots"]) == 4


def test_required_filled():
    data = load_input_config(None)
    for s in data["slots"]:
        for a in ("MOVE_LEFT", "MOVE_RIGHT", "JUMP"):
            assert a in s["bindings"], f"slot missing {a}"


def test_source_roundtrip():
    for s in ["K_a", "K_LEFT", "btn:0", "axis:0:neg", "axis:0:pos", "hat:0:x:pos", "trig:5"]:
        assert format_source(parse_source(s)) == s, s


def test_manager_broadcast():
    """K_j 同时绑定 P1.SKILL_A 与 P3.MOVE_LEFT → 广播到两个 Slot（§7.6 ②）。"""
    im = InputManager(Config.load())
    im.poll([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)])
    assert im.held(0, Action.SKILL_A)
    assert im.held(2, Action.MOVE_LEFT)
    assert im.pressed(0, Action.SKILL_A)
    im.poll([pygame.event.Event(pygame.KEYUP, key=pygame.K_j)])
    assert not im.held(0, Action.SKILL_A)
    assert not im.pressed(0, Action.SKILL_A)


def test_edge_detection():
    im = InputManager(Config.load())
    im.poll([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)])
    assert im.pressed(0, Action.MOVE_LEFT)      # 本帧刚按下
    im.poll([])                                  # 下一帧无新事件
    assert not im.pressed(0, Action.MOVE_LEFT)   # 边沿消失，仍 held
    assert im.held(0, Action.MOVE_LEFT)


def test_save_load_roundtrip(tmp_path):
    p = str(tmp_path / "input.json")
    data = load_input_config(None)
    save_input_config(p, data)
    data2 = load_input_config(p)
    assert data2["slots"][0]["bindings"]["JUMP"] == data["slots"][0]["bindings"]["JUMP"]
    assert data2["slots"][3]["device"] == "keyboard"
