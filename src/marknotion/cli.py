"""Command-line interface for marknotion.

Provides CLI commands for syncing markdown files to/from Notion pages.
"""

import re
from pathlib import Path

import click
from dotenv import load_dotenv

# Load .env from current directory
load_dotenv()


def normalize_page_id(value: str) -> str | None:
    """Normalize a page ID or extract from URL.

    Accepts:
      - Full URL: https://notion.so/Page-abc123...
      - UUID with dashes: abc123de-f456-7890-1234-56789012abcd
      - UUID without dashes: abc123def4567890123456789012abcd

    Returns:
        Page ID in UUID format with dashes, or None if invalid
    """
    if value.startswith("http"):
        path = value.split("?")[0].split("#")[0]
        match = re.search(r"([a-f0-9]{32})$", path, re.IGNORECASE)
        if match:
            hex_id = match.group(1).lower()
            return f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"
        return None

    hex_id = value.replace("-", "").lower()
    if len(hex_id) == 32 and all(c in "0123456789abcdef" for c in hex_id):
        return f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"
    return None


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--page", "-p", help="Target page (ID or URL) - update existing")
@click.option("--parent", help="Parent page (ID or URL) - create new child")
@click.option("--title", "-t", help="Page title (defaults to first H1 or filename)")
@click.version_option()
def md2notion(file: str, page: str | None, parent: str | None, title: str | None):
    """Sync a markdown file to Notion.

    \b
    Two modes:
      1. Update existing page: --page <id-or-url>
      2. Create new child page: --parent <id-or-url>

    \b
    Examples:
        # Update by URL
        md2notion README.md -p "https://notion.so/My-Page-abc123..."

        # Update by ID
        md2notion README.md -p "abc123de-f456-7890-1234-56789012abcd"

        # Create child page
        md2notion guide.md --parent "abc123..." --title "Guide"

    \b
    Environment:
        NOTION_TOKEN: Your Notion integration token
                      Create at: https://www.notion.so/my-integrations
    """
    from marknotion.client import NotionClient

    page_id = None
    parent_id = None

    if page:
        page_id = normalize_page_id(page)
        if not page_id:
            click.echo(f"Error: Invalid page ID or URL: {page}")
            raise SystemExit(1)

    if parent:
        parent_id = normalize_page_id(parent)
        if not parent_id:
            click.echo(f"Error: Invalid parent ID or URL: {parent}")
            raise SystemExit(1)

    if not page_id and not parent_id:
        click.echo("Error: Must specify --page (update) or --parent (create)")
        raise SystemExit(1)

    if page_id and parent_id:
        click.echo("Error: Cannot specify both --page and --parent")
        raise SystemExit(1)

    file_path = Path(file)
    content = file_path.read_text(encoding="utf-8")

    if not title:
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        else:
            title = file_path.stem

    client = NotionClient()

    if page_id:
        click.echo(f"Updating page: {page_id[:8]}...")
        client.update_page_content_from_markdown(page_id, content)
        click.echo(f"Done! Updated page with content from {file_path.name}")
    else:
        click.echo(f"Creating page '{title}' under {parent_id[:8]}...")
        result = client.create_child_page_from_markdown(parent_id, title, content)
        new_id = result["id"].replace("-", "")
        click.echo(f"Done! Created page: https://notion.so/{new_id}")


@click.command()
@click.argument("page", required=True)
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.version_option()
def notion2md(page: str, output: str | None):
    """Export a Notion page to Markdown.

    PAGE can be a Notion URL or page ID.

    \b
    Examples:
        # Print to stdout
        notion2md "https://notion.so/My-Page-abc123..."

        # Save to file
        notion2md abc123... -o page.md

    \b
    Environment:
        NOTION_TOKEN: Your Notion integration token
                      Create at: https://www.notion.so/my-integrations
    """
    from marknotion.client import NotionClient
    from marknotion.notion2md import blocks_to_markdown

    page_id = normalize_page_id(page)
    if not page_id:
        click.echo(f"Error: Invalid page ID or URL: {page}")
        raise SystemExit(1)

    client = NotionClient()

    click.echo(f"Fetching page: {page_id[:8]}...", err=True)
    blocks = client.get_block_children(page_id)
    blocks = _fetch_nested_children(client, blocks)

    markdown = blocks_to_markdown(blocks)

    if output:
        Path(output).write_text(markdown, encoding="utf-8")
        click.echo(f"Done! Saved to {output}", err=True)
    else:
        click.echo(markdown)


def _fetch_nested_children(client, blocks: list) -> list:
    """Recursively fetch children for blocks that have has_children=True."""
    for block in blocks:
        if block.get("has_children"):
            block_type = block.get("type")
            block_id = block.get("id")

            children = client.get_block_children(block_id)
            children = _fetch_nested_children(client, children)

            if block_type in block:
                block[block_type]["children"] = children

    return blocks


@click.command()
@click.argument("query", required=True)
@click.option("--limit", "-n", default=20, help="Max results to show (default: 20)")
@click.version_option()
def notion_search(query: str, limit: int):
    """Search Notion pages by title.

    \b
    Examples:
        # Search for pages
        notion-search "my notes"

        # Limit results
        notion-search guide -n 5

    \b
    Environment:
        NOTION_TOKEN: Your Notion integration token
                      Create at: https://www.notion.so/my-integrations
    """
    from marknotion.client import NotionClient

    client = NotionClient()

    click.echo(f"Searching for: {query}...", err=True)
    results = client.search_pages(query)

    if not results:
        click.echo("No pages found.")
        return

    click.echo(f"\nFound {len(results)} pages:\n")
    click.echo(f"{'ID':<36}  Title")
    click.echo("-" * 70)

    for page in results[:limit]:
        page_id = page.get("id", "")
        title_prop = page.get("properties", {}).get("title", {})
        title_arr = title_prop.get("title", [])
        title = title_arr[0]["plain_text"] if title_arr else "(untitled)"

        click.echo(f"{page_id}  {title}")

    if len(results) > limit:
        click.echo(f"\n... and {len(results) - limit} more (use -n to show more)")


if __name__ == "__main__":
    md2notion()
