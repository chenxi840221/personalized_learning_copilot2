#!/usr/bin/env python3
"""
Run script for the Personalized Learning Co-pilot API.
This script starts the FastAPI application with the proper settings.
"""

import uvicorn
import os
import argparse

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Personalized Learning Co-pilot API")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--app", type=str, default="app:app", help="Application import path")
    args = parser.parse_args()

    # Print startup info
    print(f"Starting Personalized Learning Co-pilot API on {args.host}:{args.port}")
    print(f"Application: {args.app}")
    print(f"Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    
    # Check for debug mode
    debug_mode = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")
    if debug_mode:
        print("DEBUG mode enabled via environment variable")
        
    # Start the server
    uvicorn.run(
        args.app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if debug_mode else "info"
    )

if __name__ == "__main__":
    main()