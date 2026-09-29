"""选人界面（1-4 人）交互测试。

真事故（玩家报障："选英雄界面有点暗，三人和四人无法选"）：
  ① 压暗层顶部 alpha 198 + vignette 110 —— 卡面上的名字/定位/技能几乎看不见；
  ② 人数胶囊只有键盘 1/2/3/4 一条通路，鼠标点击没有任何处理 ——
     点上去毫无反应，"3 人 / 4 人"在鼠标操作下等于不存在；
  ③ P4 默认绑定的是小键盘（K_KP4/6/8/5/7/9），笔记本没有小键盘时
     永远无法"准备" → 四人流程根本走不到选关。
下面这组用例把这三条钉死，并守住"卡面文案不得超出卡片"。
"""
import json

import pygame

from zero_brother.config import Config
from zero_brother.heroes.registry import HERO_ORDER, hero as hero_def
from zero_brother.input.mapping import DEFAULT_SLOTS, load_input_config
from zero_brother.levels.generate import generate_all, levels_dir
from zero_brother.scenes.select import (
    CharacterSelectScene, CARD_W, CARD_H, CARD_GAP, CARD_Y, CARD_PAD,
    GEM_ICON, GEM_ICON_PAD, GEM_ROW_GAP, gem_row_text,
    PILL_W, PILL_H, PILL_Y, PILL_STEP, PILL_LEFT,
)

LEVELS = levels_dir()
_APP = {}


def _app_cfg():
    """整个模块共用一个 App —— 每个用例都新建会白白重复初始化音频/资源。"""
    if "app" not in _APP:
        from zero_brother.core.app import App
        cfg = Config.load()
        app = App(cfg)
        _APP["app"], _APP["cfg"] = app, cfg
    return _APP["app"], _APP["cfg"]


def _select_scene():
    """新建一个选人场景（共享 App，状态互不干扰）。"""
    generate_all(LEVELS)
    app, cfg = _app_cfg()
    sc = CharacterSelectScene(app)
    app.scenes.switch(sc)
    return sc, cfg


def _click(sc, pos):
    sc.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0),
                                      buttons=(0, 0, 0)))
    sc.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def _keydown(sc, code):
    sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code, unicode="", mod=0))


def _press(app, sc, code):
    app.input.poll([pygame.event.Event(pygame.KEYDOWN, key=code)])
    sc.fixed_update(1 / 60)
    app.input.poll([pygame.event.Event(pygame.KEYUP, key=code)])


# ---------------------------------------------------------------------------
# ① 亮度
# ---------------------------------------------------------------------------
def test_hero_select_is_not_too_dark():
    """压暗层不得过重 —— 旧值顶部 alpha=198 让卡面文字基本不可读。"""
    sc, cfg = _select_scene()
    sc.render(0)
    assert sc._dim is not None, "选人界面应有一层压暗遮罩"
    top = sc._dim.get_at((10, 10))[3]
    bottom = sc._dim.get_at((10, cfg.LOGIC_H - 1))[3]
    assert top <= 150, f"选人界面顶部压暗过重: alpha={top}"
    assert bottom <= 110, f"选人界面底部压暗过重: alpha={bottom}"
    assert top > bottom, "压暗应为自上而下的渐变"


# ---------------------------------------------------------------------------
# ② 人数胶囊鼠标可点
# ---------------------------------------------------------------------------
def test_human_count_pills_are_hit_testable_and_clickable():
    """渲染位置与命中测试必须来自同一份几何 —— 否则点上去会整体偏一格。"""
    sc, cfg = _select_scene()
    for i in range(4):
        r = sc._pill_rect(i)
        assert r.w == PILL_W and r.h == PILL_H, "胶囊命中盒尺寸应与绘制一致"
        assert r.centery == PILL_Y, "胶囊命中盒应与绘制在同一行"
        assert r.centerx == cfg.LOGIC_W // 2 + PILL_LEFT + i * PILL_STEP
        assert sc._hero_hit(r.center) == ("pill", i)


def test_clicking_pills_selects_up_to_four_players():
    """鼠标点「3 人」「4 人」必须真的改人数（旧实现点击无任何反应）。"""
    sc, _ = _select_scene()
    sc.count = 2
    _click(sc, sc._pill_rect(2).center)
    assert sc.count == 3, "点「3 人」应把人数设为 3"
    _click(sc, sc._pill_rect(3).center)
    assert sc.count == 4, "点「4 人」应把人数设为 4"
    _click(sc, sc._pill_rect(0).center)
    assert sc.count == 1, "点「1 人」应把人数设为 1"


def test_changing_count_clears_previous_ready_flags():
    sc, _ = _select_scene()
    sc.count = 4
    sc.ready = [True] * 4
    _click(sc, sc._pill_rect(0).center)
    assert sc.count == 1
    assert sc.ready == [False] * 4, "改人数后旧的「已准备」必须作废"


