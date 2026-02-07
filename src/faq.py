from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from docx import Document
from rapidfuzz import fuzz, process

QUESTION_PREFIXES = ("q:", "question:", "вопрос:")
ANSWER_PREFIXES = ("a:", "answer:", "ответ:")


@dataclass(frozen=True)
class FaqItem:
    question: str
    answer: str


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _strip_prefix(text: str, prefixes: Iterable[str]) -> str:
    lowered = text.lower().strip()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text.strip()


def load_faq(docx_path: Path) -> list[FaqItem]:
    if not docx_path.exists():
        raise FileNotFoundError(f"FAQ файл не найден: {docx_path}")

    doc = Document(docx_path)
    items: list[FaqItem] = []

    current_question: str | None = None
    current_answer_parts: list[str] = []

    def flush() -> None:
        nonlocal current_question, current_answer_parts
        if current_question and current_answer_parts:
            items.append(
                FaqItem(
                    question=current_question.strip(),
                    answer="\n".join(part.strip() for part in current_answer_parts if part.strip()),
                )
            )
        current_question = None
        current_answer_parts = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        normalized = text.lower().strip()
        if normalized.startswith(QUESTION_PREFIXES):
            flush()
            current_question = _strip_prefix(text, QUESTION_PREFIXES)
            continue

        if normalized.startswith(ANSWER_PREFIXES):
            answer_text = _strip_prefix(text, ANSWER_PREFIXES)
            if current_question is None:
                current_question = answer_text
            else:
                current_answer_parts.append(answer_text)
            continue

        if current_question is None:
            current_question = text
        else:
            current_answer_parts.append(text)

    flush()

    return items


def find_best_answer(question: str, items: list[FaqItem]) -> tuple[FaqItem | None, float]:
    if not items:
        return None, 0.0

    normalized_question = _normalize(question)
    questions = [item.question for item in items]
    best_match = process.extractOne(
        normalized_question,
        questions,
        scorer=fuzz.WRatio,
    )
    if best_match is None:
        return None, 0.0

    matched_question, score, index = best_match
    item = items[index]

    keyword_score = fuzz.token_set_ratio(normalized_question, _normalize(matched_question))
    final_score = (score * 0.7) + (keyword_score * 0.3)

    return item, final_score
