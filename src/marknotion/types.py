"""Type definitions for Notion blocks."""

from typing import Literal, TypedDict

# Rich text types
class TextContent(TypedDict):
    content: str
    link: dict | None


class Annotations(TypedDict, total=False):
    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: str


class RichText(TypedDict):
    type: Literal["text"]
    text: TextContent
    annotations: Annotations
    plain_text: str
    href: str | None


# Block types
class ParagraphBlock(TypedDict):
    object: Literal["block"]
    type: Literal["paragraph"]
    paragraph: dict  # {"rich_text": list[RichText]}


class HeadingBlock(TypedDict):
    object: Literal["block"]
    type: Literal["heading_1", "heading_2", "heading_3"]
    heading_1: dict | None
    heading_2: dict | None
    heading_3: dict | None


class BulletedListItemBlock(TypedDict):
    object: Literal["block"]
    type: Literal["bulleted_list_item"]
    bulleted_list_item: dict  # {"rich_text": list[RichText]}


class NumberedListItemBlock(TypedDict):
    object: Literal["block"]
    type: Literal["numbered_list_item"]
    numbered_list_item: dict  # {"rich_text": list[RichText]}


class CodeBlock(TypedDict):
    object: Literal["block"]
    type: Literal["code"]
    code: dict  # {"rich_text": list[RichText], "language": str}


class QuoteBlock(TypedDict):
    object: Literal["block"]
    type: Literal["quote"]
    quote: dict  # {"rich_text": list[RichText]}


class DividerBlock(TypedDict):
    object: Literal["block"]
    type: Literal["divider"]
    divider: dict  # {}


class ToDoBlock(TypedDict):
    object: Literal["block"]
    type: Literal["to_do"]
    to_do: dict  # {"rich_text": list[RichText], "checked": bool}


# Union type for all blocks
NotionBlock = (
    ParagraphBlock
    | HeadingBlock
    | BulletedListItemBlock
    | NumberedListItemBlock
    | CodeBlock
    | QuoteBlock
    | DividerBlock
    | ToDoBlock
)
