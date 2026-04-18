import json
import os
from typing import List

import httpx
from openai import OpenAI


OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
MOONSHOT_DEFAULT_MODEL = "kimi-k2.5"
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
OLLAMA_DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"


def resolve_provider() -> str:
    provider = os.environ.get("WORDLEARN_PROVIDER", "auto").strip().lower()
    allowed = {"auto", "openai", "moonshot", "ollama"}
    if provider not in allowed:
        raise RuntimeError(
            "WORDLEARN_PROVIDER must be one of: auto, openai, moonshot, ollama."
        )
    return provider


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


def get_passage_requirements(exam_type: str) -> dict[str, int]:
    normalized = normalize_exam_type(exam_type)

    if normalized == "CET4":
        return {
            "min_words": 220,
            "max_words": 320,
            "min_paragraphs": 3,
            "max_paragraphs": 4,
        }
    if normalized == "CET6":
        return {
            "min_words": 320,
            "max_words": 480,
            "min_paragraphs": 5,
            "max_paragraphs": 6,
        }

    return {
        "min_words": 650,
        "max_words": 850,
        "min_paragraphs": 9,
        "max_paragraphs": 11,
    }


def load_env_file(env_path: str = ".env") -> None:
    if not os.path.exists(env_path):
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
    normalized_exam_type = normalize_exam_type(exam_type)
    exam_description = describe_exam_type(normalized_exam_type)
    requirements = get_passage_requirements(normalized_exam_type)

    return f"""
You are an English exam passage generator.

Task:
Generate a reading comprehension passage suitable for {normalized_exam_type} students.

Requirements:
- You MUST naturally use ALL the following words in the passage.
- Words: {word_list}
- Length: {requirements["min_words"]}-{requirements["max_words"]} words
- Style: similar to IELTS / CET reading
- Keep coherence and logical flow.
- Exam target: {normalized_exam_type}
- Exam guidance: {exam_description}
- Generate a short title for the passage.
- Paragraph count: {requirements["min_paragraphs"]}-{requirements["max_paragraphs"]} paragraphs.
- For IELTS, use shorter academic paragraphs like a real reading passage, not 3 long blocks.

Output ONLY valid JSON in this format:
{{
  "title": "string",
  "paragraphs": ["paragraph 1", "paragraph 2"]
}}
""".strip()


def validate_passage_payload(passage: dict[str, object], exam_type: str) -> dict[str, object]:
    requirements = get_passage_requirements(exam_type)
    title = passage.get("title")
    paragraphs = passage.get("paragraphs")

    if not isinstance(title, str) or not title.strip():
        raise RuntimeError("The model returned an invalid passage title.")
    if not isinstance(paragraphs, list) or not paragraphs or not all(
        isinstance(paragraph, str) and paragraph.strip() for paragraph in paragraphs
    ):
        raise RuntimeError("The model returned invalid passage paragraphs.")
    if not requirements["min_paragraphs"] <= len(paragraphs) <= requirements["max_paragraphs"]:
        raise RuntimeError(
            "The model returned the wrong number of paragraphs "
            f"for {normalize_exam_type(exam_type)}."
        )

    return {
        "title": title.strip(),
        "paragraphs": [paragraph.strip() for paragraph in paragraphs],
    }


def build_client_and_model(model: str | None) -> tuple[OpenAI, str, float]:
    load_env_file()
    provider = resolve_provider()
    moonshot_api_key = os.environ.get("MOONSHOT_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    ollama_model = os.environ.get("OLLAMA_MODEL")
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_DEFAULT_BASE_URL)
    ollama_api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    http_client = httpx.Client(trust_env=False)

    if provider == "ollama" or (
        provider == "auto" and (ollama_model or os.environ.get("OLLAMA_BASE_URL"))
    ):
        resolved_model = model or ollama_model
        if not resolved_model:
            raise RuntimeError(
                "Ollama is selected, but no model was provided. "
                "Set OLLAMA_MODEL in .env or pass --model."
            )
        client = OpenAI(
            api_key=ollama_api_key,
            base_url=ollama_base_url,
            http_client=http_client,
        )
        return client, resolved_model, 0.7

    if provider in {"moonshot", "auto"} and moonshot_api_key:
        client = OpenAI(
            api_key=moonshot_api_key,
            base_url=MOONSHOT_BASE_URL,
            http_client=http_client,
        )
        return client, model or MOONSHOT_DEFAULT_MODEL, 1.0

    if provider in {"openai", "auto"} and openai_api_key:
        client = OpenAI(api_key=openai_api_key, http_client=http_client)
        return client, model or OPENAI_DEFAULT_MODEL, 0.7

    raise RuntimeError(
        "No usable model provider found. Configure WORDLEARN_PROVIDER plus the matching environment "
        "variables, or add MOONSHOT_API_KEY / OPENAI_API_KEY, or set OLLAMA_MODEL for a local Ollama model."
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
    normalized_exam_type = normalize_exam_type(exam_type)
    prompt = build_prompt(words, normalized_exam_type)

    messages = [
        {"role": "system", "content": "You generate exam-quality English passages."},
        {"role": "user", "content": prompt},
    ]
    passage: dict[str, object] | None = None
    last_error: Exception | None = None

    for attempt in range(3):
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature if attempt == 0 else 0.0,
        )

        text = response.choices[0].message.content
        if text is None:
            last_error = RuntimeError("The model returned an empty response.")
        else:
            try:
                passage = validate_passage_payload(
                    parse_json_payload(text),
                    normalized_exam_type,
                )
                break
            except Exception as exc:
                last_error = exc

        messages = [
            {
                "role": "system",
                "content": (
                    "You generate exam-quality English passages. "
                    "Return only strict JSON with double-quoted keys and no markdown."
                ),
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": text or ""},
            {
                "role": "user",
                "content": (
                    "Your previous response was not valid JSON. "
                    "Rewrite the same passage as strict JSON only, and obey the required paragraph count."
                ),
            },
        ]

    if passage is None:
        raise RuntimeError(f"The model returned invalid passage JSON: {last_error}") from last_error
    return passage
