"""素材许可清单 (GDD §19.1 B3 / §13 / Q6)。

职责：
  - 记录哪些素材目录已确认授权（CC0 / OFL），哪些仍是"未知许可"需替换。
  - 加载时若命中未知许可资产，记录告警（不崩溃），待 M0 后逐步替换。

这是 Q6（分发合规）的结构化落地：白名单之外的资产不允许进最终包。
"""
from __future__ import annotations

# 已确认授权的供应商 / 目录
LICENSE_WHITELIST = {
    "vendor/kenney_new_platformer": "CC0 1.0 (public domain)",
    "vendor/kenney_interface_sounds": "CC0 1.0 (public domain)",
    "vendor/noto_sans_sc": "SIL Open Font License 1.1 (OFL)",   # Q6 已闭合
}

# 已知来源但许可未知的旧资产（必须替换 / 登记后才可分发）
UNKNOWN_LICENSE = {
    "img/", "wav/", "video/",  # 旧工程素材，来源不明
    "font/",                    # 旧占位字体 datouren（非 OFL），已被 vendor/noto_sans_sc 取代
}

# 字体回退链：项目自带 OFL 字体优先，其次是各平台常见的**中文字体**系统路径。
# 注意 pygame 2.6.1 下 SysFont 会抛异常（GDD §19.1 B1），因此这里只列具体文件路径。
KNOWN_FONTS = [
    # Windows
    "C:/Windows/Fonts/NotoSansSC-VF.ttf",
    "C:/Windows/Fonts/SourceHanSansSC-Regular.otf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/Deng.ttf",
    "C:/Windows/Fonts/simhei.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
    # 最后：无中文能力的通用字体（保证不崩，可能显示豆腐块）
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def license_of(rel_path: str) -> str:
    """返回某相对路径的许可状态描述。"""
    low = rel_path.lower().replace("\\", "/")
    for prefix, lic in LICENSE_WHITELIST.items():
        if low.startswith(prefix):
            return lic
    for prefix in UNKNOWN_LICENSE:
        if low.startswith(prefix):
            return "UNKNOWN — 需替换/登记"
    return "UNKNOWN — 不在清单"


def is_licensed(rel_path: str) -> bool:
    return license_of(rel_path).startswith(("CC0", "OFL", "SIL"))