# ---------------------------------------------------------------------------
# ② 英雄卡鼠标可点（加入 / 准备 / 取消准备）
# ---------------------------------------------------------------------------
def test_clicking_hero_card_toggles_ready_for_joined_players():
    sc, _ = _select_scene()
    sc.count = 4
    for i in range(4):
        _click(sc, sc._card_rect(i).center)
        assert sc.ready[i] is True, f"点击玩家 {i + 1} 卡片应就绪"
    _click(sc, sc._card_rect(0).center)
    assert sc.ready[0] is False, "再点一次应取消准备"


def test_clicking_unjoined_card_joins_that_player():
    """人数=2 时点「玩家 4」的卡片 = 让 P4 加入，而不是什么都不发生。"""
    sc, _ = _select_scene()
    sc.count = 2
    sc.ready = [False] * 4
    _click(sc, sc._card_rect(3).center)
    assert sc.count == 4, "点未加入的卡片应把人数扩到该槽位"
    assert sc.ready[3] is True, "加入时应顺手就绪（少点一次）"
    assert sc.ready[:3] == [False, False, False], "不应连带把别人标成就绪"


def test_mouse_alone_can_finish_hero_phase():
    """全鼠标操作：点 4 人 → 点 4 张卡 → 自动进入选关阶段。"""
    sc, _ = _select_scene()
    _click(sc, sc._pill_rect(3).center)
    for i in range(4):
        _click(sc, sc._card_rect(i).center)
    assert all(sc.ready[:4]), f"四张卡片点击后应全部就绪: {sc.ready}"
    sc.fixed_update(1 / 60)
    sc.fixed_update(1.0)          # 跨过 0.4s 门槛
    assert sc.phase == "level", f"应进入选关阶段: {sc.phase}"


def test_card_hit_test_matches_drawn_geometry():
    sc, cfg = _select_scene()
    r = sc._card_rect(0)
    assert (r.w, r.h, r.y) == (CARD_W, CARD_H, CARD_Y)
    total = CARD_W * 4 + CARD_GAP * 3
    assert r.x == (cfg.LOGIC_W - total) // 2, "首张卡片应水平居中排布"
    for i in range(4):
        assert sc._hero_hit(sc._card_rect(i).center) == ("card", i)


# ---------------------------------------------------------------------------
# ③ 没有小键盘也能四人同屏
# ---------------------------------------------------------------------------
def test_fourth_slot_ships_a_numpad_free_fallback():
    """P4 主键位是小键盘（同屏惯例），但必须同时挂一个普通键兜底。"""
    p4 = DEFAULT_SLOTS[3]["bindings"]
    for act, keys in p4.items():
        assert any(not k.startswith("K_KP") for k in keys), \
            f"P4 的 {act} 缺少无小键盘后备键: {keys}"


def test_old_config_without_fallback_keys_is_healed_on_load(tmp_path):
    """老版本写出的 input.json（P4 只有小键盘）在载入时自动补上后备键。

    否则玩家唯一的解法是手动删配置文件，这不可接受。
    """
    old = {"slots": [dict(s) for s in DEFAULT_SLOTS]}
    old["slots"][3]["bindings"] = {
        "MOVE_LEFT": ["K_KP4"], "MOVE_RIGHT": ["K_KP6"], "JUMP": ["K_KP8"],
        "CROUCH": ["K_KP5"], "SKILL_A": ["K_KP7"], "SKILL_B": ["K_KP9"],
    }
    p = tmp_path / "input.json"
    p.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")

    data = load_input_config(str(p))
    jump = data["slots"][3]["bindings"]["JUMP"]
    assert "K_KP8" in jump, "原有键位不能被删掉"
    assert any(not k.startswith("K_KP") for k in jump), \
        f"载入老配置时应补上后备跳键: {jump}"
    # 补进来之后仍然满足"必填动作不重复绑定"
    assert len(jump) == len(set(jump)), f"后备键不应与已有键重复: {jump}"


def test_four_players_can_ready_without_a_numpad():
    """真实链路：4 名玩家用各自绑定的跳键就绪，P4 走"没有小键盘"的备用键。"""
    sc, _ = _select_scene()
    app = sc.app
    sc.count = 4
    sc.ready = [False] * 4
    # P1..P3 用各自默认跳键，P4 故意用非小键盘的后备键
    for slot, code in enumerate((pygame.K_w, pygame.K_UP, pygame.K_i, pygame.K_SLASH)):
        binding = app.input.slots[slot]["bindings"]["JUMP"]
        if code == pygame.K_SLASH:
            assert "K_SLASH" in binding, f"P4 应绑定后备跳键: {binding}"
        _press(app, sc, code)
    assert all(sc.ready[:4]), f"无小键盘时四人也必须能就绪: {sc.ready}"
    sc.fixed_update(1 / 60)
    sc.fixed_update(1.0)
    assert sc.phase == "level"


