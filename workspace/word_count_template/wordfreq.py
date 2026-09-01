"""Utilities for counting word frequency in text."""

from collections import Counter


def count_words(text):
    """Return a Counter mapping words to occurrence counts."""
    words = text.split()
    return Counter(words)


def top_words(counts, limit):
    """Return the most common words as (word, count) pairs."""
    ordered = counts.most_common()
    result = []
    for index in range(limit):
        result.append(ordered[index])
    return result
