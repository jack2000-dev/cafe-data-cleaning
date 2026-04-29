# Documentation

Place data dictionaries, project notes, and reference materials here.

## Files

- **`presentation.md`** — 15-minute walkthrough of the cleaning process + EDA findings. Marp-flavored Markdown with speaker notes in HTML comments.

### Rendering the presentation

The file uses [Marp](https://marp.app/) front-matter, so it renders as slides without conversion. Three options:

```bash
# Option 1: VS Code with the "Marp for VS Code" extension — opens a live preview pane
code docs/presentation.md

# Option 2: Marp CLI to PDF
npx @marp-team/marp-cli docs/presentation.md --pdf -o docs/presentation.pdf

# Option 3: Marp CLI to HTML (interactive deck)
npx @marp-team/marp-cli docs/presentation.md --html -o docs/presentation.html
```

The Markdown is also fine to read top-to-bottom in any plain renderer (GitHub, Obsidian) — the `---` slide breaks just look like horizontal rules.

Speaker notes live in `<!-- ... -->` HTML comments after each slide. Marp surfaces them in presenter mode; plain renderers ignore them.
