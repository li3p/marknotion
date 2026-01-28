# marknotion

Bidirectional Markdown to Notion blocks converter.

## Installation

```bash
pip install marknotion
```

## Usage

```python
from marknotion import markdown_to_blocks, blocks_to_markdown

# Markdown -> Notion blocks
blocks = markdown_to_blocks("# Hello\n\nWorld")

# Notion blocks -> Markdown
md = blocks_to_markdown(blocks)
```

## Supported Features

- Headings (h1-h3)
- Paragraphs
- Bold, italic, strikethrough, inline code
- Links
- Bullet lists, numbered lists
- Code blocks (with language)
- Blockquotes
- Horizontal rules

## License

MIT
