#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无 pytest 依赖的测试运行器（CI / 无显示器环境也能跑）。

用法： python tests/run.py
等价于 pytest，但自带极简发现与执行，输出 PASS/FAIL 汇总。
"""
import os
import sys
import importlib
import inspect
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
pygame.init()

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "src"))


def _call(fn):
    sig = inspect.signature(fn)
    kwargs = {}
    if "tmp_path" in sig.parameters:
        kwargs["tmp_path"] = Path(tempfile.mkdtemp(prefix="zb_test_"))
    fn(**kwargs)


passed, failed = 0, 0
for fn in sorted(os.listdir(_HERE)):
    if not (fn.startswith("test_") and fn.endswith(".py")):
        continue
    mod = importlib.import_module(fn[:-3])
    for name in dir(mod):
        if name.startswith("test_") and callable(getattr(mod, name)):
            try:
                _call(getattr(mod, name))
                print(f"  PASS  {fn[:-3]}.{name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {fn[:-3]}.{name} -> {e}")
                traceback.print_exc()
                failed += 1

print(f"\n总计：{passed} 通过 / {failed} 失败")
sys.exit(1 if failed else 0)
