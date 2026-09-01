"""Command-line interface for the word frequency tool."""

import argparse
from pathlib import Path

from wordfreq import count_words, top_words


def build_parser():
    parser = argparse.ArgumentParser(description="Count word frequencies in a text file.")
    parser.add_argument("path", help="Text file to read")
    parser.add_argument("--top", type=int, default=10, help="Number of words to print")
    parser.add_argument(
        "--min-count",
        type=int,
        default=None,
        help="Only show words with at least this many occurrences",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    text = Path(args.path).read_text(encoding="utf-8")
    counts = count_words(text)
    for word, count in top_words(counts, args.top, min_count=args.min_count):
        print(f"{word}\t{count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
