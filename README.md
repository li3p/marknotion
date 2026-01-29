# marknotion

Bidirectional Markdown ↔ Notion converter with CLI tools.

## Installation

```bash
# With uv (recommended for CLI tools)
uv tool install marknotion

# Or with pip
pip install marknotion
```

## Setup

### 1. Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name (e.g., "marknotion")
4. Select capabilities: Read, Update, Insert content
5. Copy the "Internal Integration Token"

### 2. Set Environment Variable

```bash
export NOTION_TOKEN="secret_xxxxx..."
```

Or create a `.env` file in your project:

```
NOTION_TOKEN=secret_xxxxx...
```

### 3. Connect Pages to Your Integration

In Notion, open the page you want to access, click "..." menu → "Connections" → Add your integration.

## CLI Commands

### md2notion - Upload Markdown to Notion

```bash
# Update an existing page
md2notion README.md --page "https://notion.so/My-Page-abc123..."

# Create a new child page
md2notion guide.md --parent "abc123..." --title "User Guide"
```

### notion2md - Export Notion to Markdown

```bash
# Print to stdout
notion2md "https://notion.so/My-Page-abc123..."

# Save to file
notion2md abc123... -o exported.md
```

### notion-search - Search Notion Pages and Databases

```bash
# Search all (pages and databases)
notion-search "project"

# Search only databases (useful for finding database IDs)
notion-search "tracker" --type database

# Search only pages
notion-search "notes" --type page

# Limit results
notion-search project -n 5
```

Output includes type, ID, and clickable URL:

```
[Database] Projects
           ID:  1d73963f-ce05-8183-9af4-000b16a57189
           URL: https://www.notion.so/1d73963fce05813bac29eba023f0dd25

[Page]     Meeting Notes
           ID:  abc123de-f456-7890-1234-56789012abcd
           URL: https://www.notion.so/Meeting-Notes-abc123def4567890123456789012abcd
```

## Python API

```python
from marknotion import markdown_to_blocks, blocks_to_markdown, NotionClient

# Convert Markdown to Notion blocks
blocks = markdown_to_blocks("# Hello\n\nWorld")

# Convert Notion blocks to Markdown
md = blocks_to_markdown(blocks)

# Use NotionClient for API operations
client = NotionClient()  # Uses NOTION_TOKEN env var
client.update_page_content_from_markdown(page_id, markdown)
```

## Supported Features

- Headings (h1-h3)
- Paragraphs
- Bold, italic, strikethrough, inline code
- Links
- Bullet lists, numbered lists
- Code blocks (with language)
- Blockquotes
- Horizontal rules

## License

MIT
