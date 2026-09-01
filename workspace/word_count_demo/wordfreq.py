"""Utilities for counting word frequency in text."""

import re
from collections import Counter


def count_words(text):
    """Return a Counter mapping words to occurrence counts.

    Words are lowercased and stripped of surrounding punctuation so that
    e.g. ``Hello``, ``hello`` and ``hello,`` are treated as the same word.
    """
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return Counter(words)


def top_words(counts, limit, min_count=None):
    """Return the most common words as (word, count) pairs.

    Parameters
    ----------
    counts : Counter
        Word -> count mapping.
    limit : int
        Maximum number of words to return.  If *limit* is larger than the
        vocabulary size, all words are returned (no error is raised).
    min_count : int, optional
        If given, only words whose count is >= *min_count* are included.
    """
    ordered = counts.most_common()
    if min_count is not None:
        ordered = [(w, c) for w, c in ordered if c >= min_count]
    return ordered[:limit]
