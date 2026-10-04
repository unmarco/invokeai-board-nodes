# Save to Board (Conditional) — InvokeAI custom node

An [InvokeAI](https://github.com/invoke-ai/InvokeAI) node that saves a copy of an image to a board **chosen by name while the workflow runs**, or skips saving entirely.

The board picker on InvokeAI's built-in save nodes is fixed before the run. This node takes the board name (and an on/off switch) as ordinary inputs, so both can come from the graph:

- A session name typed into a text field, joined with `-lo` and `-hi`, saves the original generation to `toyrobot-lo` and the optional upscale to `toyrobot-hi`. Neither board has to exist beforehand.
- A LoRA name coming from a randomizer node is used as the board name, so every LoRA's results end up in their own board.
- A Boolean switches a branch of the workflow on or off (say, "also save the upscale").

## Inputs

| Input | What it does |
| --- | --- |
| `image` | The image to save a copy of. |
| `enabled` | When off, nothing is saved and the image is passed through unchanged. Can be connected to a Boolean. |
| `board_name` | The board to save to. Can be connected. Leave empty to use the board picker below, as on other save nodes (Uncategorized if unset). |
| `create_if_missing` | Create the board if it doesn't exist (default on). When off, a missing board is an error. |
| board picker | Used only when `board_name` is empty. |
| metadata | If none is connected, the copy keeps the input image's own metadata. |

The output is the saved image (or the input image when disabled), so the node can sit in the middle of a graph.

## How names are matched

- Leading and trailing whitespace is ignored; otherwise the name must match **exactly** (case-sensitive).
- Only **your own** boards are considered: other users' shared or public boards never match.
- Archived boards are ignored.
- If **more than one** board has the name, the node fails and says so. Rename or archive all but one.

These are the rules of InvokeAI's `context.boards.resolve`, which this node uses when your InvokeAI has it, and follows itself when it doesn't.

## Install

1. Clone this repository into the `nodes` folder of your InvokeAI root (the folder that also holds `invokeai.yaml`):

   ```
   cd <invokeai root>/nodes
   git clone https://github.com/<you>/invokeai-conditional-save-board
   ```

2. Restart InvokeAI and hard-reload the browser page.
3. Open or build a workflow. The node is called **Save to Board (Conditional)** (category `image`).

Workflows saved while the node wasn't installed lose their connections to it; install first, then open them.

## Compatibility

Developed and used on InvokeAI 6.14.x. On versions that have `context.boards.resolve` the node calls it; on older ones it finds and creates the board itself, with the same rules. Two things to know there:

- `context.boards.get_all()` had a bug for some versions (invoke-ai/InvokeAI#9652, fixed in #9653), which the node works around.
- Boards created while a workflow runs may not appear in the board list until the page is reloaded.

## Tests

The tests only need InvokeAI importable; run them with the Python environment of an InvokeAI install:

```
python -m pytest tests
```

They cover both code paths, with and without `context.boards.resolve`.

## License

MIT, see [LICENSE](LICENSE).
