# YouTube MCP Server

A local FastMCP server for YouTube Data API v3 channel/video searches and metadata, plus transcript retrieval through `youtube-transcript-api`.

## Install and configure

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed. In this directory, initialize/synchronize the project:

   ```powershell
   uv init --bare   # only if starting in a directory without pyproject.toml
   uv sync
   ```

   This repository already includes `pyproject.toml`; on a fresh checkout run `uv sync` directly. `uv run` also synchronizes dependencies automatically.

2. In Google Cloud Console, create/select a project, enable **YouTube Data API v3**, configure the OAuth consent screen, and create an OAuth client ID with application type **Desktop app**. Place the downloaded OAuth JSON in the project as `client-secrets.json`. Keep it private and out of version control. Set `GOOGLE_OAUTH_CLIENT_FILE` if you prefer another filename or location.

3. First launch opens the browser for Google sign-in. The local refresh token is saved under `~/.config/youtube-mcp/tokens/` (Windows: the equivalent home-profile path). You can set `GOOGLE_OAUTH_CLIENT_FILE` or `YOUTUBE_TOKEN_DIR` to use different locations. YouTube Data API calls require quota; transcript retrieval may be unavailable for some videos/languages.

4. Start the server:

   ```powershell
   uv run python mcp_youtube_server.py
   ```

   For a quick dependency install without project sync, use `uv pip install --python .venv\Scripts\python.exe -e .` after `uv venv`.

## MCP client registration

For Claude Desktop, add a server entry to its `claude_desktop_config.json` (commonly `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "youtube": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YOUR_NAME\\path\\to\\YouTube MCP",
        "run",
        "python",
        "mcp_youtube_server.py"
      ]
    }
  }
}
```

Replace the path with this project's absolute directory, save, and restart Claude Desktop. Other MCP clients can launch the same `uv --directory <project-path> run python mcp_youtube_server.py` command over stdio.
