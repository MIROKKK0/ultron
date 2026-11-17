#!/usr/bin/env python3
"""Entry point for the ULTRON personal assistant API."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the ULTRON assistant.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
