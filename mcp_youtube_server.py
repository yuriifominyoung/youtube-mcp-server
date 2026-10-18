"""FastMCP server exposing YouTube Data API and transcript tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi

from tools.google.youtube_tools import YouTubeTools, extract_video_id

mcp = FastMCP("YouTube Server")
youtube = YouTubeTools()
transcripts = YouTubeTranscriptApi()


@mcp.tool()
def get_channel_info(channel: str) -> dict[str, Any]:
    """Get YouTube channel profile and statistics by channel ID, @handle, or username."""
    return youtube.get_channel_info(channel)


@mcp.tool()
def search_channels(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search YouTube channels. max_results can be 1 to 500."""
    return youtube.search_channels(query, max_results)


@mcp.tool()
def search_playlists(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search public YouTube playlists. max_results can be 1 to 500."""
    return youtube.search_playlists(query, max_results)


@mcp.tool()
def search_videos(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search YouTube videos. max_results can be 1 to 500."""
    return youtube.search_videos(query, max_results)


@mcp.tool()
def get_video_info(video: str) -> dict[str, Any]:
    """Get snippet, statistics, content details, and topic details for a video URL or ID."""
    return youtube.get_video_info(video)


@mcp.tool()
def get_transcript(video: str, language: str = "en", with_timestamps: bool = True) -> list[dict[str, Any]]:
    """Fetch a transcript in a language such as 'en'; optionally omit timestamps."""
    video_id = extract_video_id(video)
    fetched = transcripts.fetch(video_id, languages=[language])
    rows = fetched.to_raw_data()
    if with_timestamps:
        return rows
    return [{"text": row["text"]} for row in rows]


if __name__ == "__main__":
    mcp.run()
