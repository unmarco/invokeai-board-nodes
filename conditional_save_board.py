from typing import Optional

from invokeai.app.services.board_records.board_records_common import BoardRecordOrderBy
from invokeai.app.services.shared.sqlite.sqlite_common import SQLiteDirection
from invokeai.invocation_api import (
    BaseInvocation,
    BoardDTO,
    FieldDescriptions,
    ImageField,
    ImageOutput,
    InputField,
    InvocationContext,
    WithBoard,
    WithMetadata,
    invocation,
)


@invocation(
    "conditional_save_to_board",
    title="Save to Board (Conditional)",
    tags=["image", "save", "board", "conditional", "logic"],
    category="image",
    version="1.2.0",
    use_cache=False,
)
class ConditionalSaveToBoardInvocation(BaseInvocation, WithBoard, WithMetadata):
    """Saves a copy of an image to a board chosen by name, or skips saving entirely.

    Use it when the destination is only known while the workflow runs, which the board picker of
    the built-in save nodes can't do. For example: a session name typed into a text field and joined
    with "-lo" and "-hi" to send originals and upscales to separate boards, or a LoRA name from a
    randomizer node used as the board name, so each LoRA's results end up together.

    - `board_name` can be connected, so the board is built in the graph. Surrounding whitespace is
      ignored; otherwise the name must match exactly (case-sensitive), and only your own boards are
      considered. A board that doesn't exist is created (turn off `create_if_missing` to make that
      an error instead). If several boards share the name, the node fails and says so.
    - `enabled` can be connected to a Boolean, so part of a workflow (say, an optional upscale)
      saves only when wanted. When off, nothing is written and the image passes through unchanged.
    - With an empty `board_name`, the board picker is used, as on other save nodes (Uncategorized
      if unset).
    - The copy keeps the input image's metadata unless metadata is connected.
    """

    image: ImageField = InputField(description=FieldDescriptions.image)
    enabled: bool = InputField(
        default=True,
        description="When off, nothing is saved and the input image is passed through",
    )
    board_name: str = InputField(
        default="",
        description="Name of the board to save to (exact, case-sensitive); overrides the board picker. "
        "Leave empty to use the board picker.",
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
            user_id = ConditionalSaveToBoardInvocation._queue_user_id(context)
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

    def _resolve_board_id(self, context: InvocationContext) -> Optional[str]:
        name = self.board_name.strip()
        if not name:
            return None

        if not hasattr(context.boards, "resolve"):
            return self._find_or_create_board(context, name)

        board = context.boards.resolve(name, create_if_missing=self.create_if_missing)
        if board is None:
            raise ValueError(f"No board named '{name}' (enable 'Create If Missing' to create it)")
        return board.board_id

    def invoke(self, context: InvocationContext) -> ImageOutput:
        if not self.enabled:
            return ImageOutput.build(context.images.get_dto(self.image.image_name))

        # None lets context.images.save() fall back to the WithBoard picker.
        board_id = self._resolve_board_id(context)
        image = context.images.get_pil(self.image.image_name)
        # Without connected metadata, keep the source image's own metadata on the copy.
        metadata = self.metadata or context.images.get_metadata(self.image.image_name)
        image_dto = context.images.save(image=image, board_id=board_id, metadata=metadata)
        return ImageOutput.build(image_dto)
