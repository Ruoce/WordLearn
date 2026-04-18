# validator.py

from typing import List


def check_missing_words(text: str, words: List[str]) -> List[str]:
    """
    Return words that are NOT found in the generated text.
    Case-insensitive matching.
    """
    text_lower = text.lower()

    missing = []
    for word in words:
        if word.lower() not in text_lower:
            missing.append(word)

    return missing