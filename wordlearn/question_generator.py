from wordlearn.generator import (
    build_client_and_model,
    describe_exam_type,
    normalize_exam_type,
    parse_json_payload,
)


def normalize_question_type(question_type: str) -> str:
    normalized = question_type.strip().lower().replace("-", "_")
    aliases = {
        "mcq": "careful_reading",
        "careful_reading": "careful_reading",
        "completion": "banked_cloze",
        "cloze": "banked_cloze",
        "banked_cloze": "banked_cloze",
        "matching_headings": "paragraph_matching",
        "matching": "paragraph_matching",
        "paragraph_matching": "paragraph_matching",
        "tfng": "tfng",
    }
    normalized = aliases.get(normalized, normalized)
    allowed = {"careful_reading", "banked_cloze", "paragraph_matching", "tfng"}
    if normalized not in allowed:
        raise ValueError(
            "question_type must be one of: careful_reading, banked_cloze, paragraph_matching, tfng."
        )
    return normalized


def build_question_prompt(
    passage: dict[str, object],
    exam_type: str,
    question_type: str,
) -> str:
    normalized_exam_type = normalize_exam_type(exam_type)
    normalized_question_type = normalize_question_type(question_type)
    exam_description = describe_exam_type(normalized_exam_type)
    title = str(passage["title"])
    paragraphs = passage["paragraphs"]
    paragraph_text = "\n\n".join(str(paragraph) for paragraph in paragraphs)

    task_map = {
        "careful_reading": """
Generate ONLY careful reading questions.
- Create 5 multiple-choice questions.
- Each question must have 4 options (A, B, C, D).
- Exactly 1 correct answer.
- Focus on detail, inference, main idea, and logical understanding.
Output format:
{
  "question_type": "careful_reading",
  "careful_reading": [
    {
      "question": "string",
      "options": {"A": "string", "B": "string", "C": "string", "D": "string"},
      "answer": "A"
    }
  ]
}
""",
        "banked_cloze": """
Generate ONLY banked cloze questions.
- Create 5 fill-in-the-blank items.
- Provide a word bank with 7 candidate words, including distractors.
- Every prompt must contain one blank written as ________.
- Every answer must be one of the words from the word bank.
Output format:
{
  "question_type": "banked_cloze",
  "banked_cloze": {
    "instruction": "string",
    "word_bank": ["word1", "word2", "word3"],
    "items": [
      {
        "prompt": "string with ________ blank",
        "answer": "string"
      }
    ]
  }
}
""",
        "paragraph_matching": """
Generate ONLY paragraph matching questions.
- Use paragraph labels A, B, C... based on the passage order.
- Create headings or information prompts that must be matched to paragraphs.
Output format:
{
  "question_type": "paragraph_matching",
  "paragraph_matching": {
    "instruction": "string",
    "headings": [
      {"key": "i", "text": "string"}
    ],
    "items": [
      {"paragraph": "A", "answer": "i"}
    ]
  }
}
""",
        "tfng": """
Generate ONLY True / False / Not Given questions.
- Create 5 statements.
- Each statement must be clearly answerable from the passage.
Output format:
{
  "question_type": "tfng",
  "tfng": [
    {
      "statement": "string",
      "answer": "True"
    }
  ]
}
""",
    }

    return f"""
You create high-quality reading comprehension questions.

Task:
Generate a structured question set based on the passage.

Requirements:
- Exam target: {normalized_exam_type}
- Exam guidance: {exam_description}
- Question type: {normalized_question_type}
- Match the question difficulty to the target exam.
- Avoid ambiguous, subjective, or duplicate questions.
- Return ONLY valid JSON.

{task_map[normalized_question_type]}

Passage:
Title: {title}

{paragraph_text}
""".strip()


def validate_careful_reading(items: object) -> list[dict[str, object]]:
    if not isinstance(items, list) or not items:
        raise RuntimeError("The model returned invalid careful reading data.")
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("The model returned an invalid careful reading item.")
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise RuntimeError("The model returned an invalid careful reading question.")
        options = item.get("options")
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            raise RuntimeError("The model returned invalid careful reading options.")
        if item.get("answer") not in {"A", "B", "C", "D"}:
            raise RuntimeError("The model returned an invalid careful reading answer.")
    return items


