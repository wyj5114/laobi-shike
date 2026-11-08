"""分组名校验：B 站合集自动建组时标题经常超过 20 字，旧上限会把整批任务憋死。

这里锁住 v1.1.2 的行为：上限 60 字、空名拒绝、前后空白自动裁剪。
"""

import pytest

from app.db.library_dao import GROUP_NAME_MAX, _validate_group_name


def test_limit_is_at_least_60():
    assert GROUP_NAME_MAX >= 60


def test_accepts_long_title():
    name = "课" * 60
    assert _validate_group_name(name) == name


def test_rejects_over_limit():
    with pytest.raises(ValueError, match="60"):
        _validate_group_name("课" * (GROUP_NAME_MAX + 1))


def test_rejects_blank_and_trims():
    with pytest.raises(ValueError):
        _validate_group_name("   ")
    assert _validate_group_name("  考研数学  ") == "考研数学"
