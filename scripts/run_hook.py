#!/usr/bin/env python3
"""Launcher for the OTTO PreToolUse hook in the installed layout.

install.sh copies this file next to the otto/ package; adding this file's
directory to sys.path makes `import otto` work without installation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from otto.hook import main  # noqa: E402

sys.exit(main())
