# coqu.cache.serializer - MessagePack AST serialization
"""
Serializes and deserializes COBOL AST using MessagePack.
Provides efficient binary format for large ASTs.
"""
from pathlib import Path
from typing import Optional
import msgpack

from coqu.parser.ast import CobolProgram


class ASTSerializer:
    """
    Serializes/deserializes CobolProgram AST using MessagePack.

    MessagePack is used for:
    - Fast serialization/deserialization
    - Compact binary format
    - Cross-platform compatibility
    - Safe (no arbitrary code execution unlike pickle)
    """

    # Magic bytes to identify coqu cache files
    MAGIC = b"COQU"
    VERSION = 1

    def serialize(self, program: CobolProgram) -> bytes:
        """
        Serialize a CobolProgram to bytes.

        Args:
            program: The program AST to serialize

        Returns:
            MessagePack encoded bytes
        """
        # Convert to dict
        data = program.to_dict()

        # Add metadata
        envelope = {
            "version": self.VERSION,
            "data": data,
        }

        # Encode
        packed = msgpack.packb(envelope, use_bin_type=True)

        # Add magic header
        return self.MAGIC + packed

    def deserialize(self, data: bytes) -> Optional[CobolProgram]:
        """
        Deserialize bytes to a CobolProgram.

        Args:
            data: MessagePack encoded bytes

        Returns:
            CobolProgram or None if invalid
        """
        # Check magic header
        if not data.startswith(self.MAGIC):
            return None

        try:
            # Decode
            packed = data[len(self.MAGIC):]
            envelope = msgpack.unpackb(packed, raw=False)

            # Check version
            version = envelope.get("version", 0)
            if version != self.VERSION:
                return None

            # Reconstruct program
            program_data = envelope.get("data")
            if not program_data:
                return None

            return CobolProgram.from_dict(program_data)

        except Exception:
            return None

    def save(self, program: CobolProgram, path: Path) -> bool:
        """
        Save program to a file.

        Args:
            program: Program to save
            path: File path

        Returns:
            True if successful
        """
        try:
            data = self.serialize(program)
            path.write_bytes(data)
            return True
        except Exception:
            return False

    def load(self, path: Path) -> Optional[CobolProgram]:
        """
        Load program from a file.

        Args:
            path: File path

        Returns:
            CobolProgram or None if failed
        """
        try:
            data = path.read_bytes()
            return self.deserialize(data)
        except Exception:
            return None

    def get_cache_size(self, path: Path) -> int:
        """
        Get size of a cache file in bytes.

        Args:
            path: File path

        Returns:
            Size in bytes or 0 if not found
        """
        try:
            return path.stat().st_size
        except Exception:
            return 0
