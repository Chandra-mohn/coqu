# coqu.utils.spinner - ASCII spinner for loading feedback
"""
Simple ASCII spinner for visual feedback during operations.
"""
import sys
import threading
import time
from typing import Optional


class Spinner:
    """
    Simple ASCII spinner for loading feedback.

    Usage:
        spinner = Spinner("Loading BIGFILE")
        spinner.start()
        try:
            # do work
            result = load_file()
        finally:
            spinner.stop("Loaded BIGFILE (254,123 lines)")

    Or as context manager:
        with Spinner("Loading BIGFILE") as spinner:
            result = load_file()
            spinner.final_message = f"Loaded ({result.lines} lines)"
    """

    # Classic ASCII spinner characters - works everywhere
    CHARS = ['|', '/', '-', '\\']

    def __init__(self, message: str, interval: float = 0.1):
        """
        Initialize spinner.

        Args:
            message: Message to display (e.g., "Loading BIGFILE")
            interval: Time between spinner updates in seconds
        """
        self.message = message
        self.interval = interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.idx = 0
        self.final_message: Optional[str] = None
        self._lock = threading.Lock()

    def start(self) -> "Spinner":
        """Start the spinner animation."""
        with self._lock:
            if self.running:
                return self
            self.running = True
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        return self

    def stop(self, final_message: Optional[str] = None) -> None:
        """
        Stop the spinner and display final message.

        Args:
            final_message: Message to display after spinner stops
        """
        with self._lock:
            self.running = False

        if self.thread:
            self.thread.join(timeout=0.5)

        # Clear the spinner line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()

        # Print final message
        msg = final_message or self.final_message
        if msg:
            print(msg)

    def _spin(self) -> None:
        """Internal method to animate the spinner."""
        while self.running:
            char = self.CHARS[self.idx % len(self.CHARS)]
            sys.stdout.write(f'\r{self.message} {char}')
            sys.stdout.flush()
            self.idx += 1
            time.sleep(self.interval)

    def __enter__(self) -> "Spinner":
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if exc_type:
            self.stop(f"Error: {exc_val}")
        else:
            self.stop()


class ProgressCounter:
    """
    Simple progress counter for batch operations.

    Usage:
        progress = ProgressCounter("Loading files", total=50)
        for file in files:
            load(file)
            progress.increment()
        progress.done("Loaded 50 files")
    """

    def __init__(self, message: str, total: int):
        """
        Initialize progress counter.

        Args:
            message: Message prefix (e.g., "Loading files")
            total: Total number of items
        """
        self.message = message
        self.total = total
        self.current = 0
        self._lock = threading.Lock()

    def increment(self, amount: int = 1) -> None:
        """Increment the counter and update display."""
        with self._lock:
            self.current += amount
            pct = int(100 * self.current / self.total) if self.total > 0 else 0
            sys.stdout.write(f'\r{self.message} ({self.current}/{self.total}) {pct}%')
            sys.stdout.flush()

    def done(self, final_message: Optional[str] = None) -> None:
        """Complete the progress and display final message."""
        # Clear line
        sys.stdout.write('\r' + ' ' * 60 + '\r')
        sys.stdout.flush()

        if final_message:
            print(final_message)
