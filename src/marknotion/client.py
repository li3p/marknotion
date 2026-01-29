"""Notion API client wrapper.

Provides a high-level client for Notion API operations with:
- Automatic retry on transient errors
- Markdown to blocks conversion
- Pagination handling
"""

import os
import time
from functools import wraps
from typing import Any, Callable

from notion_client import Client
from notion_client.errors import HTTPResponseError

from marknotion.md2notion import markdown_to_blocks
from marknotion.notion2md import blocks_to_markdown


def retry_on_error(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    on_retry: Callable[[Exception, int, float], None] | None = None,
):
    """Decorator for retrying on transient errors (429, 5xx)."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HTTPResponseError as e:
                    if e.status not in (429, 500, 502, 503, 504) or attempt == max_retries:
                        raise
                    if on_retry:
                        on_retry(e, attempt, delay)
                    time.sleep(delay)
                    delay = min(delay * 2, max_delay)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _default_on_retry(error: Exception, attempt: int, delay: float) -> None:
    """Default retry callback that prints progress."""
    status = getattr(error, "status", "?")
    error_type = "Rate limited" if status == 429 else f"API error {status}"
    print(f"    ⚠ {error_type}, retrying in {delay:.1f}s (attempt {attempt})...")


class NotionClient:
    """Wrapper around notion-client with convenience methods.

    Provides:
    - Automatic retry on transient errors (429, 5xx)
    - Markdown to blocks conversion
    - Pagination handling for queries
    """

    def __init__(
        self,
        token: str | None = None,
        on_retry: Callable[[Exception, int, float], None] | None = _default_on_retry,
    ):
        """Initialize Notion client.

        Args:
            token: Notion integration token. If not provided, reads from NOTION_TOKEN env var.
            on_retry: Callback (error, attempt, delay) called before each retry.
                      Set to None to disable logging.
        """
        self.token = token or os.environ.get("NOTION_TOKEN")
        if not self.token:
            raise ValueError(
                "Notion token not provided. Set NOTION_TOKEN environment variable "
                "or pass token to constructor.\n\n"
                "To create a token, visit: https://www.notion.so/my-integrations"
            )
        self.client = Client(auth=self.token)
        self._on_retry = on_retry

    def search(
        self,
        query: str,
        object_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for pages and/or databases.

        Args:
            query: Search query
            object_type: Filter by type - "page", "database", or None for both

        Returns:
            List of page/database objects
        """
        params: dict[str, Any] = {"query": query}
        if object_type == "page":
            params["filter"] = {"property": "object", "value": "page"}
        elif object_type == "database":
            # Notion API uses "data_source" for databases
            params["filter"] = {"property": "object", "value": "data_source"}

        response = self.client.search(**params)
        return response.get("results", [])

    def search_pages(self, query: str) -> list[dict[str, Any]]:
        """Search for pages by title (legacy method).

        Args:
            query: Search query

        Returns:
            List of page objects
        """
        return self.search(query, object_type="page")

    def get_block_children(self, block_id: str) -> list[dict[str, Any]]:
        """Get all child blocks of a block/page with automatic pagination.

        Args:
            block_id: Block or page ID

        Returns:
            List of all block objects
        """
        results = []
        has_more = True
        start_cursor = None

        while has_more:
            params: dict[str, Any] = {"block_id": block_id}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = self.client.blocks.children.list(**params)
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        return results

    @retry_on_error(on_retry=_default_on_retry)
    def append_blocks(self, page_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
        """Append blocks to a page.

        Args:
            page_id: Page ID
            children: Blocks to append (max 100 per call)

        Returns:
            Response object
        """
        return self.client.blocks.children.append(block_id=page_id, children=children[:100])

    def append_blocks_in_batches(self, page_id: str, blocks: list[dict[str, Any]]) -> None:
        """Append blocks to a page in batches of 100 (Notion API limit).

        Args:
            page_id: Page ID
            blocks: Blocks to append (any number)
        """
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i : i + batch_size]
            self.append_blocks(page_id, batch)

    @retry_on_error(on_retry=_default_on_retry)
    def clear_page_content(self, page_id: str) -> None:
        """Clear all content blocks from a page.

        Args:
            page_id: Page ID
        """
        self.client.pages.update(page_id=page_id, erase_content=True)

    @retry_on_error(on_retry=_default_on_retry)
    def create_child_page(
        self,
        parent_page_id: str,
        title: str,
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new page under a parent page.

        Args:
            parent_page_id: Parent page ID
            title: Page title
            children: Optional page content blocks (max 100)

        Returns:
            Created page object
        """
        params: dict[str, Any] = {
            "parent": {"page_id": parent_page_id},
            "properties": {"title": [{"text": {"content": title}}]},
        }
        if children:
            params["children"] = children[:100]

        return self.client.pages.create(**params)

    def update_page_content_from_markdown(self, page_id: str, markdown: str) -> None:
        """Update page content from markdown.

        Clears existing content and replaces with new blocks.

        Args:
            page_id: Page ID
            markdown: Markdown content
        """
        blocks = markdown_to_blocks(markdown)
        self.clear_page_content(page_id)
        if blocks:
            self.append_blocks_in_batches(page_id, blocks)

    def create_child_page_from_markdown(
        self,
        parent_page_id: str,
        title: str,
        markdown: str,
    ) -> dict[str, Any]:
        """Create a child page with markdown content.

        Args:
            parent_page_id: Parent page ID
            title: Page title
            markdown: Markdown content

        Returns:
            Created page object
        """
        blocks = markdown_to_blocks(markdown)

        first_batch = blocks[:100]
        page = self.create_child_page(parent_page_id, title, first_batch if first_batch else None)

        remaining = blocks[100:]
        if remaining:
            self.append_blocks_in_batches(page["id"], remaining)

        return page

    # =========================================================================
    # Database Operations
    # =========================================================================

    @retry_on_error(on_retry=_default_on_retry)
    def create_database_entry(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new entry (page) in a database.

        Args:
            database_id: Database ID
            properties: Property values for the entry
            children: Optional content blocks (max 100)

        Returns:
            Created page object
        """
        params: dict[str, Any] = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        if children:
            params["children"] = children[:100]

        return self.client.pages.create(**params)

    @retry_on_error(on_retry=_default_on_retry)
    def update_database_entry(
        self,
        page_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing database entry (page).

        Args:
            page_id: Page ID of the entry to update
            properties: Property values to update

        Returns:
            Updated page object
        """
        return self.client.pages.update(page_id=page_id, properties=properties)
