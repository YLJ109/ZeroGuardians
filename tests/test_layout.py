"""布局量宽回归测试：专治「字体超出自己的盒子」。

两类守护：
  A) 纯常量校验：用 gameplay 里的 BADGE_* 常量复算「关卡徽标」几何，
     对全部真实关卡名 + 边界名（空名 / 超长名）量真实墨迹，断言
     label 与 name 都落在盒内、且两行互不重叠。
  B) 集成校验：真实构造 GameplayScene、拦截 T.glass/T.text，
     调一次 _hud()，量实际画出来的文字墨迹是否落在它所在的玻璃盒内，
     并检查 _hud 画文字时用的偏移/字号确实等于 BADGE_* 常量（防漂移）。

运行：python tests/run.py  （本文件会被自动发现）
"""
import os
import glob
import json

from zero_brother.ui import theme as T
from zero_brother.scenes import gameplay as GP
from zero_brother.resources.manager import ResourceManager
from zero_brother.config import Config
from zero_brother.core.app import App
from zero_brother.world.level import load_level
from zero_brother.levels.generate import levels_dir


def _rm():
    return ResourceManager(Config.load())


def _ink(res, s, size):
    """返回 (ink_x, ink_y, ink_w, ink_h) 在「文字以 topleft=(0,0) blit」下的墨迹盒。"""
    if not s:
        return (0, 0, 0, 0)
    img = res.font(size).render(s, True, (255, 255, 255))
    bb = img.get_bounding_rect(min_alpha=1)
    return bb.x, bb.y, bb.width, bb.height


# ---------------------------------------------------------------------------
# A) 纯常量校验
# ---------------------------------------------------------------------------
def test_level_badge_text_fits_box_all_real_levels():
    res = _rm()
    d = levels_dir()
    names = []
    for p in sorted(glob.glob(os.path.join(d, "level_*.json"))):
        names.append(json.load(open(p, encoding="utf-8")).get("name", ""))
    # 边界用例：空名、超长名、带标点名
    names += ["", "试炼之始·终焉之门", "零之回响·终焉之战·再临", "A" * 12]

    for name in names:
        bw = max(176, res.font(GP.BADGE_NAME_SZ).size(name)[0] + 40)
        # 盒内坐标（左上角对齐到 0）
        lx, ly, lw, lh = _ink(res, f"第 9 关", GP.BADGE_LABEL_SZ)
        nx, ny, nw, nh = _ink(res, name, GP.BADGE_NAME_SZ)
        label_ink = (GP.BADGE_PAD_X + lx, GP.BADGE_LABEL_DY + ly, lw, lh)
        name_ink = (GP.BADGE_PAD_X + nx, GP.BADGE_NAME_DY + ny, nw, nh)
        box_w = bw
        box_h = GP.BADGE_H

        # 1) label 四边都在盒内（左右/上下各留 1px 余量）
        assert label_ink[0] >= 0, f"label 左越界: {name} {label_ink}"
        assert label_ink[1] >= 0, f"label 上越界: {name} {label_ink}"
        assert label_ink[0] + label_ink[2] <= box_w + 1, f"label 右越界: {name} {label_ink} box_w={box_w}"
        assert label_ink[1] + label_ink[3] <= box_h + 1, f"label 下越界: {name} {label_ink} box_h={box_h}"

        # 2) name 四边都在盒内（空名直接跳过）
        if name:
            assert name_ink[0] >= 0, f"name 左越界: {name!r} {name_ink}"
            assert name_ink[1] >= 0, f"name 上越界: {name!r} {name_ink}"
            assert name_ink[0] + name_ink[2] <= box_w + 1, f"name 右越界: {name!r} {name_ink} box_w={box_w}"
            assert name_ink[1] + name_ink[3] <= box_h + 1, f"name 下越界: {name!r} {name_ink} box_h={box_h}"

        # 3) 两行墨迹互不重叠（盒内坐标，留 0 容差为「不可交叠」）
        ix = max(label_ink[0], name_ink[0]); iy = max(label_ink[1], name_ink[1])
        ix2 = min(label_ink[0] + label_ink[2], name_ink[0] + name_ink[2])
        iy2 = min(label_ink[1] + label_ink[3], name_ink[1] + name_ink[3])
        if name:  # 空名无 name 墨迹，谈不上重叠
            assert not (ix2 > ix and iy2 > iy), f"label/name 重叠: {name!r} label={label_ink} name={name_ink}"