def validate_banked_cloze(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise RuntimeError("The model returned invalid banked cloze data.")
    instruction = data.get("instruction")
    word_bank = data.get("word_bank")
    items = data.get("items")
    if not isinstance(instruction, str) or not instruction.strip():
        raise RuntimeError("The model returned an invalid banked cloze instruction.")
    if not isinstance(word_bank, list) or len(word_bank) < 5:
        raise RuntimeError("The model returned an invalid word bank.")
    if not isinstance(items, list) or not items:
        raise RuntimeError("The model returned invalid banked cloze items.")
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("The model returned an invalid banked cloze item.")
        prompt = item.get("prompt")
        answer = item.get("answer")
        if not isinstance(prompt, str) or "____" not in prompt:
            raise RuntimeError("The model returned an invalid banked cloze prompt.")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("The model returned an invalid banked cloze answer.")
    return data


def validate_paragraph_matching(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise RuntimeError("The model returned invalid paragraph matching data.")
    instruction = data.get("instruction")
    headings = data.get("headings")
    items = data.get("items")
    if not isinstance(instruction, str) or not instruction.strip():
        raise RuntimeError("The model returned an invalid paragraph matching instruction.")
    if not isinstance(headings, list) or not headings:
        raise RuntimeError("The model returned invalid paragraph matching headings.")
    if not isinstance(items, list) or not items:
        raise RuntimeError("The model returned invalid paragraph matching items.")
    return data


def validate_tfng(items: object) -> list[dict[str, str]]:
    if not isinstance(items, list) or not items:
        raise RuntimeError("The model returned invalid TFNG data.")
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("The model returned an invalid TFNG item.")
        if not isinstance(item.get("statement"), str) or not item["statement"].strip():
            raise RuntimeError("The model returned an invalid TFNG statement.")
        if item.get("answer") not in {"True", "False", "Not Given"}:
            raise RuntimeError("The model returned an invalid TFNG answer.")
    return items


def generate_questions(
    passage: dict[str, object],
    exam_type: str = "CET4",
    question_type: str = "careful_reading",
    model: str | None = None,
) -> dict[str, object]:
    paragraphs = passage.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError("Passage is empty.")

    normalized_question_type = normalize_question_type(question_type)
    client, resolved_model, temperature = build_client_and_model(model)
    prompt = build_question_prompt(passage, exam_type, normalized_question_type)
    messages = [
        {"role": "system", "content": "You create structured reading comprehension question sets."},
        {"role": "user", "content": prompt},
    ]
    questions: dict[str, object] | None = None
    last_error: Exception | None = None

    for attempt in range(3):
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature if attempt == 0 else 0.0,
        )

        text = response.choices[0].message.content
        if text is None:
            last_error = RuntimeError("The model returned empty questions.")
        else:
            try:
                questions = parse_json_payload(text)
                break
            except Exception as exc:
                last_error = exc

        messages = [
            {
                "role": "system",
                "content": (
                    "You create structured reading comprehension question sets. "
                    "Return only strict JSON with double-quoted keys and no markdown."
                ),
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": text or ""},
            {
                "role": "user",
                "content": (
                    "Your previous response was not valid JSON. "
                    "Rewrite the same question set as strict JSON only."
                ),
            },
        ]

    if questions is None:
        raise RuntimeError(f"The model returned invalid questions JSON: {last_error}") from last_error

    result = {"question_type": normalized_question_type}

    if normalized_question_type == "careful_reading":
        result["careful_reading"] = validate_careful_reading(
            questions.get("careful_reading") or questions.get("mcq")
        )
    elif normalized_question_type == "banked_cloze":
        result["banked_cloze"] = validate_banked_cloze(
            questions.get("banked_cloze") or questions.get("completion")
        )
    elif normalized_question_type == "paragraph_matching":
        result["paragraph_matching"] = validate_paragraph_matching(
            questions.get("paragraph_matching") or questions.get("matching_headings")
        )
    else:
        result["tfng"] = validate_tfng(questions.get("tfng"))

    return result
