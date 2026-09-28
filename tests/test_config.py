"""配置系统测试 (GDD §12 / §9)。"""
from zero_brother.config import Config, DEFAULTS


def test_defaults_loaded():
    c = Config.load()
    assert c.LOGIC_W == 1600
    assert c.LOGIC_H == 900
    assert c.JUMP_VELOCITY == -684
    assert c.PLAYER_HITBOX == (44, 56)
    assert c.BUILD_GAP_MIN_ROWS == 5


def test_override(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text('{"LOGIC_W": 1280, "SPLASH": {"font_size": 200}}')
    c = Config.load(str(p))
    assert c.LOGIC_W == 1280            # 覆盖生效
    assert c.SPLASH["font_size"] == 200
    assert c.JUMP_VELOCITY == -684      # 其余保持默认
