"""Tests for the article_id manifest contract.

The pipeline writes article_id into tiles.json/chunks.json so the embed
pipeline reads it explicitly instead of guessing from directory names.
"""

import json
from pathlib import Path

from pixelrag_embed.embed_cpu import scan_chunks


def _make_tile_dir(base: Path, dir_name: str, article_id: int | None = None):
    """Create a minimal tile directory with tiles.json and chunks.json."""
    td = base / f"{dir_name}.png.tiles"
    td.mkdir(parents=True)

    from PIL import Image

    img = Image.new("RGB", (875, 500))
    img.save(td / "tile_0000.png")

    tiles_meta = {"tiles": ["tile_0000.png"], "complete": True}
    if article_id is not None:
        tiles_meta["article_id"] = article_id
    (td / "tiles.json").write_text(json.dumps(tiles_meta))

    chunks_meta = {
        "chunks": [
            {
                "tile": "tile_0000.png",
                "tile_index": 0,
                "chunk_index": 0,
                "file": "tile_0000.png",
                "x_offset": 0,
                "y_offset": 0,
                "height": 500,
                "width": 875,
            }
        ],
    }
    if article_id is not None:
        chunks_meta["article_id"] = article_id
    (td / "chunks.json").write_text(json.dumps(chunks_meta))
    return td


def test_article_id_from_manifest(tmp_path):
    """When article_id is in the manifest, embed reads it (not the dir name)."""
    _make_tile_dir(tmp_path, "report", article_id=0)
    items = scan_chunks(str(tmp_path))
    assert len(items) == 1
    assert items[0]["article_id"] == 0


def test_article_id_fallback_to_dir_name(tmp_path):
    """Without article_id in manifest, fall back to parsing directory name."""
    _make_tile_dir(tmp_path, "42", article_id=None)
    items = scan_chunks(str(tmp_path))
    assert len(items) == 1
    assert items[0]["article_id"] == 42


def test_non_numeric_dir_without_manifest_id(tmp_path):
    """Non-numeric dir name + no manifest article_id → hash fallback."""
    _make_tile_dir(tmp_path, "my_report", article_id=None)
    items = scan_chunks(str(tmp_path))
    assert len(items) == 1
    assert isinstance(items[0]["article_id"], int)


def test_manifest_id_overrides_dir_name(tmp_path):
    """Manifest article_id wins over directory name even if dir name is numeric."""
    _make_tile_dir(tmp_path, "999", article_id=7)
    items = scan_chunks(str(tmp_path))
    assert len(items) == 1
    assert items[0]["article_id"] == 7


def test_multiple_articles_distinct_ids(tmp_path):
    """Multiple tile dirs get distinct article_ids from manifests."""
    _make_tile_dir(tmp_path, "report", article_id=0)
    _make_tile_dir(tmp_path, "slides", article_id=1)
    items = scan_chunks(str(tmp_path))
    ids = {it["article_id"] for it in items}
    assert ids == {0, 1}
