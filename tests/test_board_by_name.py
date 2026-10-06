"""Tests for BoardByNameInvocation.

Run with the Python environment of an InvokeAI install (they only need InvokeAI importable):
    python -m pytest -q

The tests cover both code paths: InvokeAI versions that have `context.boards.resolve`, and older ones.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from invokeai.app.invocations.fields import BoardField

from board_by_name import BoardByNameInvocation, BoardByNameOutput

USER = "queue-user"


def _board(board_id: str, name: str, user_id: str = USER) -> SimpleNamespace:
    return SimpleNamespace(board_id=board_id, board_name=name, user_id=user_id)


def _context(boards: list[SimpleNamespace], has_resolve: bool = False) -> MagicMock:
    """A mocked InvocationContext. Without `has_resolve` it behaves like an InvokeAI that predates resolve()."""
    context = MagicMock()
    context.boards.get_all.return_value = boards
    context.boards.create.side_effect = lambda name: _board(f"new-{name}", name)
    context.boards._data.queue_item.user_id = USER
    if not has_resolve:
        del context.boards.resolve
    return context


def _resolve(context: MagicMock, **kwargs) -> str:
    output = BoardByNameInvocation(id="n", **kwargs).invoke(context)
    assert isinstance(output, BoardByNameOutput)
    assert isinstance(output.board, BoardField)
    return output.board.board_id


def test_is_never_cached():
    # A cached output could point at a board that was deleted or renamed since.
    assert BoardByNameInvocation(id="n", board_name="x").use_cache is False


@pytest.mark.parametrize("has_resolve", [False, True])
def test_empty_name_is_an_error(has_resolve):
    context = _context([], has_resolve=has_resolve)
    with pytest.raises(ValueError, match="Board name is empty"):
        _resolve(context, board_name="   ")
    context.boards.create.assert_not_called()


# --- InvokeAI with context.boards.resolve ---------------------------------------------------------------------


@pytest.mark.parametrize("create_if_missing", [True, False])
def test_resolve_is_used_when_available(create_if_missing):
    context = _context([], has_resolve=True)
    context.boards.resolve.return_value = _board("b1", "session-hi")
    assert _resolve(context, board_name=" session-hi ", create_if_missing=create_if_missing) == "b1"
    context.boards.resolve.assert_called_once_with("session-hi", create_if_missing=create_if_missing)
    context.boards.get_all.assert_not_called()
    context.boards.create.assert_not_called()


def test_resolve_returning_none_is_a_clear_error():
    context = _context([], has_resolve=True)
    context.boards.resolve.return_value = None
    with pytest.raises(ValueError, match="No board named 'nope'"):
        _resolve(context, board_name="nope", create_if_missing=False)


def test_resolve_errors_propagate():
    context = _context([], has_resolve=True)
    context.boards.resolve.side_effect = RuntimeError('Multiple boards named "dup"')
    with pytest.raises(RuntimeError, match="Multiple boards"):
        _resolve(context, board_name="dup")


# --- InvokeAI without context.boards.resolve ------------------------------------------------------------------


def test_existing_board_is_found():
    context = _context([_board("b1", "session-hi")])
    assert _resolve(context, board_name="session-hi") == "b1"
    context.boards.create.assert_not_called()


def test_name_is_trimmed():
    context = _context([_board("b1", "session-hi")])
    assert _resolve(context, board_name="  session-hi ") == "b1"


def test_missing_board_is_created():
    context = _context([])
    assert _resolve(context, board_name="session-lo") == "new-session-lo"
    context.boards.create.assert_called_once_with("session-lo")


def test_matching_is_case_sensitive():
    context = _context([_board("b1", "Session-HI")])
    assert _resolve(context, board_name="session-hi") == "new-session-hi"
    context.boards.create.assert_called_once_with("session-hi")


def test_other_users_boards_never_match():
    context = _context([_board("b1", "session-hi", user_id="someone-else")])
    assert _resolve(context, board_name="session-hi") == "new-session-hi"
    context.boards.create.assert_called_once_with("session-hi")


def test_missing_board_errors_when_create_disabled():
    context = _context([])
    with pytest.raises(ValueError, match="No board named"):
        _resolve(context, board_name="nope", create_if_missing=False)
    context.boards.create.assert_not_called()


def test_ambiguous_name_errors():
    context = _context([_board("b1", "dup"), _board("b2", "dup")])
    with pytest.raises(ValueError, match="Multiple boards"):
        _resolve(context, board_name="dup")


def test_get_all_typeerror_falls_back_to_service():
    context = _context([])
    context.boards.get_all.side_effect = TypeError("missing is_admin")
    context.boards._services.configuration.multiuser = False
    context.boards._services.boards.get_all.return_value = [_board("b9", "found")]
    assert _resolve(context, board_name="found") == "b9"
