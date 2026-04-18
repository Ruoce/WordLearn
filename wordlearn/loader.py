import pandas as pd


def load_words(file_path: str) -> list[str]:
    """
    Load words from an Excel file.
    Assumes words are in the first column.
    """
    df = pd.read_excel(file_path)

    if df.empty:
        return []

    # Use the first column, drop blanks, and normalize spacing.
    words = (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    return words
