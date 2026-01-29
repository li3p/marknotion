"""Markdown to Notion blocks converter."""

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.admon import admon_plugin


# Regex to match YAML front matter at the start of document
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _extract_front_matter(markdown: str) -> tuple[str | None, str]:
    """Extract YAML front matter from markdown.

    Returns:
        Tuple of (front_matter_content, remaining_markdown).
        front_matter_content is None if no front matter found.
    """
    match = FRONT_MATTER_RE.match(markdown)
    if match:
        front_matter = match.group(1)
        remaining = markdown[match.end():]
        return front_matter, remaining
    return None, markdown


def _make_toggle_block(title: str, children: list[dict]) -> dict:
    """Create a Notion toggle block with children."""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [_make_rich_text(title, {}, None)],
            "children": children,
        },
    }


def markdown_to_blocks(markdown: str) -> list[dict]:
    """Convert Markdown text to a list of Notion block objects.

    Args:
        markdown: Markdown text to convert.

    Returns:
        List of Notion block dictionaries.
    """
    blocks: list[dict] = []

    # Extract front matter if present
    front_matter, markdown = _extract_front_matter(markdown)
    if front_matter:
        # Create toggle block with code block inside
        code_block = _make_code_block(front_matter, "yaml")
        toggle_block = _make_toggle_block("📋 Front Matter", [code_block])
        blocks.append(toggle_block)

    md = MarkdownIt("commonmark")
    md.enable("strikethrough")
    md.enable("table")
    md.use(tasklists_plugin)
    md.use(dollarmath_plugin, allow_space=True, allow_digits=True)
    md.use(admon_plugin)
    md.use(footnote_plugin)
    tokens = md.parse(markdown)
    blocks.extend(_tokens_to_blocks(tokens))

    return blocks


def _tokens_to_blocks(tokens: list[Token]) -> list[dict]:
    """Convert markdown-it tokens to Notion blocks."""
    blocks: list[dict] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            # Next token is inline content
            inline_token = tokens[i + 1]
            rich_text = _inline_to_rich_text(inline_token.children or [])
            blocks.append(_make_heading_block(level, rich_text))
            i += 3  # heading_open, inline, heading_close

        elif token.type == "paragraph_open":
            inline_token = tokens[i + 1]
            rich_text = _inline_to_rich_text(inline_token.children or [])
            blocks.append(_make_paragraph_block(rich_text))
            i += 3  # paragraph_open, inline, paragraph_close

        elif token.type == "bullet_list_open":
            # Collect all list items until bullet_list_close
            list_blocks, consumed = _parse_list(tokens[i:], "bulleted_list_item")
            blocks.extend(list_blocks)
            i += consumed

        elif token.type == "ordered_list_open":
            list_blocks, consumed = _parse_list(tokens[i:], "numbered_list_item")
            blocks.extend(list_blocks)
            i += consumed

        elif token.type == "fence":
            language = token.info or "plain text"
            content = token.content.rstrip("\n")
            blocks.append(_make_code_block(content, language))
            i += 1

        elif token.type == "code_block":
            content = token.content.rstrip("\n")
            blocks.append(_make_code_block(content, "plain text"))
            i += 1

        elif token.type == "blockquote_open":
            quote_blocks, consumed = _parse_blockquote(tokens[i:])
            blocks.extend(quote_blocks)
            i += consumed

        elif token.type == "hr":
            blocks.append(_make_divider_block())
            i += 1

        elif token.type == "table_open":
            table_block, consumed = _parse_table(tokens[i:])
            if table_block:
                blocks.append(table_block)
            i += consumed

        elif token.type == "math_block":
            expression = token.content.strip()
            blocks.append(_make_equation_block(expression))
            i += 1

        elif token.type == "admonition_open":
            admon_block, consumed = _parse_admonition(tokens[i:])
            if admon_block:
                blocks.append(admon_block)
            i += consumed

        elif token.type == "footnote_block_open":
            footnote_blocks, consumed = _parse_footnote_block(tokens[i:])
            blocks.extend(footnote_blocks)
            i += consumed

        else:
            i += 1

    return blocks


