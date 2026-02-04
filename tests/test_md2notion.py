"""Tests for Markdown to Notion conversion."""

import pytest
from marknotion import markdown_to_blocks


class TestHeadings:
    def test_heading_1(self):
        blocks = markdown_to_blocks("# Hello")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["heading_1"]["rich_text"][0]["plain_text"] == "Hello"

    def test_heading_2(self):
        blocks = markdown_to_blocks("## World")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"

    def test_heading_3(self):
        blocks = markdown_to_blocks("### Test")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"


class TestParagraph:
    def test_simple_paragraph(self):
        blocks = markdown_to_blocks("Hello world")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["plain_text"] == "Hello world"

    def test_multiple_paragraphs(self):
        blocks = markdown_to_blocks("First\n\nSecond")
        assert len(blocks) == 2
        assert blocks[0]["paragraph"]["rich_text"][0]["plain_text"] == "First"
        assert blocks[1]["paragraph"]["rich_text"][0]["plain_text"] == "Second"


class TestInlineFormatting:
    def test_bold(self):
        blocks = markdown_to_blocks("**bold**")
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "bold"
        assert rich_text["annotations"]["bold"] is True

    def test_italic(self):
        blocks = markdown_to_blocks("*italic*")
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "italic"
        assert rich_text["annotations"]["italic"] is True

    def test_code_inline(self):
        blocks = markdown_to_blocks("`code`")
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "code"
        assert rich_text["annotations"]["code"] is True

    def test_link(self):
        blocks = markdown_to_blocks("[text](https://example.com)")
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "text"
        assert rich_text["href"] == "https://example.com"


class TestLists:
    def test_bullet_list(self):
        md = "- Item 1\n- Item 2\n- Item 3"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 3
        assert all(b["type"] == "bulleted_list_item" for b in blocks)
        assert blocks[0]["bulleted_list_item"]["rich_text"][0]["plain_text"] == "Item 1"

    def test_ordered_list(self):
        md = "1. First\n2. Second\n3. Third"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 3
        assert all(b["type"] == "numbered_list_item" for b in blocks)


class TestCodeBlock:
    def test_code_block_with_language(self):
        md = "```python\nprint('hello')\n```"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert blocks[0]["code"]["rich_text"][0]["plain_text"] == "print('hello')"

    def test_code_block_no_language(self):
        md = "```\nsome code\n```"
        blocks = markdown_to_blocks(md)
        assert blocks[0]["code"]["language"] == "plain text"

    def test_code_block_long_content_split(self):
        """Code blocks >2000 chars should be split into multiple rich_text items."""
        content = "x" * 2500
        md = f"```\n{content}\n```"
        blocks = markdown_to_blocks(md)
        rich_text = blocks[0]["code"]["rich_text"]
        assert len(rich_text) == 2
        assert len(rich_text[0]["plain_text"]) == 2000
        assert len(rich_text[1]["plain_text"]) == 500

    def test_code_block_split_respects_utf16_length(self):
        """Splitting must count UTF-16 code units, not Python codepoints.

        Emoji like 📋 (U+1F4CB) are 1 Python char but 2 UTF-16 code units.
        A string of 1000 such emoji is 1000 Python chars but 2000 UTF-16 units,
        so it should fit in one rich_text item.  1001 emoji = 2002 UTF-16 units
        and must be split.
        """
        # 1000 emoji = 2000 UTF-16 units → fits in one chunk
        content = "📋" * 1000
        md = f"```\n{content}\n```"
        blocks = markdown_to_blocks(md)
        rich_text = blocks[0]["code"]["rich_text"]
        assert len(rich_text) == 1

        # 1001 emoji = 2002 UTF-16 units → must split
        content = "📋" * 1001
        md = f"```\n{content}\n```"
        blocks = markdown_to_blocks(md)
        rich_text = blocks[0]["code"]["rich_text"]
        assert len(rich_text) == 2
        assert rich_text[0]["plain_text"] == "📋" * 1000
        assert rich_text[1]["plain_text"] == "📋"

    def test_code_block_split_mixed_ascii_and_emoji(self):
        """Mix of ASCII (1 UTF-16 unit) and emoji (2 UTF-16 units)."""
        # 1997 ASCII chars + 1 emoji = 1997 + 2 = 1999 UTF-16 units → one chunk
        content = "a" * 1997 + "📋"
        md = f"```\n{content}\n```"
        blocks = markdown_to_blocks(md)
        assert len(blocks[0]["code"]["rich_text"]) == 1

        # 1999 ASCII chars + 1 emoji = 1999 + 2 = 2001 UTF-16 units → two chunks
        content = "a" * 1999 + "📋"
        md = f"```\n{content}\n```"
        blocks = markdown_to_blocks(md)
        rich_text = blocks[0]["code"]["rich_text"]
        assert len(rich_text) == 2
        assert rich_text[0]["plain_text"] == "a" * 1999
        assert rich_text[1]["plain_text"] == "📋"


class TestQuote:
    def test_blockquote(self):
        blocks = markdown_to_blocks("> This is a quote")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "quote"
        assert blocks[0]["quote"]["rich_text"][0]["plain_text"] == "This is a quote"


