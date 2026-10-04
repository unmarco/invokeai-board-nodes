# Save to Board (Conditional)

A custom node for [InvokeAI](https://github.com/invoke-ai/InvokeAI) that saves an image to a board whose **name is decided while the workflow runs**, and can switch saving on or off.

## Why

InvokeAI's built-in save nodes use a board picker, which is fixed before you press Invoke. That is fine until the destination depends on something the workflow itself produces or receives. With this node, the board name and an on/off switch are ordinary inputs, so they can be connected to other nodes.

Some things that become possible:

- **One workflow, many sessions.** Type a name such as `toyrobot` into a text field and join it with `-lo` and `-hi`. The original image is saved to `toyrobot-lo`, the optional upscale to `toyrobot-hi`. The boards are created the first time they are needed.
- **Grouping by a value from the graph.** A randomizer node picks a LoRA, and its name becomes the board name, so each LoRA's results are collected in their own board.
- **Optional branches.** Connect a Boolean to `enabled` so an extra step, for example the upscale, is saved only when you want it.

## Using it

Add **Save to Board (Conditional)** (category `image`) and connect an image. Then:

| Input | What it does |
| --- | --- |
| `image` | The image to save. A copy is saved; the original is untouched. |
| `board_name` | The board to save to. Connect it to build the name in the graph, or type it. If it is empty, the board picker below is used, as on other save nodes (Uncategorized if unset). |
| `create_if_missing` | On by default: a board that doesn't exist yet is created. Turn it off to make a missing board an error instead. |
| `enabled` | On by default. When off, nothing is saved and the image is passed on unchanged. |
| board picker | Used only when `board_name` is empty. |
| metadata | If none is connected, the saved copy keeps the input image's own metadata. |

The node outputs the saved image (or the input image when `enabled` is off), so you can put it in the middle of a graph and keep going.

## How the board name is matched

- Spaces at the start and end are ignored. Otherwise the name must be exactly the same, including upper and lower case: `Toyrobot` and `toyrobot` are different boards.
- Only your own boards are considered, not boards that other users have shared with you.
- Archived boards are ignored, so archiving a board means "done with this name".
- If two or more of your boards have that name, the node stops with an error that says so. Rename or archive all but one.

## Install

1. Clone this repository into the `nodes` folder of your InvokeAI root (the folder that holds `invokeai.yaml`):

   ```
   cd <invokeai root>/nodes
   git clone https://github.com/<you>/invokeai-conditional-save-board
   ```

2. Restart InvokeAI and hard-reload the browser page.
3. Add the node in the workflow editor.

Install the node before opening workflows that use it. A workflow opened without it loses its connections to the missing node, and saving it keeps them lost.

## Compatibility

Developed and used on InvokeAI 6.14.x. Newer versions of InvokeAI may provide `context.boards.resolve`, which finds or creates a board by name for custom nodes. If it is there, the node uses it. If not, the node does the same thing itself, with the same rules as above.

On older versions, two things to know:

- Boards created while a workflow runs may not show up in the board list until you reload the page.
- InvokeAI's `context.boards.get_all()` had a bug in some versions ([#9652](https://github.com/invoke-ai/InvokeAI/issues/9652), fixed in [#9653](https://github.com/invoke-ai/InvokeAI/pull/9653)). The node works around it.

## Tests

The tests need InvokeAI importable, so run them with the Python environment of an InvokeAI install:

```
python -m pytest tests
```

They cover both ways the node finds boards: with and without `context.boards.resolve`.

## License

MIT, see [LICENSE](LICENSE).
