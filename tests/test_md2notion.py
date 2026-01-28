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
