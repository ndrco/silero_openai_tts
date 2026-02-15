from __future__ import annotations
import os
from pathlib import Path

class DiskCache:
    def __init__(self, root: str, max_files: int = 2000):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_files = int(max_files)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / (key[2:4]) / f"{key}.bin"

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        if not p.exists():
            return None
        return p.read_bytes()

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        self._gc()

    def _gc(self):
        files = []
        for dirpath, _, filenames in os.walk(self.root):
            for fn in filenames:
                if fn.endswith(".bin"):
                    fp = Path(dirpath) / fn
                    files.append((fp.stat().st_mtime, fp))
        if len(files) <= self.max_files:
            return
        files.sort()
        for _, fp in files[: len(files) - self.max_files]:
            try:
                fp.unlink()
            except OSError:
                pass
