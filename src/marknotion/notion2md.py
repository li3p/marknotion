"""Notion blocks to Markdown converter."""


def blocks_to_markdown(blocks: list[dict], indent: int = 0) -> str:
    """Convert a list of Notion block objects to Markdown text.

    Args:
        blocks: List of Notion block dictionaries.
        indent: Indentation level for nested content.

    Returns:
        Markdown text.
    """
    lines: list[str] = []
    prev_type: str | None = None
    indent_str = "    " * indent  # 4 spaces per level

    for block in blocks:
        block_type = block.get("type", "")
        content = _block_to_markdown(block, indent)

        # Add blank line between different block types (except consecutive list items)
        if prev_type and content:
            is_list_continuation = (
                prev_type in ("bulleted_list_item", "numbered_list_item", "to_do")
                and block_type in ("bulleted_list_item", "numbered_list_item", "to_do")
            )
            if not is_list_continuation:
                lines.append("")

        if content:
            lines.append(content)
            prev_type = block_type

    return "\n".join(lines)


def _block_to_markdown(block: dict, indent: int = 0) -> str:
    """Convert a single Notion block to Markdown."""
    block_type = block.get("type", "")
    data = block.get(block_type, {})
    indent_str = "    " * indent

    if block_type == "paragraph":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"{indent_str}{text}"

    elif block_type == "heading_1":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"{indent_str}# {text}"

    elif block_type == "heading_2":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"{indent_str}## {text}"

    elif block_type == "heading_3":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        return f"{indent_str}### {text}"

    elif block_type == "bulleted_list_item":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        result = f"{indent_str}- {text}"
        # Handle nested children
        children = data.get("children", [])
        if children:
            child_md = blocks_to_markdown(children, indent + 1)
            result += "\n" + child_md
        return result

    elif block_type == "numbered_list_item":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        result = f"{indent_str}1. {text}"
        # Handle nested children
        children = data.get("children", [])
        if children:
            child_md = blocks_to_markdown(children, indent + 1)
            result += "\n" + child_md
        return result

    elif block_type == "to_do":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        checked = data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        result = f"{indent_str}- {checkbox} {text}"
        # Handle nested children
        children = data.get("children", [])
        if children:
            child_md = blocks_to_markdown(children, indent + 1)
            result += "\n" + child_md
        return result

    elif block_type == "code":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        language = data.get("language", "")
        if language == "plain text":
            language = ""
        return f"{indent_str}```{language}\n{text}\n{indent_str}```"

    elif block_type == "quote":
        text = _rich_text_to_markdown(data.get("rich_text", []))
        lines = text.split("\n")
        return "\n".join(f"{indent_str}> {line}" for line in lines)

    elif block_type == "divider":
        return f"{indent_str}---"

    elif block_type == "image":
        image_data = data
        url = ""
        if image_data.get("type") == "external":
            url = image_data.get("external", {}).get("url", "")
        elif image_data.get("type") == "file":
            url = image_data.get("file", {}).get("url", "")

        caption_list = image_data.get("caption", [])
        caption = _rich_text_to_markdown(caption_list) if caption_list else ""
        alt = caption or "image"
        return f"{indent_str}![{alt}]({url})"

    elif block_type == "table":
        return _table_to_markdown(data, indent_str)

    elif block_type == "table_row":
        # Handled by table block
        return ""

    elif block_type == "equation":
        expression = data.get("expression", "")
        return f"{indent_str}$$\n{expression}\n$$"

    elif block_type == "callout":
        return _callout_to_markdown(data, indent_str)

    return ""


def _table_to_markdown(data: dict, indent_str: str = "") -> str:
    """Convert Notion table block to Markdown table."""
    children = data.get("children", [])
    has_header = data.get("has_column_header", False)

    if not children:
        return ""

    rows: list[list[str]] = []
    for child in children:
        if child.get("type") == "table_row":
            cells = child.get("table_row", {}).get("cells", [])
            row = [_rich_text_to_markdown(cell) for cell in cells]
            rows.append(row)

    if not rows:
        return ""

    # Determine column widths (minimum 3 for markdown separator)
    col_count = max(len(row) for row in rows) if rows else 0
    col_widths = [3] * col_count
    for row in rows:
        for i, cell in enumerate(row):
            if i < col_count:
                col_widths[i] = max(col_widths[i], len(cell))

    lines: list[str] = []

    # Header row
    if rows:
        header = rows[0]
        header_cells = [cell.ljust(col_widths[i]) if i < len(col_widths) else cell
                       for i, cell in enumerate(header)]
        # Pad if needed
        while len(header_cells) < col_count:
            header_cells.append(" " * col_widths[len(header_cells)])
        lines.append(f"{indent_str}| " + " | ".join(header_cells) + " |")

        # Separator
        sep_cells = ["-" * col_widths[i] for i in range(col_count)]
        lines.append(f"{indent_str}| " + " | ".join(sep_cells) + " |")

        # Data rows
        for row in rows[1:]:
            row_cells = [cell.ljust(col_widths[i]) if i < len(col_widths) else cell
                        for i, cell in enumerate(row)]
            while len(row_cells) < col_count:
                row_cells.append(" " * col_widths[len(row_cells)])
            lines.append(f"{indent_str}| " + " | ".join(row_cells) + " |")

    return "\n".join(lines)


def _callout_to_markdown(data: dict, indent_str: str = "") -> str:
    """Convert Notion callout block to Markdown admonition."""
    rich_text = data.get("rich_text", [])
    icon_data = data.get("icon", {})

    # Try to determine admonition type from icon
    admon_type = "note"
    if icon_data.get("type") == "emoji":
        emoji = icon_data.get("emoji", "")
        # Reverse lookup from emoji to type
        icon_to_type = {
            "📝": "note",
            "ℹ️": "info",
            "💡": "tip",
            "❗": "important",
            "⚠️": "warning",
            "🔴": "danger",
            "❌": "error",
            "🐛": "bug",
            "📋": "example",
            "💬": "quote",
            "📌": "footnote",
        }
        admon_type = icon_to_type.get(emoji, "note")

    text = _rich_text_to_markdown(rich_text)

    # Format as admonition
    lines = text.split("\n")
    result = [f"{indent_str}!!! {admon_type}"]
    for line in lines:
        result.append(f"{indent_str}    {line}")

    return "\n".join(result)


def _rich_text_to_markdown(rich_text: list[dict]) -> str:
    """Convert Notion rich_text array to Markdown string."""
    parts: list[str] = []

    for item in rich_text:
        item_type = item.get("type", "text")

        # Handle inline equations
        if item_type == "equation":
            expression = item.get("equation", {}).get("expression", "")
            parts.append(f"${expression}$")
            continue

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
