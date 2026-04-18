from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from wordlearn.generator import generate_passage
from wordlearn.loader import load_words
from wordlearn.question_generator import generate_questions, normalize_question_type


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
WORDS_FILE = BASE_DIR / "words.xlsx"
HTML_FILE = BASE_DIR / "end.html"


def build_fallback_questions(question_type: str) -> dict[str, object]:
    normalized = normalize_question_type(question_type)
    if normalized == "careful_reading":
        return {
            "question_type": "careful_reading",
            "careful_reading": [
                {
                    "question": "According to the passage, what does symbiosis refer to?",
                    "options": {
                        "A": "A short-term interaction between organisms of the same species",
                        "B": "A close and long-term interaction between two different biological organisms",
                        "C": "A competitive relationship that causes harm to both parties",
                        "D": "A temporary partnership formed during resource shortages",
                    },
                    "answer": "B",
                },
                {
                    "question": "What role does mutualistic symbiosis play in the natural world?",
                    "options": {
                        "A": "It forces organisms to develop parasitic strategies",
                        "B": "It maintains ecological balance",
                        "C": "It prevents seasonal shifts in the environment",
                        "D": "It eliminates the need for mimicry among species",
                    },
                    "answer": "B",
                },
                {
                    "question": "Why do certain harmless insects mimic the appearance of dangerous species?",
                    "options": {
                        "A": "To attract mates more effectively",
                        "B": "To hunt other insects for food",
                        "C": "To avoid predators",
                        "D": "To adapt to climate change faster",
                    },
                    "answer": "C",
                },
            ],
        }
    if normalized == "banked_cloze":
        return {
            "question_type": "banked_cloze",
            "banked_cloze": {
                "instruction": "Choose the correct word from the word bank to complete each sentence.",
                "word_bank": ["symbiosis", "mimicry", "pressure", "balance", "adapt", "host", "threats"],
                "items": [
                    {
                        "prompt": "A close and long-term interaction between species is called ________.",
                        "answer": "symbiosis",
                    },
                    {
                        "prompt": "Some species use ________ to resemble more dangerous organisms.",
                        "answer": "mimicry",
                    },
                    {
                        "prompt": "Environmental ________ may force relationships to change rapidly.",
                        "answer": "pressure",
                    },
                ],
            },
        }
    if normalized == "tfng":
        return {
            "question_type": "tfng",
            "tfng": [
                {
                    "statement": "Symbiosis can describe a long-term interaction between two different species.",
                    "answer": "True",
                },
                {
                    "statement": "Mimicry always benefits predators rather than prey.",
                    "answer": "False",
                },
                {
                    "statement": "The passage states that all ecosystems recover quickly from climate change.",
                    "answer": "Not Given",
                },
            ],
        }
    return {
        "question_type": "paragraph_matching",
        "paragraph_matching": {
            "instruction": "Match each paragraph with the best heading.",
            "headings": [
                {"key": "i", "text": "The meaning of symbiosis"},
                {"key": "ii", "text": "Defensive adaptation through imitation"},
                {"key": "iii", "text": "Environmental pressure and change"},
            ],
            "items": [
                {"paragraph": "A", "answer": "i"},
                {"paragraph": "B", "answer": "ii"},
                {"paragraph": "C", "answer": "iii"},
            ],
        },
    }


def build_fallback_payload(exam: str, question_type: str) -> dict[str, object]:
    title = f"{exam} Reading Practice: Nature's Complex Partnerships"
    paragraphs = [
        "In the natural world, the relationships between different species often go beyond simple survival. Symbiosis refers to the close and long-term interaction between two different biological organisms. These connections can be beneficial, neutral, or harmful depending on the specific circumstances. When both parties gain advantages, we call this a symbiotic relationship, which plays a vital role in maintaining ecological balance.",
        "However, not all interactions are mutually beneficial. Some creatures have developed parasitic strategies, living on or inside a host organism and causing it harm. Another fascinating adaptation is mimicry, where one species evolves to resemble another for protection or hunting advantages. Scientists study these behaviors to understand how environmental pressures force organisms to adapt over time.",
        "When environmental conditions are ripe for change, such as during seasonal shifts or resource shortages, the strain on both partners increases significantly. This pressure can cause relationships to evolve rapidly, transforming cooperative bonds into competitive struggles or forcing new alliances to form. Understanding these complex dynamics helps biologists predict how ecosystems might respond to climate change and other environmental threats."
    ]

    return {
        "title": title,
        "paragraphs": paragraphs,
        "questions": build_fallback_questions(question_type),
        "source": "fallback",
        "message": "Model rate limit reached. Showing local fallback content.",
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.get("/generate")
def generate(exam: str = "CET4", question_type: str = "careful_reading") -> dict[str, object]:
    try:
        words = load_words(str(WORDS_FILE))

        passage = generate_passage(words, exam_type=exam)
        questions = generate_questions(passage, exam_type=exam, question_type=question_type)

        return {
            "title": passage["title"],
            "paragraphs": passage["paragraphs"],
            "questions": questions,
            "source": "model",
        }
    except Exception as exc:
        error_message = str(exc)
        if "429" in error_message or "rate limit" in error_message.lower():
            return build_fallback_payload(exam, question_type)
        raise HTTPException(status_code=500, detail=error_message) from exc
