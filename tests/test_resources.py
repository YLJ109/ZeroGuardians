"""资源加载器测试 (GDD §19.1 B3 / B1)。"""
import os

import pygame

from zero_brother.config import Config
from zero_brother.resources import ResourceManager, is_licensed


def test_case_insensitive_resolve(tmp_path):
    """逻辑路径 img/foo.png 应能解析到磁盘上的 Img/Foo.PNG（大小写不敏感，B3）。"""
    d = tmp_path / "Img"
    d.mkdir()
    (d / "Foo.PNG").write_bytes(b"\x89PNG\r\n\x1a\n")
    rm = ResourceManager(Config.load(), assets_root=str(tmp_path))
    resolved = rm._resolve_file("img/foo.png")
    assert resolved is not None
    assert resolved.replace("\\", "/").lower().endswith("img/foo.png")


def test_font_fallback_no_crash():
    """字体解析失败应回退内置默认字体，冷启动不崩（B1 根治）。"""
    rm = ResourceManager(Config.load(), assets_root="/nonexistent_path_xyz")
    f = rm.font(24)  # 不抛异常
    assert f is not None
    assert isinstance(f, pygame.font.Font)


def test_license_classification():
    assert is_licensed("vendor/kenney_new_platformer/foo.png")
    assert not is_licensed("img/unknown.png")
