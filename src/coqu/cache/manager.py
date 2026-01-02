# coqu.cache.manager - Cache management
"""
Manages cached AST files using MessagePack serialization.
"""
from pathlib import Path
from typing import Optional
import time

from coqu.parser.ast import CobolProgram
from coqu.cache.serializer import ASTSerializer


class CacheManager:
    """
    Manages AST cache files.

    Cache files are stored as:
    - {cache_dir}/{source_hash}.coqu

    Features:
    - Hash-based cache keys (SHA256 of source)
    - Automatic cache invalidation via hash
    - Cache statistics
    - Cache cleanup
    """

    # Cache file extension
    EXTENSION = ".coqu"

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files. Defaults to ~/.cache/coqu
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "coqu"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.serializer = ASTSerializer()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0,
        }

    def _get_cache_path(self, source_hash: str) -> Path:
        """Get cache file path for a source hash."""
        return self.cache_dir / f"{source_hash}{self.EXTENSION}"

    def get(self, source_hash: str) -> Optional[CobolProgram]:
        """
        Get cached program by source hash.

        Args:
            source_hash: SHA256 hash of source code

        Returns:
            CobolProgram or None if not cached
        """
        cache_path = self._get_cache_path(source_hash)

        if not cache_path.exists():
            self._stats["misses"] += 1
            return None

        program = self.serializer.load(cache_path)
        if program:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
            # Invalid cache file, remove it
            try:
                cache_path.unlink()
            except Exception:
                pass

        return program

    def put(self, source_hash: str, program: CobolProgram) -> bool:
        """
        Store program in cache.

        Args:
            source_hash: SHA256 hash of source code
            program: Program AST to cache

        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(source_hash)

        success = self.serializer.save(program, cache_path)
        if success:
            self._stats["saves"] += 1

        return success

    def remove(self, source_hash: str) -> bool:
        """
        Remove a cache entry.

        Args:
            source_hash: Hash to remove

        Returns:
            True if removed
        """
        cache_path = self._get_cache_path(source_hash)
        try:
            if cache_path.exists():
                cache_path.unlink()
                return True
        except Exception:
            pass
        return False

    def clear(self) -> int:
        """
        Clear all cache files.

        Returns:
            Number of files removed
        """
        count = 0
        for path in self.cache_dir.glob(f"*{self.EXTENSION}"):
            try:
                path.unlink()
                count += 1
            except Exception:
                pass
        return count

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss/save counts and size info
        """
        total_size = 0
        file_count = 0

        for path in self.cache_dir.glob(f"*{self.EXTENSION}"):
            try:
                total_size += path.stat().st_size
                file_count += 1
            except Exception:
                pass

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "saves": self._stats["saves"],
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hit_rate": self._get_hit_rate(),
        }

    def _get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return round(self._stats["hits"] / total * 100, 1)

    def list_cached(self) -> list[dict]:
        """
        List all cached files.

        Returns:
            List of cache file info
        """
        results = []
        for path in self.cache_dir.glob(f"*{self.EXTENSION}"):
            try:
                stat = path.stat()
                results.append({
                    "hash": path.stem,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except Exception:
                pass

        return sorted(results, key=lambda x: x["modified"], reverse=True)

    def cleanup_old(self, max_age_days: int = 30) -> int:
        """
        Remove cache files older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of files removed
        """
        cutoff = time.time() - (max_age_days * 24 * 60 * 60)
        count = 0

        for path in self.cache_dir.glob(f"*{self.EXTENSION}"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    count += 1
            except Exception:
                pass

        return count

    def cleanup_by_size(self, max_size_mb: int = 500) -> int:
        """
        Remove oldest cache files to stay under size limit.

        Args:
            max_size_mb: Maximum total cache size in MB

        Returns:
            Number of files removed
        """
        max_bytes = max_size_mb * 1024 * 1024

        # Get all cache files with stats
        files = []
        for path in self.cache_dir.glob(f"*{self.EXTENSION}"):
            try:
                stat = path.stat()
                files.append({
                    "path": path,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                })
            except Exception:
                pass

        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x["mtime"])

        # Calculate total size
        total_size = sum(f["size"] for f in files)

        # Remove oldest files until under limit
        count = 0
        while total_size > max_bytes and files:
            oldest = files.pop(0)
            try:
                oldest["path"].unlink()
                total_size -= oldest["size"]
                count += 1
            except Exception:
                pass

        return count