class TestDivider:
    def test_horizontal_rule(self):
        blocks = markdown_to_blocks("---")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "divider"


class TestMixedContent:
    def test_heading_and_paragraph(self):
        md = "# Title\n\nSome content"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "heading_1"
        assert blocks[1]["type"] == "paragraph"


class TestStrikethrough:
    def test_strikethrough(self):
        blocks = markdown_to_blocks("~~deleted~~")
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "deleted"
        assert rich_text["annotations"]["strikethrough"] is True


class TestTaskList:
    def test_unchecked_task(self):
        md = "- [ ] Task to do"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["checked"] is False
        assert blocks[0]["to_do"]["rich_text"][0]["plain_text"] == "Task to do"

    def test_checked_task(self):
        md = "- [x] Done task"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["checked"] is True

    def test_multiple_tasks(self):
        md = "- [ ] First\n- [x] Second\n- [ ] Third"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 3
        assert all(b["type"] == "to_do" for b in blocks)
        assert blocks[0]["to_do"]["checked"] is False
        assert blocks[1]["to_do"]["checked"] is True
        assert blocks[2]["to_do"]["checked"] is False


class TestTable:
    def test_simple_table(self):
        md = """| Name | Age |
| --- | --- |
| Alice | 30 |
| Bob | 25 |"""
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "table"
        table = blocks[0]["table"]
        assert table["table_width"] == 2
        assert len(table["children"]) == 3  # header + 2 rows

    def test_table_content(self):
        md = """| A | B |
| --- | --- |
| 1 | 2 |"""
        blocks = markdown_to_blocks(md)
        table = blocks[0]["table"]
        children = table["children"]
        # First row (header)
        assert children[0]["type"] == "table_row"
        cells = children[0]["table_row"]["cells"]
        assert cells[0][0]["plain_text"] == "A"
        assert cells[1][0]["plain_text"] == "B"


class TestNestedLists:
    def test_nested_bullet_list(self):
        md = """- Parent
    - Child 1
    - Child 2"""
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "bulleted_list_item"
        children = blocks[0]["bulleted_list_item"].get("children", [])
        assert len(children) == 2
        assert all(c["type"] == "bulleted_list_item" for c in children)

    def test_nested_mixed_list(self):
        md = """1. First
    - Nested bullet
    - Another bullet
2. Second"""
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "numbered_list_item"
        children = blocks[0]["numbered_list_item"].get("children", [])
        assert len(children) == 2


class TestImage:
    def test_inline_image(self):
        md = "![alt text](https://example.com/image.png)"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        # Image in paragraph context becomes a link
        rich_text = blocks[0]["paragraph"]["rich_text"][0]
        assert rich_text["plain_text"] == "alt text"
        assert rich_text["href"] == "https://example.com/image.png"


class TestMathEquation:
    def test_inline_math(self):
        md = "The formula is $x^2 + y^2 = z^2$ here."
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        rich_text = blocks[0]["paragraph"]["rich_text"]
        # Should have text, equation, text
        assert any(rt.get("type") == "equation" for rt in rich_text)
        equation_rt = [rt for rt in rich_text if rt.get("type") == "equation"][0]
        assert equation_rt["equation"]["expression"] == "x^2 + y^2 = z^2"

    def test_block_math(self):
        md = "$$\nE = mc^2\n$$"
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "equation"
        assert blocks[0]["equation"]["expression"] == "E = mc^2"

    def test_block_math_multiline(self):
        md = "$$\n\\frac{a}{b}\n$$"
        blocks = markdown_to_blocks(md)
        assert blocks[0]["type"] == "equation"


class TestCallout:
    def test_note_admonition(self):
        md = '!!! note "Important"\n    This is a note.'
        blocks = markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["icon"]["emoji"] == "📝"

    def test_warning_admonition(self):
        md = "!!! warning\n    Be careful!"
        blocks = markdown_to_blocks(md)
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["icon"]["emoji"] == "⚠️"

    def test_tip_admonition(self):
        md = "!!! tip\n    A helpful tip."
        blocks = markdown_to_blocks(md)
        assert blocks[0]["callout"]["icon"]["emoji"] == "💡"


class TestFootnote:
    def test_footnote_reference(self):
        md = "Text with footnote[^1].\n\n[^1]: This is the footnote."
        blocks = markdown_to_blocks(md)
        # Should have paragraph with reference and footnote callout
        assert len(blocks) >= 1
        # First block is paragraph with footnote ref
        para = blocks[0]
        assert para["type"] == "paragraph"
        rich_text = para["paragraph"]["rich_text"]
        # Should contain [1] marker
        full_text = "".join(rt.get("plain_text", "") for rt in rich_text)
        assert "[1]" in full_text

    def test_footnote_content(self):
        md = "Text[^note].\n\n[^note]: The note content."
        blocks = markdown_to_blocks(md)
        # Should have footnote as callout
        callouts = [b for b in blocks if b.get("type") == "callout"]
        assert len(callouts) >= 1
