"""Notion blocks to Markdown converter."""


def blocks_to_markdown(blocks: list[dict]) -> str:
    """Convert a list of Notion block objects to Markdown text.

    Args:
        blocks: List of Notion block dictionaries.

    Returns:
        Markdown text.
    """
    lines: list[str] = []
    prev_type: str | None = None

    for block in blocks:
        block_type = block.get("type", "")
        content = _block_to_markdown(block)

        # Add blank line between different block types (except consecutive list items)
        if prev_type and content:
            is_list_continuation = (
                prev_type in ("bulleted_list_item", "numbered_list_item")
                and block_type in ("bulleted_list_item", "numbered_list_item")
            )
            if not is_list_continuation:
                lines.append("")

        if content:
            lines.append(content)
            prev_type = block_type

    return "\n".join(lines)


def _block_to_markdown(block: dict) -> str:
    """Convert a single Notion block to Markdown."""
    block_type = block.get("type", "")
    data = block.get(block_type, {})

    if block_type == "paragraph":
        return _rich_text_to_markdown(data.get("rich_text", []))

    elif block_type == "heading_1":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"# {text}"

    elif block_type == "heading_2":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"## {text}"

    elif block_type == "heading_3":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"### {text}"

    elif block_type == "bulleted_list_item":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"- {text}"

    elif block_type == "numbered_list_item":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"1. {text}"

    elif block_type == "code":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        language = data.get("language", "")
        if language == "plain text":
            language = ""
        return f"```{language}\n{text}\n```"

    elif block_type == "quote":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        # Handle multi-line quotes
        lines = text.split("\n")
        return "\n".join(f"> {line}" for line in lines)

    elif block_type == "divider":
        return "---"

    elif block_type == "to_do":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        checked = data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        return f"- {checkbox} {text}"

    return ""


def _rich_text_to_markdown(rich_text: list[dict]) -> str:
    """Convert Notion rich_text array to Markdown string."""
    parts: list[str] = []

    for item in rich_text:
        text = item.get("plain_text", "")
        if not text:
            text_obj = item.get("text", {})
            text = text_obj.get("content", "")

        annotations = item.get("annotations", {})
        href = item.get("href")

        # Apply formatting in order: code, bold, italic, strikethrough
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"

        # Apply link
        if href:
            text = f"[{text}]({href})"

        parts.append(text)

    return "".join(parts)
