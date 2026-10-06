from typing import Optional

from invokeai.invocation_api import (
    BaseInvocation,
    BoardField,
    FieldDescriptions,
    ImageField,
    ImageOutput,
    Input,
    InputField,
    InvocationContext,
    WithMetadata,
    invocation,
)


@invocation(
    "conditional_save_to_board",
    title="Save to Board (Conditional)",
    tags=["image", "save", "board", "conditional", "logic"],
    category="image",
    version="2.0.0",
    use_cache=False,
)
class ConditionalSaveToBoardInvocation(BaseInvocation, WithMetadata):
    """Saves a copy of an image to a board, or skips saving entirely.

    - Board is a board picker that can also be connected, unlike the one on the built-in save
      nodes. Connect Board by Name to it when the destination is only known while the workflow runs.
    - Save Enabled can be connected to a Boolean, so part of a workflow (say, an optional upscale)
      saves only when wanted. When off, nothing is written and the image passes through unchanged.
    - Save to Gallery (at the bottom of the node) must be on while Save Enabled is on; otherwise the node
      stops with an error, because an intermediate copy would be hidden from the board.
    - The copy keeps the input image's metadata unless metadata is connected.
    """

    image: ImageField = InputField(description=FieldDescriptions.image)
    # Not WithBoard: its picker accepts no connections, and the name `board` is reserved for it.
    # images.save() only reads WithBoard's field by itself, so invoke() passes this one explicitly.
    target_board: Optional[BoardField] = InputField(
        default=None, title="Board", description=FieldDescriptions.board, input=Input.Any
    )
    enabled: bool = InputField(
        default=True,
        title="Save Enabled",
        description="When off, nothing is saved and the input image is passed through",
    )

    def invoke(self, context: InvocationContext) -> ImageOutput:
        if not self.enabled:
            return ImageOutput.build(context.images.get_dto(self.image.image_name))
        if self.is_intermediate:
            # An intermediate copy is hidden from the board and removed by Clear Intermediates, so the save would
            # look like it never happened. Both UIs add custom nodes with Save to Gallery off.
            raise ValueError(
                "Save to Gallery is off, so the copy would be hidden from the board. "
                "Turn it on, or turn off Save Enabled to skip saving."
            )

        image = context.images.get_pil(self.image.image_name)
        # Without connected metadata, keep the source image's own metadata on the copy.
        metadata = self.metadata or context.images.get_metadata(self.image.image_name)
        board_id = self.target_board.board_id if self.target_board else None
        image_dto = context.images.save(image=image, board_id=board_id, metadata=metadata)
        return ImageOutput.build(image_dto)
