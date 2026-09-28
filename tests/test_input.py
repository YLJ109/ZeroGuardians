"""输入系统测试 (GDD §7, M1)。"""
import os

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


def test_save_creates_missing_parent_dir(tmp_path):
    """全新 clone 里 config/ 并不存在（git 不跟踪空目录），首跑必须能自己建目录。

    这是从「本地 clone 自检」里揪出来的真实 bug：旧实现直接 open(...,'w')，
    在干净仓库里会 FileNotFoundError，进而让 InputManager 初始化整体失败。
    """
    p = str(tmp_path / "config" / "input.json")
    assert not os.path.isdir(os.path.dirname(p))
    save_input_config(p, load_input_config(None))
    assert os.path.exists(p)
    assert len(load_input_config(p)["slots"]) == 4


def test_manager_bootstraps_config_when_absent(tmp_path):
    """把键位路径指向一个不存在的目录，模拟「刚 clone 下来」的首次运行。

    用子类覆写 _input_path 而不是 monkeypatch —— tests/run.py 是不依赖 pytest 的
    极简运行器，注入不了 fixture。
    """
    from zero_brother.input.manager import InputManager

    target = tmp_path / "nested" / "config" / "input.json"

    class _Bootstrap(InputManager):
        def _input_path(self):
            return str(target)

    im = _Bootstrap(Config.load())
    assert target.exists(), "首跑应自动写出默认键位"
    assert im.n == 4