# ---------------------------------------------------------------------------
# B) 集成校验：真渲染、量真实墨迹
# ---------------------------------------------------------------------------
def test_level_badge_rendered_text_fits_its_box():
    res = _rm()
    cfg = Config.load()
    app = App(cfg)
    d = levels_dir()
    lvl = load_level(os.path.join(d, "level_1.json"))  # 翠谷启程
    scene = GP.GameplayScene(app, lvl, [(0, "archer")])

    glasses = []   # (x, y, w, h, kind)
    texts = []     # (s, size, topleft)

    _org_glass = T.glass
    _org_text = T.text

    def _rec_glass(surf, rect, *a, **k):
        r = __import__("pygame").Rect(rect)
        glasses.append((r.x, r.y, r.w, r.h, "glass"))
        return _org_glass(surf, rect, *a, **k)

    def _rec_text(surf, r, s, size, color, topleft=None, center=None, **k):
        if topleft is not None:
            texts.append((s, size, topleft))
        return _org_text(surf, r, s, size, color, topleft=topleft, center=center, **k)

    T.glass = _rec_glass
    T.text = _rec_text
    try:
        scene._hud()
    finally:
        T.glass = _org_glass
        T.text = _org_text

    # 找到关卡徽标：宽 176、高 BADGE_H、位于右上（x 较大）的玻璃盒
    badge = None
    for (x, y, w, h, kind) in glasses:
        if kind == "glass" and h == GP.BADGE_H and w >= 176 and x > cfg.LOGIC_W // 2:
            badge = (x, y, w, h)
            break
    assert badge is not None, "未捕获到关卡徽标玻璃盒"

    # 找出徽标内的两行文字（文字中心落在盒内即归属该盒）
    bx, by, bw, bh = badge
    label_draw = None
    name_draw = None
    for (s, size, tl) in texts:
        w, h = res.font(size).size(s)
        cx, cy = tl[0] + w / 2, tl[1] + h / 2
        if not (bx <= cx <= bx + bw and by <= cy <= by + bh):
            continue
        if size == GP.BADGE_LABEL_SZ:
            label_draw = (s, size, tl)
        elif size == GP.BADGE_NAME_SZ:
            name_draw = (s, size, tl)

    assert label_draw is not None, "徽标内未找到 label 文字"
    assert name_draw is not None, "徽标内未找到 name 文字"

    # 真实墨迹相对盒子的位置
    def _ink_in_box(draw):
        s, size, (tx, ty) = draw
        ix, iy, iw, ih = _ink(res, s, size)
        return (tx + ix - bx, ty + iy - by, iw, ih)

    li = _ink_in_box(label_draw)
    ni = _ink_in_box(name_draw)
    assert li[0] >= -1 and li[1] >= -1 and li[0] + li[2] <= bw + 1 and li[1] + li[3] <= bh + 1, \
        f"渲染后 label 墨迹越出徽标: {li} box={badge}"
    assert ni[0] >= -1 and ni[1] >= -1 and ni[0] + ni[2] <= bw + 1 and ni[1] + ni[3] <= bh + 1, \
        f"渲染后 name 墨迹越出徽标: {ni} box={badge}"

    # 防漂移：_hud 实际画的偏移/字号必须等于 BADGE_* 常量
    (_, _, (lx, ly)) = label_draw
    (_, _, (nx, ny)) = name_draw
    assert (lx - bx, ly - by) == (GP.BADGE_PAD_X, GP.BADGE_LABEL_DY), \
        f"_hud label 偏移漂移: {(lx-bx, ly-by)} != {(GP.BADGE_PAD_X, GP.BADGE_LABEL_DY)}"
    assert (nx - bx, ny - by) == (GP.BADGE_PAD_X, GP.BADGE_NAME_DY), \
        f"_hud name 偏移漂移: {(nx-bx, ny-by)} != {(GP.BADGE_PAD_X, GP.BADGE_NAME_DY)}"
