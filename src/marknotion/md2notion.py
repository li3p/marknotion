"""Markdown to Notion blocks converter."""

from markdown_it import MarkdownIt
from markdown_it.token import Token


def markdown_to_blocks(markdown: str) -> list[dict]:
    """Convert Markdown text to a list of Notion block objects.

    Args:
        markdown: Markdown text to convert.

    Returns:
        List of Notion block dictionaries.
    """
    md = MarkdownIt("commonmark")
    tokens = md.parse(markdown)
    return _tokens_to_blocks(tokens)


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

        else:
            i += 1

    return blocks


def _parse_list(tokens: list[Token], list_type: str) -> tuple[list[dict], int]:
    """Parse a list (bullet or ordered) and return blocks and consumed count."""
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
            # Find the content of this list item
            item_content: list[dict] = []
            i += 1
            while i < len(tokens) and tokens[i].type != "list_item_close":
                if tokens[i].type == "paragraph_open":
                    inline_token = tokens[i + 1]
                    rich_text = _inline_to_rich_text(inline_token.children or [])
                    item_content.append({"rich_text": rich_text})
                    i += 3
                elif tokens[i].type in ("bullet_list_open", "ordered_list_open"):
                    # Nested list - for now, skip
                    nested_depth = 1
                    i += 1
                    while i < len(tokens) and nested_depth > 0:
                        if tokens[i].type in ("bullet_list_open", "ordered_list_open"):
                            nested_depth += 1
                        elif tokens[i].type in ("bullet_list_close", "ordered_list_close"):
                            nested_depth -= 1
                        i += 1
                else:
                    i += 1

            if item_content:
                blocks.append(_make_list_item_block(list_type, item_content[0]["rich_text"]))
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
