#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    # Add src to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
    from cli import main
    main.app()