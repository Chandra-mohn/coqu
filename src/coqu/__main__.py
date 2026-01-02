# coqu.__main__ - Entry point for python -m coqu
"""
Allows running coqu as: python -m coqu
"""
from coqu.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
