import argparse

from wordlearn.generator import generate_passage
from wordlearn.loader import load_words
from wordlearn.question_generator import generate_questions
from wordlearn.validator import check_missing_words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load words from Excel and generate a reading passage."
    )
    parser.add_argument(
        "--file",
        default="words.xlsx",
        help="Path to the Excel file containing words in the first column.",
    )
    parser.add_argument(
        "--exam",
        default="CET4",
        choices=["IELTS", "CET4", "CET6"],
        help="Target exam type used for both the passage and the questions.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model used to generate the passage. Leave empty to auto-select by provider.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    words = load_words(args.file)
    if not words:
        raise ValueError(f"No usable words were found in {args.file}.")

    passage = generate_passage(
        words,
        exam_type=args.exam,
        model=args.model,
    )
    passage_text = "\n\n".join(passage["paragraphs"])
    questions = generate_questions(
        passage,
        exam_type=args.exam,
        model=args.model,
    )
    missing_words = check_missing_words(passage_text, words)

    print("=== Loaded Words ===")
    print(words)
    print()
    print("=== Settings ===")
    print(f"Exam: {args.exam}")
    print()
    print("=== Title ===")
    print(passage["title"])
    print()
    print("=== Paragraphs ===")
    for paragraph in passage["paragraphs"]:
        print(paragraph)
        print()
    print("=== Validation ===")
    if missing_words:
        print("Missing words:", ", ".join(missing_words))
    else:
        print("All words were included in the generated passage.")
    print()
    print("=== MCQ ===")
    for index, item in enumerate(questions["careful_reading"], start=1):
        print(f"Q{index}. {item['question']}")
        for option_key in ["A", "B", "C", "D"]:
            print(f"{option_key}. {item['options'][option_key]}")
        print(f"Answer: {item['answer']}")
        print()


if __name__ == "__main__":
    main()
