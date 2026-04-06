"""
Bug condition exploration test for history-bugs-fix spec.

Task 1: Write bug condition exploration test
目标：在未修复代码上断言 get_subject_sessions 返回的每条 dict 包含 subject_id 字段。
此测试在未修复代码上 MUST FAIL（失败即证明 bug 存在）。

Validates: Requirements 2.1, 2.2
"""

from datetime import datetime
from unittest.mock import MagicMock, patch


def _make_fake_session(id_=5, subject_id=1, user_id=1, title="Test Session",
                       session_type="qa", created_at=None):
    """构造一个假的 ConversationSession ORM 对象。"""
    obj = MagicMock()
    obj.id = id_
    obj.subject_id = subject_id
    obj.user_id = user_id
    obj.title = title
    obj.session_type = session_type
    obj.created_at = created_at or datetime(2024, 1, 1, 12, 0, 0)
    return obj


def test_get_subject_sessions_has_subject_id():
    """
    Bug condition exploration test (Bug 1 & 4):
    断言 get_subject_sessions 返回的每条 dict 包含 subject_id 字段。

    在未修复代码上此测试 MUST FAIL，失败即证明 bug 存在。
    """
    fake_session_obj = _make_fake_session(id_=5, subject_id=1, user_id=1)

    # Mock 数据库查询，避免真实数据库连接
    mock_query = MagicMock()
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [fake_session_obj]

    mock_db_session = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_db_session.__enter__ = MagicMock(return_value=mock_db_session)
    mock_db_session.__exit__ = MagicMock(return_value=False)

    with patch("utils.get_session", return_value=mock_db_session):
        from utils import get_subject_sessions
        result = get_subject_sessions(subject_id=1, user_id=1)

    assert isinstance(result, list), "get_subject_sessions 应返回列表"
    assert len(result) == 1, "应返回 1 条会话"

    # 以下断言在未修复代码上 WILL FAIL（bug 的证明）
    assert "subject_id" in result[0], (
        "Bug detected: get_subject_sessions 返回的 dict 缺少 'subject_id' 字段"
    )
    assert result[0]["subject_id"] == 1, (
        f"Bug detected: subject_id 应为 1，实际为 {result[0].get('subject_id')}"
    )


"""
Task 2: Write preservation property tests (BEFORE implementing fix)
目标：验证 get_subject_sessions 原有字段（id、title、session_type、type_label、created_at）不变。
此测试在未修复代码上 MUST PASS（确认基准行为）。

Validates: Requirements 3.6
"""


def test_get_subject_sessions_preserves_original_fields():
    """
    Preservation property test (Property 4):
    断言 get_subject_sessions 返回的每条 dict 包含所有原有字段，且值正确。

    在未修复代码上此测试 MUST PASS（确认基准行为不变）。
    """
    fake_session_obj = _make_fake_session(
        id_=5,
        subject_id=1,
        user_id=1,
        title="Test Session",
        session_type="qa",
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )

    mock_query = MagicMock()
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [fake_session_obj]

    mock_db_session = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_db_session.__enter__ = MagicMock(return_value=mock_db_session)
    mock_db_session.__exit__ = MagicMock(return_value=False)

    with patch("utils.get_session", return_value=mock_db_session):
        from utils import get_subject_sessions
        result = get_subject_sessions(subject_id=1, user_id=1)

    assert isinstance(result, list), "get_subject_sessions 应返回列表"
    assert len(result) == 1, "应返回 1 条会话"

    item = result[0]

    # 验证所有原有字段存在
    for field in ("id", "title", "session_type", "type_label", "created_at"):
        assert field in item, f"原有字段 '{field}' 不应被移除"

    # 验证各字段值正确
    assert item["id"] == 5, f"id 应为 5，实际为 {item['id']}"
    assert item["title"] == "Test Session", f"title 应为 'Test Session'，实际为 {item['title']}"
    assert item["session_type"] == "qa", f"session_type 应为 'qa'，实际为 {item['session_type']}"
    assert item["type_label"] == "💬 问答", f"type_label 应为 '💬 问答'，实际为 {item['type_label']}"
    assert item["created_at"] == datetime(2024, 1, 1, 12, 0, 0), (
        f"created_at 应为 datetime(2024,1,1,12,0,0)，实际为 {item['created_at']}"
    )


def test_get_subject_sessions_preserves_order_by_created_at_desc():
    """
    Preservation property test (Property 4 - ordering):
    断言 get_subject_sessions 返回列表按 created_at 倒序排列。

    在未修复代码上此测试 MUST PASS（确认排序行为不变）。
    """
    older = _make_fake_session(id_=1, subject_id=1, user_id=1, title="Older",
                               session_type="qa", created_at=datetime(2024, 1, 1, 10, 0, 0))
    newer = _make_fake_session(id_=2, subject_id=1, user_id=1, title="Newer",
                               session_type="qa", created_at=datetime(2024, 1, 2, 10, 0, 0))

    # 数据库已按 created_at desc 排序，mock 返回顺序模拟该行为（newer 在前）
    mock_query = MagicMock()
    mock_query.filter_by.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = [newer, older]

    mock_db_session = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_db_session.__enter__ = MagicMock(return_value=mock_db_session)
    mock_db_session.__exit__ = MagicMock(return_value=False)

    with patch("utils.get_session", return_value=mock_db_session):
        from utils import get_subject_sessions
        result = get_subject_sessions(subject_id=1, user_id=1)

    assert len(result) == 2, "应返回 2 条会话"
    assert result[0]["created_at"] >= result[1]["created_at"], (
        "返回列表应按 created_at 倒序排列（较新的在前）"
    )
    assert result[0]["id"] == 2, "较新的会话（id=2）应排在第一位"
    assert result[1]["id"] == 1, "较旧的会话（id=1）应排在第二位"
