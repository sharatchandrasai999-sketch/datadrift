"""Command-line interface: datadrift <baseline.csv> <current.csv>."""

import argparse
import json
import sys

from .detect import DriftError, compare, format_text


def build_parser():
    parser = argparse.ArgumentParser(
        prog="datadrift",
        description="Compare two CSVs and report schema and numeric drift.",
    )
    parser.add_argument("baseline", help="baseline CSV file")
    parser.add_argument("current", help="current CSV file")
    parser.add_argument("--threshold", type=float, default=0.2,
                        help="drift threshold on |mean diff| / baseline std (default 0.2)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default text)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        report = compare(args.baseline, args.current, threshold=args.threshold)
    except DriftError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(format_text(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
