from invokeai.app.services.board_records.board_records_common import BoardRecordOrderBy
from invokeai.app.services.shared.sqlite.sqlite_common import SQLiteDirection
from invokeai.invocation_api import (
    BaseInvocation,
    BaseInvocationOutput,
    BoardDTO,
    BoardField,
    InputField,
    InvocationContext,
    OutputField,
    invocation,
    invocation_output,
)


@invocation_output("board_by_name_output")
class BoardByNameOutput(BaseInvocationOutput):
    """A board, for any input that takes one"""

    board: BoardField = OutputField(description="The board")


@invocation(
    "board_by_name",
    title="Board by Name",
    tags=["board", "name", "resolve", "create"],
    category="image",
    version="1.0.0",
    use_cache=False,
)
class BoardByNameInvocation(BaseInvocation):
    """Finds one of your boards by name, creating it if it doesn't exist, and outputs it for a board input.

    Use it when the destination is only known while the workflow runs. Connect `board_name` to build
    the name in the graph, for example a session name joined with "-lo" or "-hi", or a LoRA name from
    a randomizer node, then connect the output to the board input of Save to Board (Conditional).

    Surrounding whitespace is ignored; otherwise the name must match exactly (case-sensitive), and only
    your own boards are considered. A board that doesn't exist is created (turn off `create_if_missing`
    to make that an error instead). If several boards share the name, the node fails and says so.
    """

    board_name: str = InputField(
        default="",
        description="Name of the board (exact, case-sensitive; surrounding spaces are ignored)",
    )
    create_if_missing: bool = InputField(
        default=True,
        description="Create the board if no board with this name exists. When off, a missing board is an error.",
    )

    @staticmethod
    def _get_all_boards(context: InvocationContext) -> list[BoardDTO]:
        try:
            return context.boards.get_all()
        except TypeError:
            # BoardsInterface.get_all() doesn't pass the `is_admin` argument that BoardService.get_all() gained
            # with multiuser support (invoke-ai/InvokeAI#9652, fixed by #9653; affects 6.14.x and 7.0.0-alpha.1).
            # Call the service the way the API router does. Dead code once the fix ships.
            services = context.boards._services
            user_id = BoardByNameInvocation._queue_user_id(context)
            is_admin = not services.configuration.multiuser or services.users.get(user_id).is_admin
            return services.boards.get_all(
                user_id, is_admin, order_by=BoardRecordOrderBy.CreatedAt, direction=SQLiteDirection.Descending
            )

    @staticmethod
    def _queue_user_id(context: InvocationContext) -> str:
        return context.boards._data.queue_item.user_id

    def _find_or_create_board(self, context: InvocationContext, name: str) -> str:
        """Board lookup for InvokeAI versions without `context.boards.resolve`.

        Follows the same rules as `resolve`: exact, case-sensitive names; only the queue user's own boards.
        """
        user_id = self._queue_user_id(context)
        matches = [b for b in self._get_all_boards(context) if b.board_name == name and b.user_id == user_id]
        if len(matches) > 1:
            raise ValueError(f"Multiple boards are named '{name}'; rename one so the target is unambiguous")
        if matches:
            return matches[0].board_id
        if not self.create_if_missing:
            raise ValueError(f"No board named '{name}' (enable 'Create If Missing' to create it)")

        context.logger.info(f"Creating board '{name}'")
        return context.boards.create(name).board_id

    def _resolve_board_id(self, context: InvocationContext, name: str) -> str:
        if not hasattr(context.boards, "resolve"):
            return self._find_or_create_board(context, name)

        board = context.boards.resolve(name, create_if_missing=self.create_if_missing)
        if board is None:
            raise ValueError(f"No board named '{name}' (enable 'Create If Missing' to create it)")
        return board.board_id

    def invoke(self, context: InvocationContext) -> BoardByNameOutput:
        name = self.board_name.strip()
        if not name:
            raise ValueError("Board name is empty")
        return BoardByNameOutput(board=BoardField(board_id=self._resolve_board_id(context, name)))
