"""Google OAuth and API service construction."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        # Windows does not support POSIX mode bits; rely on the user's profile ACL.
        pass


def create_service(
    api_name: str = "youtube",
    api_version: str = "v3",
    *,
    client_secret_file: str | Path = "client-secrets.json",
    token_dir: str | Path | None = None,
    scopes: tuple[str, ...] = (YOUTUBE_READONLY_SCOPE,),
) -> Any:
    """Return an authenticated Google API client, refreshing/storing OAuth tokens.

    ``GOOGLE_OAUTH_CLIENT_FILE`` and ``YOUTUBE_TOKEN_DIR`` can override the
    paths. Tokens are stored outside the repository by default.
    """
    secret_path = Path(os.environ.get("GOOGLE_OAUTH_CLIENT_FILE", client_secret_file)).expanduser().resolve()
    if not secret_path.is_file():
        raise FileNotFoundError(f"OAuth client file not found: {secret_path}")
    try:
        import json

        config = json.loads(secret_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not read OAuth client JSON at {secret_path}") from exc
    if "installed" not in config:
        raise ValueError(
            "client_secret.json is a placeholder or not a Desktop app OAuth client. "
            "Download the Desktop app JSON from Google Cloud Console."
        )

    base = Path(token_dir or os.environ.get("YOUTUBE_TOKEN_DIR", "~/.config/youtube-mcp/tokens")).expanduser()
    _private_directory(base)
    token_path = base / f"{api_name}-{api_version}.json"
    credentials = Credentials.from_authorized_user_file(str(token_path), scopes) if token_path.exists() else None

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    elif not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), scopes)
        credentials = flow.run_local_server(port=0, open_browser=True)

    # Write atomically so interruption cannot leave a truncated token file.
    temporary = token_path.with_suffix(".tmp")
    temporary.write_text(credentials.to_json(), encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(token_path)
    try:
        token_path.chmod(0o600)
    except OSError:
        pass
    return build(api_name, api_version, credentials=credentials, cache_discovery=False)
