# AGENTS.md - marknotion

Guidelines for AI coding agents working on the marknotion project.

## Project Overview

marknotion is a bidirectional Markdown ↔ Notion blocks converter with CLI tools. It provides:
- `md2notion`: Convert Markdown files to Notion pages
- `notion2md`: Export Notion pages to Markdown
- `notion-search`: Search Notion workspace

**Note**: This is a foundational library used by `bmadnotion`.

## Build/Test/Lint Commands

This project uses **uv** as the package manager (not pip).

```bash
# Install dependencies (including dev)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_md2notion.py

# Run a single test function
uv run pytest tests/test_md2notion.py::test_heading_conversion

# Run tests matching a pattern
uv run pytest -k "test_code"

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=marknotion

# Build package
uv build
```

## Project Structure

```
marknotion/
├── src/marknotion/       # Source code
│   ├── __init__.py       # Package exports
│   ├── cli.py            # Click CLI commands (md2notion, notion2md, etc.)
│   ├── client.py         # NotionClient wrapper for API operations
│   ├── md2notion.py      # Markdown → Notion blocks converter
│   ├── notion2md.py      # Notion blocks → Markdown converter
│   └── types.py          # TypedDict definitions for Notion blocks
├── tests/                # Test files (pytest)
│   ├── test_md2notion.py # Markdown conversion tests
│   └── test_notion2md.py # Notion export tests
└── pyproject.toml        # Project configuration
```

## Code Style Guidelines

### Python Version
- **Python 3.13+** required (see `.python-version`)

### Imports
- Group imports: stdlib → third-party → local
- Use absolute imports for local modules
- No `from __future__ import annotations` in this project (different from bmadnotion)

```python
"""Module docstring."""

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.tasklists import tasklists_plugin

from marknotion.types import NotionBlock
```

### Formatting
- **Line length**: Default (88 characters, black-style)
- Keep functions focused and reasonably sized

### Type Hints
- Use type hints for function signatures
- Use `|` for union types: `str | None`
- Use `Literal` for constrained string values
- Use `TypedDict` for Notion API structures

```python
from typing import Literal, TypedDict

class RichText(TypedDict):
    type: Literal["text"]
    text: TextContent
    annotations: Annotations
    plain_text: str
    href: str | None

def markdown_to_blocks(markdown: str) -> list[dict]:
    ...
```

### TypedDict Usage
- Use `TypedDict` for Notion block type definitions
- Use `total=False` for optional fields
- Document structure in comments

```python
class Annotations(TypedDict, total=False):
    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: str
```

### Naming Conventions
- **Classes**: PascalCase (`NotionClient`, `RichText`)
- **Functions**: snake_case (`markdown_to_blocks`, `blocks_to_markdown`)
- **Constants**: UPPER_SNAKE_CASE (`FRONT_MATTER_RE`)
- **Private helpers**: prefix with underscore (`_make_rich_text`, `_tokens_to_blocks`)

### Docstrings
- Use triple-quoted docstrings for modules and public functions
- Include Args/Returns sections

```python
def markdown_to_blocks(markdown: str) -> list[dict]:
    """Convert Markdown text to a list of Notion block objects.

    Args:
        markdown: Markdown text to convert.

    Returns:
        List of Notion block dictionaries.
    """
```

### Error Handling
- Use descriptive error messages
- Let Notion API errors propagate with context
- Handle edge cases in conversion gracefully

### Conversion Functions
- Functions returning Notion blocks should return `dict` type
- Use helper functions prefixed with `_make_` for block construction
- Handle nested structures (lists, toggles) recursively

```python
def _make_rich_text(content: str, annotations: dict, href: str | None) -> dict:
    """Create a Notion rich text object."""
    return {
        "type": "text",
        "text": {"content": content, "link": {"url": href} if href else None},
        "annotations": annotations,
        "plain_text": content,
        "href": href,
    }

def _make_code_block(code: str, language: str) -> dict:
    """Create a Notion code block."""
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [_make_rich_text(code, {}, None)],
            "language": language,
        },
    }
```

### Testing
- Use pytest with function-based tests
- Test both directions of conversion where applicable
- Test edge cases (empty content, special characters, nested structures)

```python
def test_heading_conversion():
    """Test Markdown headings convert to Notion heading blocks."""
    blocks = markdown_to_blocks("# Heading 1\n## Heading 2")
    
    assert blocks[0]["type"] == "heading_1"
    assert blocks[1]["type"] == "heading_2"

def test_roundtrip():
    """Test Markdown → Notion → Markdown preserves content."""
    original = "# Title\n\nParagraph text."
    blocks = markdown_to_blocks(original)
    result = blocks_to_markdown(blocks)
    assert "Title" in result
    assert "Paragraph text" in result
```

### Key Libraries

- **markdown-it-py**: Markdown parsing (CommonMark compliant)
- **mdit-py-plugins**: Extensions (task lists, footnotes, math, admonitions)
- **notion-client**: Official Notion API client
- **click**: CLI framework

## CI/CD

GitHub Actions workflow runs on push/PR to main:
- **test**: `uv run --extra dev pytest -v`
- **publish**: Triggered on `v*` tags, publishes to PyPI

## API Patterns

### NotionClient Usage

```python
from marknotion import NotionClient

client = NotionClient()  # Uses NOTION_TOKEN env var

# Create page with Markdown content
page = client.create_page(
    parent_id="...",
    title="Page Title",
    markdown="# Content\n\nParagraph.",
)

# Update existing page
client.update_page(page_id="...", markdown="# Updated")

# Export page to Markdown
markdown = client.export_page(page_id="...")
```

### Direct Conversion

```python
from marknotion import markdown_to_blocks, blocks_to_markdown

# Markdown to Notion blocks
blocks = markdown_to_blocks("# Hello\n\n- Item 1\n- Item 2")

# Notion blocks to Markdown
markdown = blocks_to_markdown(blocks)
```
