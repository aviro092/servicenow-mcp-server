#!/usr/bin/env python3
"""Start ServiceNow FastMCP Server."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastmcp_server import main

if __name__ == "__main__":
    main()