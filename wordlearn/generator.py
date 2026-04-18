import json
import os
from typing import List

import httpx
from openai import OpenAI


OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
MOONSHOT_DEFAULT_MODEL = "kimi-k2.5"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"


def normalize_exam_type(exam_type: str) -> str:
    normalized = exam_type.strip().upper().replace("-", "")

    if normalized in {"CET4", "CET6", "IELTS"}:
        return normalized

    raise ValueError("exam_type must be one of: IELTS, CET4, CET6.")


def describe_exam_type(exam_type: str) -> str:
    normalized = normalize_exam_type(exam_type)

    if normalized == "CET4":
        return (
            "Target CET-4 difficulty: clear topic progression, mostly explicit information, "
            "accessible academic vocabulary, and limited inference."
        )
    if normalized == "CET6":
        return (
            "Target CET-6 difficulty: denser information, more complex sentence structures, "
            "more abstract ideas, and moderate inference."
        )

    return (
        "Target IELTS reading difficulty: academic tone, cohesive paragraph development, "
        "careful logical relations, and moderate-to-deeper inference."
    )


def load_env_file(env_path: str = ".env") -> None:
    if (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("MOONSHOT_API_KEY")
        or not os.path.exists(env_path)
    ):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


def build_prompt(words: List[str], exam_type: str) -> str:
    word_list = ", ".join(words)
    exam_description = describe_exam_type(exam_type)

    return f"""
You are an English exam passage generator.

Task:
Generate a reading comprehension passage suitable for {exam_type} students.

Requirements:
- You MUST naturally use ALL the following words in the passage.
- Words: {word_list}
- Length: 200-250 words
- Style: similar to IELTS / CET reading
- Keep coherence and logical flow.
- Exam target: {exam_type}
- Exam guidance: {exam_description}
- Generate a short title for the passage.
- Split the passage into 2 to 4 paragraphs.

Output ONLY valid JSON in this format:
{{
  "title": "string",
  "paragraphs": ["paragraph 1", "paragraph 2"]
}}
""".strip()


def build_client_and_model(model: str | None) -> tuple[OpenAI, str, float]:
    moonshot_api_key = os.environ.get("MOONSHOT_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    http_client = httpx.Client(trust_env=False)

    if moonshot_api_key:
        client = OpenAI(
            api_key=moonshot_api_key,
            base_url=MOONSHOT_BASE_URL,
            http_client=http_client,
        )
        return client, model or MOONSHOT_DEFAULT_MODEL, 1.0

    if openai_api_key:
        client = OpenAI(api_key=openai_api_key, http_client=http_client)
        return client, model or OPENAI_DEFAULT_MODEL, 0.7

    raise RuntimeError(
        "No API key found. Add MOONSHOT_API_KEY or OPENAI_API_KEY to the terminal environment or a .env file."
    )


def parse_json_payload(text: str) -> dict:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end + 1]
        return json.loads(candidate)

    raise RuntimeError("The model did not return valid JSON.")


def generate_passage(
    words: List[str],
    exam_type: str = "CET4",
    model: str | None = None,
) -> dict[str, object]:
    if not words:
        raise ValueError("Word list is empty.")

    load_env_file()
    client, resolved_model, temperature = build_client_and_model(model)
    prompt = build_prompt(words, normalize_exam_type(exam_type))

    response = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {"role": "system", "content": "You generate exam-quality English passages."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )

    text = response.choices[0].message.content
    if text is None:
        raise RuntimeError("The model returned an empty response.")

    passage = parse_json_payload(text)

    title = passage.get("title")
    paragraphs = passage.get("paragraphs")
    if not isinstance(title, str) or not title.strip():
        raise RuntimeError("The model returned an invalid passage title.")
    if not isinstance(paragraphs, list) or not paragraphs or not all(
        isinstance(paragraph, str) and paragraph.strip() for paragraph in paragraphs
    ):
        raise RuntimeError("The model returned invalid passage paragraphs.")

    return {
        "title": title.strip(),
        "paragraphs": [paragraph.strip() for paragraph in paragraphs],
    }