def test_ready_slot_locks_its_hero():
    """已准备的槽位锁定英雄。

    P1 的技能键 J 同时是 P3 的 MOVE_LEFT（§7.6 ② 同屏共用键是设计如此），
    不锁的话 P1 一按 J 就会把 P3 选好的英雄转走。
    """
    sc, _ = _select_scene()
    app = sc.app
    sc.count = 3
    sc.ready = [False] * 3
    _press(app, sc, pygame.K_i)              # P3 用 JUMP 就绪
    assert sc.ready[2] is True
    p3_hero = sc.heroes[2]
    _press(app, sc, pygame.K_j)              # P1 用 SKILL_A 就绪（= P3 的 MOVE_LEFT）
    assert sc.ready[0] is True, "P1 按 J 应就绪"
    assert sc.heroes[2] == p3_hero, "已准备的 P3 英雄不应被 P1 的技能键转走"
    assert sc.ready[2] is True, "已准备的 P3 不应被顺带清掉"
    # 取消准备后（P3 再按一次 JUMP）又可以换英雄
    _press(app, sc, pygame.K_i)
    assert sc.ready[2] is False
    _press(app, sc, pygame.K_l)              # P3 的 MOVE_RIGHT
    assert sc.heroes[2] != p3_hero, "取消准备后应能继续换英雄"


def test_card_hint_names_the_real_ready_key():
    """卡片上必须写出该玩家的真实就绪键（4 人同屏时每人的键都不一样）。"""
    sc, _ = _select_scene()
    app = sc.app
    assert sc._key_label(0) == "W"
    assert sc._key_label(1) == "↑"
    assert sc._key_label(2) == "I"
    p4 = sc._key_label(3)
    assert "小键盘8" in p4 and "/" in p4, f"P4 应同时写明主键与后备键: {p4}"
    # 手柄/无绑定槽位不能崩，也不能显示空串
    assert sc._key_label(9) == "跳"


# ---------------------------------------------------------------------------
# 文案不出框（历史上出现过"字体太大超出盒子"）
# ---------------------------------------------------------------------------
def test_card_text_fits_inside_the_card():
    sc, _ = _select_scene()
    sc.count = 4
    f20 = sc.app.resources.font(20)
    f18 = sc.app.resources.font(18)
    f17 = sc.app.resources.font(17)
    inner = CARD_W - 40          # 卡内左右各留 20px
    for slot in range(4):
        pill = f"准备中 · {sc._key_label(slot)}"
        assert f20.size(pill)[0] <= inner, f"P{slot + 1} 状态胶囊文案过宽: {pill}"
        for hint in ("←→ 换英雄 · 也可点卡片准备", "已锁定 · 再按一次取消准备"):
            assert f17.size(hint)[0] <= inner, f"P{slot + 1} 底部提示过宽: {hint}"


def test_affinity_row_fits_inside_the_card():
    """亲和行必须落在卡内留白里。

    真事故：单行「亲和 绿宝石 · 同色 +1 奖励」18px 下宽 290px，加上宝石图标
    316px > 卡内可用 282px —— 文案顶到卡边、右段被裁掉。拆成左右两段后最宽 231px。
    """
    sc, _ = _select_scene()
    f18 = sc.app.resources.font(18)
    inner = CARD_W - 2 * CARD_PAD
    icon_budget = GEM_ICON + GEM_ICON_PAD
    for hero_id in HERO_ORDER:
        left, right = gem_row_text(hero_def(hero_id)["gem"])
        need = icon_budget + f18.size(left)[0] + GEM_ROW_GAP + f18.size(right)[0]
        assert need <= inner, f"{hero_id} 亲和行过宽: {need} > {inner}"


def test_affinity_row_names_both_the_colour_and_the_bonus():
    """亲和只影响奖励、不构成门槛 —— 文案必须同时说清"什么颜色"和"加什么"。"""
    assert gem_row_text("green") == ("亲和 绿宝石", "同色 +1")
    assert gem_row_text("yellow") == ("亲和 黄宝石", "同色 +1")
    assert gem_row_text("any") == ("亲和 任意宝石", "全色 +1")


def test_hero_select_renders_without_resource_errors():
    """整页渲染（含 4 人 + 悬停高亮 + 未加入卡片）不得抛异常。"""
    sc, _ = _select_scene()
    sc.count = 4
    sc.hover = ("pill", 3)
    sc.render(0)
    sc.hover = ("card", 0)
    sc.render(0)
    sc.count = 1
    sc.hover = None
    sc.render(0)
    assert True
