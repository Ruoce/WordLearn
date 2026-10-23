import logging
from pathlib import Path
from typing import Literal

from openai import APITimeoutError, APIConnectionError
from pydantic import BaseModel, Field, SecretStr

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from wordlearn.generator import build_client_and_model, generate_passage, normalize_exam_type
from wordlearn.loader import load_words, parse_uploaded_words, normalize_uploaded_words, MAX_UPLOAD_BYTES
from wordlearn.question_generator import generate_questions, normalize_question_type, validate_exam_question_type


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
    normalized_exam = normalize_exam_type(exam)

    if normalized_exam == "IELTS":
        paragraphs = [
            "In biology, close long-term contact between different species is often described as symbiosis.",
            "Such relationships may benefit both organisms, favour one side, or even harm a host.",
            "Because these patterns are widespread, they help scientists explain how ecosystems remain stable over time.",
            "One familiar example involves reef organisms that exchange shelter for nutrients.",
            "Another example can be found in insects that rely on mimicry to avoid predators.",
            "By copying the appearance of dangerous species, harmless creatures may improve their chances of survival.",
            "Environmental pressure can still change these arrangements when resources become limited.",
            "If conditions shift quickly, cooperation may weaken and competition may intensify.",
            "For this reason, the study of symbiotic systems is important for understanding ecological change.",
        ]
    elif normalized_exam == "CET6":
        paragraphs = [
            "In the natural world, the relationships between species often extend beyond simple competition for survival.",
            "Symbiosis refers to close and lasting contact between different organisms, and it may produce benefits, costs, or a mixture of both.",
            "Some creatures develop mimicry or other adaptations in order to improve their position within these relationships.",
            "Scientists examine such behavior to understand how environmental pressure shapes evolutionary change.",
            "This knowledge also helps researchers predict how ecosystems may respond to future disturbance.",
        ]
    else:
        paragraphs = [
            "In the natural world, the relationships between different species often go beyond simple survival.",
            "Symbiosis refers to the close and long-term interaction between two different biological organisms.",
            "These connections can be beneficial, neutral, or harmful depending on the circumstances.",
            "Scientists study such behavior to understand adaptation and ecological balance.",
        ]

    return {
        "title": title,
        "paragraphs": paragraphs,
        "questions": build_fallback_questions(question_type),
        "source": "fallback",
        "message": "The configured cloud model hit a rate limit, so local fallback content is being shown.",
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


class GenerateRequest(BaseModel):
    exam: Literal["CET4", "CET6", "IELTS"] = "CET4"
    question_type: Literal["careful_reading", "banked_cloze", "paragraph_matching", "tfng"] = "careful_reading"
    provider: Literal["openai", "moonshot", "deepseek", "ollama"]
    api_key: SecretStr = SecretStr("")
    model: str = Field(default="", max_length=200)
    words: list[str] | None = Field(default=None, max_length=100)


@app.post("/words/upload")
async def upload_words(request: Request, filename: str) -> dict[str, object]:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="文件不能超过 5 MB。")
    try:
        words = parse_uploaded_words(bytes(content), filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"words": words, "count": len(words)}


@app.post("/models")
def list_models(request: GenerateRequest) -> dict[str, object]:
    key = request.api_key.get_secret_value().strip()
    if request.provider != "ollama" and not key:
        raise HTTPException(status_code=400, detail="请先输入 API 密钥。")
    client = None
    try:
        client, _, _ = build_client_and_model(None, {"provider": request.provider, "api_key": key})
        models = sorted({item.id for item in client.models.list()})
        return {"models": models}
    except Exception:
        raise HTTPException(status_code=502, detail="无法获取模型列表，请检查密钥和服务连接，或手动填写模型名称。") from None
    finally:
        if client is not None:
            client.close()


@app.post("/generate")
def generate_with_settings(request: GenerateRequest) -> dict[str, object]:
    key = request.api_key.get_secret_value().strip()
    if request.provider != "ollama" and not key:
        raise HTTPException(status_code=400, detail="请填写所选提供方的 API 密钥。")
    settings = {"provider": request.provider, "api_key": key, "model": request.model.strip()}
    try:
        words = normalize_uploaded_words(request.words) if request.words is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return run_generation(request.exam, request.question_type, settings, words)


def run_generation(exam: str, question_type: str, settings: dict, words: list[str] | None = None) -> dict[str, object]:
    try:
        validate_exam_question_type(exam, question_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    stage = "读取词表"
    try:
        if words is None:
            words = load_words(str(WORDS_FILE))

        stage = "生成文章"
        passage = generate_passage(words, exam_type=exam, settings=settings)
        stage = "生成题目"
        questions = generate_questions(passage, exam_type=exam, question_type=question_type, settings=settings)

        return {
            "title": passage["title"],
            "paragraphs": passage["paragraphs"],
            "questions": questions,
            "source": "model",
        }
    except Exception as exc:
        logging.getLogger(__name__).warning("Generation failed: stage=%s type=%s status=%s", stage, type(exc).__name__, getattr(exc, "status_code", None))
        if isinstance(exc, APITimeoutError):
            raise HTTPException(status_code=504, detail=f"{stage}时模型响应超时，请稍后重试或切换模型。") from None
        if isinstance(exc, APIConnectionError):
            raise HTTPException(status_code=502, detail=f"{stage}时无法连接模型服务，请检查网络或本地服务。") from None
        error_message = str(exc)
        if settings["provider"] != "ollama" and (
            "429" in error_message or "rate limit" in error_message.lower()
        ):
            return build_fallback_payload(exam, question_type)
        status = getattr(exc, "status_code", None)
        if status in {401, 403}:
            detail = "密钥无效或无访问权限，请检查模型与密钥设置。"
        elif status in {400, 404, 422}:
            detail = f"{stage}失败：模型服务拒绝请求，请确认所选模型支持对话生成。"
        elif isinstance(exc, RuntimeError):
            detail = f"{stage}失败：模型返回内容未符合练习格式，请重试或切换模型。"
        else:
            detail = f"{stage}失败，请检查网络连接及账户额度后重试。"
        raise HTTPException(status_code=502, detail=detail) from None