def _parse_list(tokens: list[Token], list_type: str) -> tuple[list[dict], int]:
    """Parse a list (bullet or ordered) and return blocks and consumed count.

    Supports task lists (checkboxes) and nested lists.
    """
    blocks: list[dict] = []
    i = 1  # Skip the list_open token
    depth = 1

    while i < len(tokens) and depth > 0:
        token = tokens[i]

        if token.type in ("bullet_list_open", "ordered_list_open"):
            depth += 1
            i += 1
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            depth -= 1
            i += 1
        elif token.type == "list_item_open" and depth == 1:
            # Check if this is a task list item
            is_task = token.attrGet("class") == "task-list-item"
            is_checked = False

            i += 1
            item_rich_text: list[dict] = []
            children_blocks: list[dict] = []

            while i < len(tokens) and tokens[i].type != "list_item_close":
                if tokens[i].type == "paragraph_open":
                    inline_token = tokens[i + 1]
                    inline_children = inline_token.children or []

                    # Check for checkbox in task list (html_inline token)
                    if is_task and inline_children:
                        first_child = inline_children[0]
                        if first_child.type == "html_inline" and "checkbox" in first_child.content:
                            is_checked = 'checked="checked"' in first_child.content
                            # Skip the checkbox token and leading space in next token
                            inline_children = inline_children[1:]
                            # Remove leading space from text
                            if inline_children and inline_children[0].type == "text":
                                inline_children[0].content = inline_children[0].content.lstrip()

                    item_rich_text = _inline_to_rich_text(inline_children)
                    i += 3
                elif tokens[i].type in ("bullet_list_open", "ordered_list_open"):
                    # Nested list - parse recursively
                    nested_type = "bulleted_list_item" if tokens[i].type == "bullet_list_open" else "numbered_list_item"
                    nested_blocks, consumed = _parse_list(tokens[i:], nested_type)
                    children_blocks.extend(nested_blocks)
                    i += consumed
                else:
                    i += 1

            if item_rich_text or is_task:
                if is_task:
                    block = _make_todo_block(item_rich_text, is_checked)
                else:
                    block = _make_list_item_block(list_type, item_rich_text)

                # Add nested children
                if children_blocks:
                    block[block["type"]]["children"] = children_blocks

                blocks.append(block)
            i += 1  # Skip list_item_close
        else:
            i += 1

    return blocks, i


def _parse_blockquote(tokens: list[Token]) -> tuple[list[dict], int]:
    """Parse a blockquote and return blocks and consumed count."""
    blocks: list[dict] = []
    i = 1  # Skip blockquote_open
    depth = 1
    quote_text: list[dict] = []

    while i < len(tokens) and depth > 0:
        token = tokens[i]

        if token.type == "blockquote_open":
            depth += 1
            i += 1
        elif token.type == "blockquote_close":
            depth -= 1
            i += 1
        elif token.type == "paragraph_open" and depth == 1:
            inline_token = tokens[i + 1]
            rich_text = _inline_to_rich_text(inline_token.children or [])
            quote_text.extend(rich_text)
            i += 3
        else:
            i += 1

    if quote_text:
        blocks.append(_make_quote_block(quote_text))

    return blocks, i


def _inline_to_rich_text(tokens: list[Token]) -> list[dict]:
    """Convert inline tokens to Notion rich_text array."""
    rich_text: list[dict] = []
    annotations: dict = {}
    link_href: str | None = None

    for token in tokens:
        if token.type == "text":
            if token.content:  # Skip empty text tokens
                rich_text.append(_make_rich_text(token.content, annotations.copy(), link_href))
        elif token.type == "code_inline":
            rich_text.append(_make_rich_text(token.content, {"code": True}, None))
        elif token.type == "strong_open":
            annotations["bold"] = True
        elif token.type == "strong_close":
            annotations.pop("bold", None)
        elif token.type == "em_open":
            annotations["italic"] = True
        elif token.type == "em_close":
            annotations.pop("italic", None)
        elif token.type == "s_open":
            annotations["strikethrough"] = True
        elif token.type == "s_close":
            annotations.pop("strikethrough", None)
        elif token.type == "link_open":
            link_href = token.attrGet("href")
        elif token.type == "link_close":
            link_href = None
        elif token.type == "softbreak":
            rich_text.append(_make_rich_text("\n", {}, None))
        elif token.type == "hardbreak":
            rich_text.append(_make_rich_text("\n", {}, None))
        elif token.type == "image":
            # Images in inline context - add alt text as link
            alt = token.attrGet("alt") or token.content or "image"
            src = token.attrGet("src") or ""
            rich_text.append(_make_rich_text(alt, {}, src))
        elif token.type == "math_inline":
            # Inline math - wrap in equation notation
            rich_text.append(_make_equation_rich_text(token.content))
        elif token.type == "footnote_ref":
            # Footnote reference - add as superscript-style text
            label = token.meta.get("label", "?") if token.meta else "?"
            rich_text.append(_make_rich_text(f"[{label}]", {}, None))

    return rich_text


