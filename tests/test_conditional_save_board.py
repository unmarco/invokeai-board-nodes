"""Tests for ConditionalSaveToBoardInvocation.

Run with the Python environment of an InvokeAI install (they only need InvokeAI importable):
    python -m pytest -q

The server's custom-node loader only imports the pack's __init__.py, so these are never loaded by Invoke.
The tests cover both code paths: InvokeAI versions that have `context.boards.resolve`, and older ones.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from invokeai.app.invocations.fields import BoardField, ImageField, WithBoard

from conditional_save_board import ConditionalSaveToBoardInvocation

USER = "queue-user"


def _board(board_id: str, name: str, user_id: str = USER) -> SimpleNamespace:
    return SimpleNamespace(board_id=board_id, board_name=name, user_id=user_id)


def _context(boards: list[SimpleNamespace], has_resolve: bool = False) -> MagicMock:
    """A mocked InvocationContext. Without `has_resolve` it behaves like an InvokeAI that predates resolve()."""
    context = MagicMock()
    context.boards.get_all.return_value = boards
    context.boards.create.side_effect = lambda name: _board(f"new-{name}", name)
    context.boards._data.queue_item.user_id = USER
    context.images.save.return_value = SimpleNamespace(image_name="copy.png", width=8, height=8)
    context.images.get_dto.return_value = SimpleNamespace(image_name="src.png", width=8, height=8)
    if not has_resolve:
        del context.boards.resolve
    return context


def _node(**kwargs) -> ConditionalSaveToBoardInvocation:
    return ConditionalSaveToBoardInvocation(id="n", image=ImageField(image_name="src.png"), **kwargs)


def _saved_board_id(context: MagicMock) -> str | None:
    context.images.save.assert_called_once()
    return context.images.save.call_args.kwargs["board_id"]


def test_has_board_picker_like_other_save_nodes():
    assert issubclass(ConditionalSaveToBoardInvocation, WithBoard)
    assert _node().board is None


@pytest.mark.parametrize("has_resolve", [False, True])
def test_empty_name_defers_to_picker(has_resolve):
    # board_id=None makes context.images.save() fall back to the WithBoard picker (or Uncategorized if unset).
    context = _context([_board("b1", "session")], has_resolve=has_resolve)
    _node(board_name="  ", board=BoardField(board_id="picked")).invoke(context)
    assert _saved_board_id(context) is None
    context.boards.get_all.assert_not_called()
    if has_resolve:
        context.boards.resolve.assert_not_called()


@pytest.mark.parametrize("picked, expected", [(BoardField(board_id="picked"), "picked"), (None, None)])
def test_real_save_falls_back_to_picker(picked, expected):
    # Exercises Invoke's own ImagesInterface.save(), which reads the WithBoard field when board_id is None.
    from invokeai.app.services.shared.invocation_context import ImagesInterface

    node = _node(board_name="", board=picked)
    services = MagicMock()
    services.configuration.multiuser = False
    data = MagicMock()
    data.invocation = node
    data.queue_item.workflow = None
    data.queue_item.session.graph = None
    ImagesInterface(services=services, data=data, util=MagicMock()).save(image=MagicMock(), board_id=None)
    assert services.images.create.call_args.kwargs["board_id"] == expected


def test_disabled_passes_through_without_saving():
    context = _context([], has_resolve=True)
    _node(enabled=False, board_name="x", board=BoardField(board_id="picked")).invoke(context)
    context.images.save.assert_not_called()
    context.boards.create.assert_not_called()
    context.boards.resolve.assert_not_called()


# --- InvokeAI with context.boards.resolve ---------------------------------------------------------------------


@pytest.mark.parametrize("create_if_missing", [True, False])
def test_resolve_is_used_when_available(create_if_missing):
    context = _context([], has_resolve=True)
    context.boards.resolve.return_value = _board("b1", "session-hi")
    _node(board_name=" session-hi ", create_if_missing=create_if_missing, board=BoardField(board_id="picked")).invoke(
        context
    )
    context.boards.resolve.assert_called_once_with("session-hi", create_if_missing=create_if_missing)
    assert _saved_board_id(context) == "b1"
    context.boards.get_all.assert_not_called()
    context.boards.create.assert_not_called()


def test_resolve_returning_none_is_a_clear_error():
    context = _context([], has_resolve=True)
    context.boards.resolve.return_value = None
    with pytest.raises(ValueError, match="No board named 'nope'"):
        _node(board_name="nope", create_if_missing=False).invoke(context)
    context.images.save.assert_not_called()


def test_resolve_errors_propagate():
    context = _context([], has_resolve=True)
    context.boards.resolve.side_effect = RuntimeError('Multiple boards named "dup"')
    with pytest.raises(RuntimeError, match="Multiple boards"):
        _node(board_name="dup").invoke(context)
    context.images.save.assert_not_called()


# --- InvokeAI without context.boards.resolve ------------------------------------------------------------------


def test_name_overrides_picker():
    context = _context([_board("b1", "session-hi")])
    _node(board_name="session-hi", board=BoardField(board_id="picked")).invoke(context)
    assert _saved_board_id(context) == "b1"


def test_name_is_trimmed():
    context = _context([_board("b1", "session-hi")])
    _node(board_name="  session-hi ").invoke(context)
    assert _saved_board_id(context) == "b1"


def test_missing_board_is_created():
    context = _context([])
    _node(board_name="session-lo").invoke(context)
    context.boards.create.assert_called_once_with("session-lo")
    assert _saved_board_id(context) == "new-session-lo"


def test_matching_is_case_sensitive():
    context = _context([_board("b1", "Session-HI")])
    _node(board_name="session-hi").invoke(context)
    context.boards.create.assert_called_once_with("session-hi")
    assert _saved_board_id(context) == "new-session-hi"


def test_other_users_boards_never_match():
    context = _context([_board("b1", "session-hi", user_id="someone-else")])
    _node(board_name="session-hi").invoke(context)
    context.boards.create.assert_called_once_with("session-hi")
    assert _saved_board_id(context) == "new-session-hi"


def test_missing_board_errors_when_create_disabled():
    context = _context([])
    with pytest.raises(ValueError, match="No board named"):
        _node(board_name="nope", create_if_missing=False).invoke(context)
    context.images.save.assert_not_called()


def test_ambiguous_name_errors():
    context = _context([_board("b1", "dup"), _board("b2", "dup")])
    with pytest.raises(ValueError, match="Multiple boards"):
        _node(board_name="dup").invoke(context)
    context.images.save.assert_not_called()


def test_get_all_typeerror_falls_back_to_service():
    context = _context([])
    context.boards.get_all.side_effect = TypeError("missing is_admin")
    context.boards._services.configuration.multiuser = False
    context.boards._services.boards.get_all.return_value = [_board("b9", "found")]
    _node(board_name="found").invoke(context)
    assert _saved_board_id(context) == "b9"
