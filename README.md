# Board nodes for InvokeAI

Two custom nodes for [InvokeAI](https://github.com/invoke-ai/InvokeAI) that let a workflow **choose its board while it runs**, and switch saving on or off.

- **Board by Name** finds one of your boards by name, creating it if needed, and outputs it.
- **Save to Board (Conditional)** saves a copy of an image to a board. Its board input can be connected, and saving can be turned off from the graph.

## Why

InvokeAI's built-in save nodes use a board picker, which is fixed before you press Invoke and can't be connected. That is fine until the destination depends on something the workflow itself produces or receives.

Some things that become possible:

- **One workflow, many sessions.** Type a name such as `toyrobot` into a text field and join it with `-lo` and `-hi`. The original image is saved to `toyrobot-lo`, the optional upscale to `toyrobot-hi`. The boards are created the first time they are needed.
- **Grouping by a value from the graph.** A randomizer node picks a LoRA, and its name becomes the board name, so each LoRA's results are collected in their own board.
- **Optional branches.** Connect a Boolean to Save Enabled so an extra step, for example the upscale, is saved only when you want it.

## Using them

Both nodes are in the `image` category. A typical chain:

<img width="4584" height="2322" alt="board-nodes-demo" src="https://github.com/user-attachments/assets/65bce4f6-adef-4531-8756-958b8627a207" />

### Board by Name

| Input | What it does |
| --- | --- |
| `board_name` | The board's name. Connect it to build the name in the graph, or type it. An empty name is an error. |
| `create_if_missing` | On by default: a board that doesn't exist yet is created. Turn it off to make a missing board an error instead. |

Its output is a board, which can go into any board input that accepts a connection. It is never cached, so a board deleted or renamed since the last run isn't reused by mistake.

### Save to Board (Conditional)

| Input | What it does |
| --- | --- |
| `image` | The image to save. A copy is saved; the original is untouched. |
| Board | A board picker that can also be connected, for example to Board by Name. Uncategorized if unset. |
| Save Enabled | On by default. When off, nothing is saved and the image is passed on unchanged. |
| metadata | If none is connected, the saved copy keeps the input image's own metadata. |
| Save to Gallery | The checkbox at the bottom of the node. It must be on while Save Enabled is on; otherwise the node stops with an error, because the copy would be an intermediate, hidden from the board. InvokeAI adds custom nodes with it off, so turn it on after adding the node. |

The node outputs the saved image (or the input image when Save Enabled is off), so you can put it in the middle of a graph and keep going.

## How board names are matched

- Spaces at the start and end are ignored. Otherwise the name must be exactly the same, including upper and lower case: `Toyrobot` and `toyrobot` are different boards.
- Only your own boards are considered, not boards that other users have shared with you.
- Archived boards are ignored, so archiving a board means "done with this name".
- If two or more of your boards have that name, the node stops with an error that says so. Rename or archive all but one.

## Install

1. Clone this repository into the `nodes` folder of your InvokeAI root (the folder that holds `invokeai.yaml`):

   ```
   cd <invokeai root>/nodes
   git clone https://github.com/unmarco/invokeai-board-nodes
   ```

2. Restart InvokeAI and hard-reload the browser page.
3. Add the nodes in the workflow editor.

Install the nodes before opening workflows that use them. A workflow opened without them loses its connections to the missing nodes, and saving it keeps them lost.

### Upgrading from 1.x

Version 1.x had a single node, Save to Board (Conditional), with `board_name` and `create_if_missing` inputs. In 2.0 those moved to Board by Name. Workflows built with 1.x need a Board by Name node between the name and the save node; the old name connections don't carry over. Version 1.2.0 is tagged if you need it.

## Compatibility

Developed on InvokeAI 6.14.x and tested on 7.0.0-alpha.

A board-by-name lookup for nodes, `context.boards.resolve`, is proposed for InvokeAI itself (prototype on the [`feat/boards-resolve-by-name`](https://github.com/unmarco/InvokeAI/tree/feat/boards-resolve-by-name) branch of my fork). When InvokeAI provides it, Board by Name calls it. Otherwise it does the same thing itself, with the same rules as above.

On 6.14.x, two things to know:

- Boards created while a workflow runs may not show up in the board list until you reload the page. The v7 UI refreshes them when the run ends.
- InvokeAI's `context.boards.get_all()` had a bug in some versions ([#9652](https://github.com/invoke-ai/InvokeAI/issues/9652), fixed in [#9653](https://github.com/invoke-ai/InvokeAI/pull/9653)). Board by Name works around it.

## Tests

The tests need InvokeAI importable, so run them with the Python environment of an InvokeAI install:

```
python -m pytest tests
```

They cover both ways Board by Name finds boards: with and without `context.boards.resolve`.

## License

MIT, see [LICENSE](LICENSE).