def _make_rich_text(content: str, annotations: dict, href: str | None) -> dict:
    """Create a Notion rich_text object."""
    text_obj: dict = {"content": content}
    if href:
        text_obj["link"] = {"url": href}

    result: dict = {
        "type": "text",
        "text": text_obj,
        "plain_text": content,
        "href": href,
    }

    # Only include non-default annotations
    if annotations:
        result["annotations"] = annotations

    return result


def _make_paragraph_block(rich_text: list[dict]) -> dict:
    """Create a Notion paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text},
    }


def _make_heading_block(level: int, rich_text: list[dict]) -> dict:
    """Create a Notion heading block."""
    # Notion only supports heading_1, heading_2, heading_3
    level = min(level, 3)
    heading_type = f"heading_{level}"
    return {
        "object": "block",
        "type": heading_type,
        heading_type: {"rich_text": rich_text},
    }


def _make_list_item_block(list_type: str, rich_text: list[dict]) -> dict:
    """Create a Notion list item block."""
    return {
        "object": "block",
        "type": list_type,
        list_type: {"rich_text": rich_text},
    }


def _make_code_block(content: str, language: str) -> dict:
    """Create a Notion code block."""
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [_make_rich_text(content, {}, None)],
            "language": language,
        },
    }


def _make_quote_block(rich_text: list[dict]) -> dict:
    """Create a Notion quote block."""
    return {
        "object": "block",
        "type": "quote",
        "quote": {"rich_text": rich_text},
    }


def _make_divider_block() -> dict:
    """Create a Notion divider block."""
    return {
        "object": "block",
        "type": "divider",
        "divider": {},
    }


def _make_todo_block(rich_text: list[dict], checked: bool) -> dict:
    """Create a Notion to_do block."""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": rich_text,
            "checked": checked,
        },
    }


def _make_equation_block(expression: str) -> dict:
    """Create a Notion equation block."""
    return {
        "object": "block",
        "type": "equation",
        "equation": {
            "expression": expression,
        },
    }


def _make_equation_rich_text(expression: str) -> dict:
    """Create a Notion inline equation rich_text object."""
    return {
        "type": "equation",
        "equation": {
            "expression": expression,
        },
        "plain_text": expression,
        "href": None,
    }


# Mapping of admonition types to Notion callout icons
ADMON_ICONS = {
    "note": "📝",
    "info": "ℹ️",
    "tip": "💡",
    "hint": "💡",
    "important": "❗",
    "warning": "⚠️",
    "caution": "⚠️",
    "danger": "🔴",
    "error": "❌",
    "bug": "🐛",
    "example": "📋",
    "quote": "💬",
    "footnote": "📌",
}


def _make_callout_block(admon_type: str, title: str, rich_text: list[dict]) -> dict:
    """Create a Notion callout block from admonition."""
    icon = ADMON_ICONS.get(admon_type.lower(), "📝")

    # If title exists and differs from type, prepend it
    if title and title.lower() != admon_type.lower():
        title_text = _make_rich_text(f"{title}: ", {"bold": True}, None)
        rich_text = [title_text] + rich_text

    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich_text,
            "icon": {"type": "emoji", "emoji": icon},
        },
    }


def _make_image_block(url: str, caption: str = "") -> dict:
    """Create a Notion image block."""
    block: dict = {
        "object": "block",
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": url},
        },
    }
    if caption:
        block["image"]["caption"] = [_make_rich_text(caption, {}, None)]
    return block


def _make_table_block(rows: list[list[list[dict]]], has_header: bool = True) -> dict:
    """Create a Notion table block.

    Args:
        rows: List of rows, each row is a list of cells, each cell is rich_text list
        has_header: Whether first row is a header
    """
    if not rows:
        return {}

    table_width = len(rows[0]) if rows else 0

    children = []
    for row in rows:
        # Pad row to table_width if needed
        cells = row + [[] for _ in range(table_width - len(row))]
        children.append({
            "object": "block",
            "type": "table_row",
            "table_row": {"cells": cells[:table_width]},
        })

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": table_width,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": children,
        },
    }


def _parse_admonition(tokens: list[Token]) -> tuple[dict | None, int]:
    """Parse an admonition/callout block."""
    i = 0
    token = tokens[i]

    # Get admonition type and title from meta
    admon_type = token.meta.get("tag", "note") if token.meta else "note"
    i += 1

    title = ""
    content_rich_text: list[dict] = []

    while i < len(tokens) and tokens[i].type != "admonition_close":
        if tokens[i].type == "admonition_title_open":
            i += 1
            if i < len(tokens) and tokens[i].type == "inline":
                title = tokens[i].content
                i += 1
            if i < len(tokens) and tokens[i].type == "admonition_title_close":
                i += 1
        elif tokens[i].type == "paragraph_open":
            inline_token = tokens[i + 1]
            rich_text = _inline_to_rich_text(inline_token.children or [])
            content_rich_text.extend(rich_text)
            i += 3
        else:
            i += 1

    i += 1  # Skip admonition_close

    return _make_callout_block(admon_type, title, content_rich_text), i


def _parse_footnote_block(tokens: list[Token]) -> tuple[list[dict], int]:
    """Parse footnote block and return as quote blocks with footnote prefix."""
    blocks: list[dict] = []
    i = 1  # Skip footnote_block_open

    while i < len(tokens) and tokens[i].type != "footnote_block_close":
        if tokens[i].type == "footnote_open":
            label = tokens[i].meta.get("label", "?") if tokens[i].meta else "?"
            i += 1

            footnote_content: list[dict] = []
            while i < len(tokens) and tokens[i].type != "footnote_close":
                if tokens[i].type == "paragraph_open":
                    inline_token = tokens[i + 1]
                    # Filter out footnote_anchor tokens
                    children = [c for c in (inline_token.children or [])
                               if c.type != "footnote_anchor"]
                    rich_text = _inline_to_rich_text(children)
                    footnote_content.extend(rich_text)
                    i += 3
                else:
                    i += 1

            # Create footnote as a callout with footnote icon
            if footnote_content:
                prefix_text = _make_rich_text(f"[{label}] ", {"bold": True}, None)
                blocks.append(_make_callout_block(
                    "footnote",
                    f"Footnote {label}",
                    [prefix_text] + footnote_content
                ))
            i += 1  # Skip footnote_close
        else:
            i += 1

    i += 1  # Skip footnote_block_close
    return blocks, i


def _parse_table(tokens: list[Token]) -> tuple[dict | None, int]:
    """Parse a table and return block and consumed count."""
    rows: list[list[list[dict]]] = []
    i = 1  # Skip table_open
    has_header = False
    current_row: list[list[dict]] = []

    while i < len(tokens) and tokens[i].type != "table_close":
        token = tokens[i]

        if token.type == "thead_open":
            has_header = True
            i += 1
        elif token.type == "thead_close":
            i += 1
        elif token.type == "tbody_open":
            i += 1
        elif token.type == "tbody_close":
            i += 1
        elif token.type == "tr_open":
            current_row = []
            i += 1
        elif token.type == "tr_close":
            if current_row:
                rows.append(current_row)
            i += 1
        elif token.type in ("th_open", "td_open"):
            i += 1
        elif token.type in ("th_close", "td_close"):
            i += 1
        elif token.type == "inline":
            cell_content = _inline_to_rich_text(token.children or [])
            current_row.append(cell_content)
            i += 1
        else:
            i += 1

    i += 1  # Skip table_close

    if rows:
        return _make_table_block(rows, has_header), i
    return None, i
