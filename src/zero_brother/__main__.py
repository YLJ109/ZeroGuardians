"""支持 `python -m zero_brother`（需把 src 加入 PYTHONPATH）。"""
import os
import sys

if __package__ in (None, ""):
    # 直接以脚本方式运行时，把 src 加入搜索路径
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from zero_brother import main

if __name__ == "__main__":
    main()
