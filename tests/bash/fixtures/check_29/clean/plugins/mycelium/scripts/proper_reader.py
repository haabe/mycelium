"""Test fixture for Check 29: clean (passing) scenario.

This script reads a state file but has the explicit-source override
mechanism Check 29 requires. The pattern is the worked example from
parse_manifest.py: argparse-driven --manifest=<path> override.

Check 29 must NOT surface this.
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).resolve().parent.parent / "manifest.yml"),
        help="Path to manifest.yml. Override for upgrade/sync flows reading upstream state.",
    )
    args = parser.parse_args()
    return Path(args.manifest).read_text()


if __name__ == "__main__":
    main()
