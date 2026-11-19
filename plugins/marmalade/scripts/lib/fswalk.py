"""One directory walker for every Marmalade script.

Two things each script used to get wrong on its own:

- Skip directories were matched against the *whole* path, so a repository that
  merely lived under a directory called `build` or `dist` looked empty. Only
  the part of the path below the root being walked is checked here.
- `Path.rglob` descends into `node_modules` and `.git` before the caller can
  filter them out. This prunes them, which matters to a hook with a timeout.
"""

from __future__ import annotations

import os
from pathlib import Path

SKIP_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "target",
    "__pycache__", ".tox", ".mypy_cache",
})


def iter_files(root, exts=None, skip=SKIP_DIRS, limit=None):
    """Yield files under `root`, pruning `skip` directories below it.

    `exts` is a tuple of lowercase suffixes (".mmd", ...) or None for every
    file. `limit` caps how many files are yielded. Order is deterministic.
    """
    root = Path(root)
    if not root.is_dir():
        return
    seen = 0
    for current, dirs, files in os.walk(str(root)):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(files):
            if exts is not None and os.path.splitext(name)[1].lower() not in exts:
                continue
            if limit is not None and seen >= limit:
                return
            seen += 1
            yield Path(current) / name


def sorted_files(root, exts=None, skip=SKIP_DIRS):
    """Every matching file under `root`, sorted by path."""
    return sorted(iter_files(root, exts, skip))
