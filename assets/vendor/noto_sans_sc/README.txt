Noto Sans SC (思源黑体 / Source Han Sans 同源) — 简体中文常规字重
========================================================================

用途
----
《零零守护者》的默认 UI / HUD 字体。此前 assets/font/font.ttf 是来源不明的
占位字体（datouren，非 OFL），中文度量不均、排版拥挤，是 Q6 合规与画质的
共同短板。这里换成真正可自由分发的 OFL 字体。

来源
----
上游仓库  : https://github.com/googlefonts/noto-cjk
上游文件  : Sans/SubsetOTF/SC/NotoSansSC-Regular.otf  (8.3 MB, 完整 SC 子集)
抓取地址  : https://cdn.jsdelivr.net/gh/googlefonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf
许可文件  : LICENSE.txt（上游 Sans/LICENSE，SIL Open Font License 1.1 全文）

为什么是子集
------------
完整文件 8.3 MB，对一个小游戏偏重。本项目用 fontTools 做了字符子集化，
只保留游戏真正会渲染的 3,964 个字符（GB2312 一级汉字 3,755 + ASCII +
CJK 标点 + UI 用符号），体积降到 862 KB。

复现命令（需要 pip install fonttools）
------------------------------------
    python -m fontTools.subset NotoSansSC-Regular.otf \
        --text-file=<字符集文件, 见 tools/build_font_subset.py> \
        --output-file=NotoSansSC-Regular.otf \
        --layout-features='*' --no-hinting --desubroutinize --name-IDs='*' --name-legacy

字符集可用 tools/build_font_subset.py 重新生成（它会扫描 src/ 下所有字符串，
再并入 GB2312 一级汉字与常用标点，保证新增文案不会缺字）。

许可
----
SIL Open Font License 1.1 —— 允许自由使用、修改、再分发（含商用），
要求保留版权声明与许可文本，且不得单独出售字体本身。
许可全文见同目录 LICENSE.txt。
