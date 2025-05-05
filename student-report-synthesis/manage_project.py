#!/usr/bin/env python3
"""
Project management script for Student Report Generation System.

This script provides utilities for managing the project file structure,
including creating, updating, and cleaning files and directories.
"""

import sys
from project_manager import ProjectManager, parse_args


def main() -> int:
    """Main entry point for the project manager."""
    args = parse_args()
    
    if args.command == "setup":
        project_manager = ProjectManager(args.dir)
        project_manager.setup_project(clean=args.clean)
        return 0
    elif args.command == "update":
        project_manager = ProjectManager(args.dir)
        project_manager.update_project()
        return 0
    elif args.command == "clean":
        project_manager = ProjectManager(args.dir)
        project_manager.clean_project(exclude=args.exclude)
        return 0
    else:
        print("Please specify a command. Use --help for more information.")
        return 1


if __name__ == "__main__":
    sys.exit(main())