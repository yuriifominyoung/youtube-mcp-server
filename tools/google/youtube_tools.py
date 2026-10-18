"""Typed wrappers around the YouTube Data API v3."""

from __future__ import annotations

import re
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, Field

from .google_apis import create_service

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class ChannelInfo(BaseModel):
    id: str
    title: str
    description: str = ""
    custom_url: str | None = None
    published_at: str | None = None
    thumbnails: dict[str, Any] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    country: str | None = None


class SearchResult(BaseModel):
    id: str
    title: str
    description: str = ""
    published_at: str | None = None
    thumbnails: dict[str, Any] = Field(default_factory=dict)
    channel_id: str | None = None
    channel_title: str | None = None


class VideoInfo(BaseModel):
    id: str
    snippet: dict[str, Any] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    content_details: dict[str, Any] = Field(default_factory=dict)
    topic_details: dict[str, Any] = Field(default_factory=dict)


def extract_video_id(value: str) -> str:
    """Extract an 11-character YouTube video ID from a URL or raw ID."""
    candidate = value.strip()
    if VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").lower()
    video_id = None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif host == "youtube.com" or host.endswith(".youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            match = re.match(r"^/(?:embed|shorts|live)/([^/?]+)", parsed.path)
            if match:
                video_id = match.group(1)
    if not video_id or not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Expected a YouTube URL or an 11-character video ID")
    return video_id


class YouTubeTools:
    def __init__(self, service: Any | None = None) -> None:
        # Authenticate on first API use so MCP clients can start and connect
        # before the browser-based OAuth flow is needed.
        self._service = service
        self._service_lock = threading.Lock()

    @property
    def service(self) -> Any:
        if self._service is None:
            with self._service_lock:
                if self._service is None:
                    self._service = create_service()
        return self._service

    @staticmethod
    def _items(response: dict[str, Any]) -> list[dict[str, Any]]:
        return response.get("items", [])

    def get_channel_info(self, channel: str) -> dict[str, Any]:
        """Resolve a channel ID, @handle, or legacy username and return its details."""
        term = channel.strip()
        if term.startswith("@"):
            response = self.service.channels().list(part="snippet,statistics,contentDetails,brandingSettings", forHandle=term[1:]).execute()
        elif term.startswith("UC"):
            response = self.service.channels().list(part="snippet,statistics,contentDetails,brandingSettings", id=term).execute()
        else:
            response = self.service.channels().list(part="snippet,statistics,contentDetails,brandingSettings", forUsername=term).execute()
            if not self._items(response):
                response = self.service.search().list(part="snippet", q=term, type="channel", maxResults=1).execute()
                found = self._items(response)
                if found:
                    response = self.service.channels().list(part="snippet,statistics,contentDetails,brandingSettings", id=found[0]["id"]["channelId"]).execute()
        items = self._items(response)
        if not items:
            raise ValueError(f"No YouTube channel found for {channel!r}")
        item = items[0]
        snippet = item.get("snippet", {})
        return ChannelInfo(
            id=item["id"], title=snippet.get("title", ""), description=snippet.get("description", ""),
            custom_url=snippet.get("customUrl"), published_at=snippet.get("publishedAt"),
            thumbnails=snippet.get("thumbnails", {}), statistics=item.get("statistics", {}), country=snippet.get("country"),
        ).model_dump()

    def _search(self, query: str, kind: str, max_results: int = 25) -> list[dict[str, Any]]:
        if not 1 <= max_results <= 500:
            raise ValueError("max_results must be between 1 and 500")
        results: list[dict[str, Any]] = []
        page_token = None
        while len(results) < max_results:
            count = min(50, max_results - len(results))
            params: dict[str, Any] = {"part": "snippet", "q": query, "type": kind, "maxResults": count}
            if page_token:
                params["pageToken"] = page_token
            response = self.service.search().list(**params).execute()
            for item in self._items(response):
                snippet = item.get("snippet", {})
                identifier = item.get("id", {})
                key = {"channel": "channelId", "video": "videoId", "playlist": "playlistId"}[kind]
                results.append(SearchResult(
                    id=identifier.get(key, ""), title=snippet.get("title", ""),
                    description=snippet.get("description", ""), published_at=snippet.get("publishedAt"),
                    thumbnails=snippet.get("thumbnails", {}), channel_id=snippet.get("channelId"),
                    channel_title=snippet.get("channelTitle"),
                ).model_dump())
            page_token = response.get("nextPageToken")
            if not page_token or not self._items(response):
                break
        return results

    def search_channels(self, query: str, max_results: int = 25) -> list[dict[str, Any]]:
        return self._search(query, "channel", max_results)

    def search_playlists(self, query: str, max_results: int = 25) -> list[dict[str, Any]]:
        return self._search(query, "playlist", max_results)

    def search_videos(self, query: str, max_results: int = 25) -> list[dict[str, Any]]:
        return self._search(query, "video", max_results)

    def get_video_info(self, video: str) -> dict[str, Any]:
        video_id = extract_video_id(video)
        response = self.service.videos().list(part="snippet,statistics,contentDetails,topicDetails", id=video_id).execute()
        items = self._items(response)
        if not items:
            raise ValueError(f"No video found for ID {video_id}")
        item = items[0]
        return VideoInfo(id=item["id"], snippet=item.get("snippet", {}), statistics=item.get("statistics", {}),
                         content_details=item.get("contentDetails", {}), topic_details=item.get("topicDetails", {})).model_dump()
