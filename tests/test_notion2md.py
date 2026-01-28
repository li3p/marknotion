"""Tests for Notion to Markdown conversion."""

import pytest
from marknotion import blocks_to_markdown


class TestHeadings:
    def test_heading_1(self):
        blocks = [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"plain_text": "Hello"}]},
            }
        ]
        assert blocks_to_markdown(blocks) == "# Hello"

    def test_heading_2(self):
        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"plain_text": "World"}]},
            }
        ]
        assert blocks_to_markdown(blocks) == "## World"

    def test_heading_3(self):
        blocks = [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"plain_text": "Test"}]},
            }
        ]
        assert blocks_to_markdown(blocks) == "### Test"


class TestParagraph:
    def test_simple_paragraph(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Hello world"}]},
            }
        ]
        assert blocks_to_markdown(blocks) == "Hello world"

    def test_multiple_paragraphs(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "First"}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"plain_text": "Second"}]},
            },
        ]
        assert blocks_to_markdown(blocks) == "First\n\nSecond"


class TestInlineFormatting:
    def test_bold(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "bold", "annotations": {"bold": True}}]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "**bold**"

    def test_italic(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "italic", "annotations": {"italic": True}}]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "*italic*"

    def test_code_inline(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "code", "annotations": {"code": True}}]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "`code`"

    def test_link(self):
        blocks = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "text", "href": "https://example.com"}]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "[text](https://example.com)"


class TestLists:
    def test_bullet_list(self):
        blocks = [
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Item 1"}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"plain_text": "Item 2"}]},
            },
        ]
        assert blocks_to_markdown(blocks) == "- Item 1\n- Item 2"

    def test_ordered_list(self):
        blocks = [
            {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"plain_text": "First"}]},
            },
            {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"plain_text": "Second"}]},
            },
        ]
        assert blocks_to_markdown(blocks) == "1. First\n1. Second"


class TestCodeBlock:
    def test_code_block_with_language(self):
        blocks = [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"plain_text": "print('hello')"}],
                    "language": "python",
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "```python\nprint('hello')\n```"

    def test_code_block_plain_text(self):
        blocks = [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"plain_text": "some code"}],
                    "language": "plain text",
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "```\nsome code\n```"


class TestQuote:
    def test_blockquote(self):
        blocks = [
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"plain_text": "This is a quote"}]},
            }
        ]
        assert blocks_to_markdown(blocks) == "> This is a quote"


class TestDivider:
    def test_horizontal_rule(self):
        blocks = [{"object": "block", "type": "divider", "divider": {}}]
        assert blocks_to_markdown(blocks) == "---"


class TestToDo:
    def test_unchecked(self):
        blocks = [
            {
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": [{"plain_text": "Task"}], "checked": False},
            }
        ]
        assert blocks_to_markdown(blocks) == "- [ ] Task"

    def test_checked(self):
        blocks = [
            {
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": [{"plain_text": "Done"}], "checked": True},
            }
        ]
        assert blocks_to_markdown(blocks) == "- [x] Done"


class TestRoundTrip:
    """Test that markdown -> blocks -> markdown preserves content."""

    def test_simple_roundtrip(self):
        from marknotion import markdown_to_blocks

        original = "# Title\n\nSome text"
        blocks = markdown_to_blocks(original)
        result = blocks_to_markdown(blocks)
        assert result == original

    def test_list_roundtrip(self):
        from marknotion import markdown_to_blocks

        original = "- Item 1\n- Item 2\n- Item 3"
        blocks = markdown_to_blocks(original)
        result = blocks_to_markdown(blocks)
        assert result == original
