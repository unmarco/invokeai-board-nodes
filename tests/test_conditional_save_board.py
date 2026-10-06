"""Tests for ConditionalSaveToBoardInvocation.

Run with the Python environment of an InvokeAI install (they only need InvokeAI importable):
    python -m pytest -q

The server's custom-node loader only imports the pack's __init__.py, so these are never loaded by Invoke.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from invokeai.app.invocations.fields import BoardField, ImageField, Input, WithBoard

from conditional_save_board import ConditionalSaveToBoardInvocation


def _context() -> MagicMock:
    context = MagicMock()
    context.images.save.return_value = SimpleNamespace(image_name="copy.png", width=8, height=8)
    context.images.get_dto.return_value = SimpleNamespace(image_name="src.png", width=8, height=8)
    return context


def _node(**kwargs) -> ConditionalSaveToBoardInvocation:
    return ConditionalSaveToBoardInvocation(id="n", image=ImageField(image_name="src.png"), **kwargs)


def _saved_board_id(context: MagicMock) -> str | None:
    context.images.save.assert_called_once()
    return context.images.save.call_args.kwargs["board_id"]


def test_board_is_a_connectable_picker():
    # WithBoard's picker is direct-only; this node declares its own so Board by Name can feed it.
    assert not issubclass(ConditionalSaveToBoardInvocation, WithBoard)
    field = ConditionalSaveToBoardInvocation.model_fields["target_board"]
    assert field.json_schema_extra["input"] == Input.Any
    assert field.json_schema_extra["field_kind"] == "input"
    assert field.title == "Board"
    assert _node().target_board is None


def test_enabled_is_titled_save_enabled():
    assert ConditionalSaveToBoardInvocation.model_fields["enabled"].title == "Save Enabled"


def test_has_no_name_inputs():
    # Names are Board by Name's job now.
    assert "board_name" not in ConditionalSaveToBoardInvocation.model_fields
    assert "create_if_missing" not in ConditionalSaveToBoardInvocation.model_fields


@pytest.mark.parametrize("board, expected", [(BoardField(board_id="picked"), "picked"), (None, None)])
def test_saves_to_the_board_input(board, expected):
    context = _context()
    _node(target_board=board).invoke(context)
    assert _saved_board_id(context) == expected


@pytest.mark.parametrize("board, expected", [(BoardField(board_id="picked"), "picked"), (None, None)])
def test_real_save_uses_the_board_input(board, expected):
    # Invoke's own ImagesInterface.save() only reads WithBoard fields by itself, so the node must pass board_id.
    from invokeai.app.services.shared.invocation_context import ImagesInterface

    node = _node(target_board=board)
    services = MagicMock()
    services.configuration.multiuser = False
    data = MagicMock()
    data.invocation = node
    data.queue_item.workflow = None
    data.queue_item.session.graph = None
    context = _context()
    context.images = ImagesInterface(services=services, data=data, util=MagicMock())
    context.images.get_pil = MagicMock()
    context.images.get_metadata = MagicMock(return_value=None)
    services.images.create.return_value = SimpleNamespace(image_name="copy.png", width=8, height=8)
    node.invoke(context)
    assert services.images.create.call_args.kwargs["board_id"] == expected


def test_disabled_passes_through_without_saving():
    context = _context()
    output = _node(enabled=False, target_board=BoardField(board_id="picked")).invoke(context)
    context.images.save.assert_not_called()
    assert output.image.image_name == "src.png"


def test_intermediate_save_is_refused():
    # An intermediate copy is hidden from the board and removed by Clear Intermediates, so saving one would look
    # like the node did nothing. Both UIs add custom nodes with Save to Gallery off, so this is the common case.
    context = _context()
    with pytest.raises(ValueError, match="Save to Gallery is off"):
        _node(is_intermediate=True, target_board=BoardField(board_id="picked")).invoke(context)
    context.images.save.assert_not_called()


def test_intermediate_is_fine_when_disabled():
    context = _context()
    output = _node(is_intermediate=True, enabled=False).invoke(context)
    context.images.save.assert_not_called()
    assert output.image.image_name == "src.png"


def test_keeps_source_metadata_when_none_connected():
    context = _context()
    context.images.get_metadata.return_value = {"seed": 1}
    _node().invoke(context)
    assert context.images.save.call_args.kwargs["metadata"] == {"seed": 1}
