"""
Reserved for future direct-to-blob uploads. On Vercel, serverless request bodies are ~4.5MB max,
so large videos should use a public HTTPS URL (see upload form) or client-side Blob upload.
"""
from __future__ import annotations


def upload_video_to_blob(filename: str, data: bytes, content_type: str) -> str | None:
    return None
