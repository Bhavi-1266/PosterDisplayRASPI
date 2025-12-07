#!/usr/bin/env python3
"""
cache_handler.py

Handles caching and syncing of poster images.
"""
from pathlib import Path
import os
import requests

# Configuration
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))
SCRIPT_DIR = Path(__file__).parent
CACHE_DIR = SCRIPT_DIR / "eposter_cache"


def ensure_cache():
    """Creates cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def expected_filenames_from_urls(urls):
    """
    Extracts expected filenames from URLs.
    
    Args:
        urls: List of image URLs
    
    Returns:
        set: Set of expected filenames
    """
    names = set()
    for u in urls:
        if not u:
            continue
        name = u.split("/")[-1].split("?")[0]
        if name:
            names.add(name)
    return names


def sync_cache(expected_urls):
    """
    Syncs cache directory with expected URLs.
    Downloads missing files and deletes extras.
    
    Args:
        expected_urls: List of image URLs to cache
    
    Returns:
        list: List of cached file paths
    """
    ensure_cache()
    expected_names = expected_filenames_from_urls(expected_urls)

    # Delete extras
    for f in CACHE_DIR.iterdir():
        if not f.is_file():
            continue
        if f.name.startswith("."):
            continue
        if f.name not in expected_names:
            try:
                f.unlink()
                print("[sync_cache] deleted old file:", f.name)
            except Exception as e:
                print("[sync_cache] failed delete:", f.name, e)

    # Download missing files in order
    cached_paths = []
    for url in expected_urls:
        if not url:
            continue
        fname = url.split("/")[-1].split("?")[0]
        if not fname:
            continue
        dest = CACHE_DIR / fname
        if dest.exists():
            cached_paths.append(dest)
            continue
        tmp = None
        try:
            r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            tmp = dest.with_suffix(".tmp")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(8192):
                    if chunk:
                        fh.write(chunk)
            tmp.rename(dest)
            print("[sync_cache] downloaded:", fname)
            cached_paths.append(dest)
        except Exception as e:
            print("[sync_cache] download failed for", url, "->", e)
            try:
                if tmp and tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
    return cached_paths

