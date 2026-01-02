# coqu.config.config - Configuration management
"""
Configuration file loading and management.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sys

# Use tomli for Python < 3.11, tomllib for 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class Config:
    """
    coqu configuration.

    Configuration file locations (in order of precedence):
    1. --config argument
    2. .coqu.toml in current directory
    3. ~/.config/coqu/config.toml
    """

    # Copybook search paths
    copybook_paths: list[Path] = field(default_factory=list)

    # Cache settings
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    cache_max_size_mb: int = 500
    cache_max_age_days: int = 30

    # Parser settings
    use_indexer_only: bool = False
    debug_parser: bool = False

    # REPL settings
    history_file: Optional[Path] = None

    # File patterns
    cobol_extensions: list[str] = field(
        default_factory=lambda: [".cbl", ".cob", ".CBL", ".COB"]
    )
    copybook_extensions: list[str] = field(
        default_factory=lambda: [".cpy", ".copy", ".CPY", ".COPY"]
    )

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """
        Create config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        config = cls()

        # Copybook paths
        if "copybook_paths" in data:
            paths = data["copybook_paths"]
            if isinstance(paths, list):
                config.copybook_paths = [Path(p).expanduser() for p in paths]

        # Cache settings
        cache = data.get("cache", {})
        if "enabled" in cache:
            config.cache_enabled = bool(cache["enabled"])
        if "dir" in cache:
            config.cache_dir = Path(cache["dir"]).expanduser()
        if "max_size_mb" in cache:
            config.cache_max_size_mb = int(cache["max_size_mb"])
        if "max_age_days" in cache:
            config.cache_max_age_days = int(cache["max_age_days"])

        # Parser settings
        parser = data.get("parser", {})
        if "use_indexer_only" in parser:
            config.use_indexer_only = bool(parser["use_indexer_only"])
        if "debug" in parser:
            config.debug_parser = bool(parser["debug"])

        # REPL settings
        repl = data.get("repl", {})
        if "history_file" in repl:
            config.history_file = Path(repl["history_file"]).expanduser()

        # File patterns
        if "cobol_extensions" in data:
            config.cobol_extensions = list(data["cobol_extensions"])
        if "copybook_extensions" in data:
            config.copybook_extensions = list(data["copybook_extensions"])

        return config

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "copybook_paths": [str(p) for p in self.copybook_paths],
            "cache": {
                "enabled": self.cache_enabled,
                "dir": str(self.cache_dir) if self.cache_dir else None,
                "max_size_mb": self.cache_max_size_mb,
                "max_age_days": self.cache_max_age_days,
            },
            "parser": {
                "use_indexer_only": self.use_indexer_only,
                "debug": self.debug_parser,
            },
            "repl": {
                "history_file": str(self.history_file) if self.history_file else None,
            },
            "cobol_extensions": self.cobol_extensions,
            "copybook_extensions": self.copybook_extensions,
        }


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration.

    Args:
        config_path: Optional explicit config path

    Returns:
        Config instance
    """
    # Try explicit path first
    if config_path and config_path.exists():
        return _load_from_file(config_path)

    # Try current directory
    local_config = Path(".coqu.toml")
    if local_config.exists():
        return _load_from_file(local_config)

    # Try user config directory
    user_config = Path.home() / ".config" / "coqu" / "config.toml"
    if user_config.exists():
        return _load_from_file(user_config)

    # Return defaults
    return Config()


def _load_from_file(path: Path) -> Config:
    """Load config from TOML file."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return Config.from_dict(data)
    except Exception as e:
        print(f"Warning: Failed to load config from {path}: {e}")
        return Config()
