#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 UI 字体的字符集文件，并（可选）调用 fontTools 做子集化。

为什么需要它：assets/vendor/noto_sans_sc/NotoSansSC-Regular.otf 是从完整
Noto Sans SC（8.3 MB）子集化来的。子集字符集 = 全项目源码里出现过的所有
字符 ∪ GB2312 一级汉字 ∪ ASCII ∪ 常用 CJK 标点。扫描源码是为了保证「新增
文案不会缺字」，加入 GB2312 一级是为了「未来新增文案也不会缺字」。

用法：
    # 1) 只用标准库生成字符集文件
    python tools/build_font_subset.py --chars-only -o subset_chars.txt

    # 2) 完整流程（需要先把 fontTools 装进隔离目录）
    pip install --target .fonttools fonttools
    set PYTHONPATH=.fonttools
    python tools/build_font_subset.py \
        --src NotoSansSC-Regular.otf \
        --out assets/vendor/noto_sans_sc/NotoSansSC-Regular.otf
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXTRA_SYMBOLS = (
    "，。、；：？！「」『』（）《》〈〉—…·　→←↑↓★☆●○◆◇✓✔×÷±≈≤≥“”‘’～％＆＃＠"
    "─│┌┐└┘█▌▐░▒▓■□▲▼◀▶"
)
EXTRA_LATIN = "áàâäéèêëíìîïóòôöúùûüñçÁÀÂÄÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÑÇ"


def collect_chars(scan_dirs=("src", "main.py", "tools")) -> set[str]:
    chars: set[str] = set()
    for rel in scan_dirs:
        path = os.path.join(ROOT, rel)
        if os.path.isfile(path):
            files = [path]
        else:
            files = glob.glob(os.path.join(path, "**", "*.py"), recursive=True)
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    chars |= set(fh.read())
            except (OSError, UnicodeDecodeError):
                pass
    chars |= {chr(c) for c in range(0x20, 0x7F)}     # ASCII 可打印
    chars |= _gb2312_level1()
    chars |= set(EXTRA_SYMBOLS) | set(EXTRA_LATIN)
    return {c for c in chars if ord(c) > 32}


def _gb2312_level1() -> set[str]:
    """GB2312 一级汉字（高频 3755 字，按拼音序）。"""
    out: set[str] = set()
    for hi in range(0xB0, 0xD8):
        for lo in range(0xA1, 0xFF):
            try:
                out.add(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chars-only", action="store_true", help="只生成字符集文件")
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "subset_chars.txt"))
    ap.add_argument("--src", help="输入字体（完整 Noto Sans SC）")
    ap.add_argument("--target", help="输出字体（子集化结果）")
    args = ap.parse_args()

    chars = collect_chars()
    text = "".join(sorted(chars))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    cjk = sum(1 for c in chars if ord(c) > 0x2E80)
    print(f"[chars] {len(chars)} 个字符（其中 CJK {cjk}）-> {args.out}")

    if args.chars_only:
        return 0
    if not args.src:
        print("[skip] 未提供 --src，仅生成字符集。", file=sys.stderr)
        return 0
    target = args.target or args.src.replace(".otf", ".subset.otf")
    cmd = [
        sys.executable, "-m", "fontTools.subset", args.src,
        f"--text-file={args.out}", f"--output-file={target}",
        "--layout-features=*", "--no-hinting", "--desubroutinize",
        "--name-IDs=*", "--name-legacy",
    ]
    print("[run]", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
