"""Anthropic SDK ラッパー"""

import json
import anthropic
from dotenv import load_dotenv

from config import MODEL, MAX_TOKENS, TEMPERATURE, QUADRANTS
from prompts import (
    SYSTEM_PROMPT,
    QUADRANT_START_PROMPT,
    QUADRANT_FOLLOWUP_PROMPT,
    QUADRANT_COMPLETION_CHECK_PROMPT,
    SYNTHESIS_PROMPT,
    validate_response,
)

load_dotenv()


class EthicsNaviClient:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def ask_quadrant_questions_stream(
        self,
        case_overview: str,
        quadrant_key: str,
        conversation: list[dict],
        remaining_subtopics: list[str] | None = None,
    ):
        """象限の深掘り質問をストリーミングで生成"""
        quad = next(q for q in QUADRANTS if q["key"] == quadrant_key)

        if len(conversation) == 0:
            user_content = QUADRANT_START_PROMPT.format(
                quadrant_title=quad["title_ja"],
                case_overview=case_overview,
                subtopics="、".join(quad["subtopics"]),
            )
            messages = [{"role": "user", "content": user_content}]
        else:
            if remaining_subtopics is None:
                remaining_subtopics = quad["subtopics"]
            user_content = QUADRANT_FOLLOWUP_PROMPT.format(
                quadrant_title=quad["title_ja"],
                case_overview=case_overview,
                remaining_subtopics="、".join(remaining_subtopics),
            )
            messages = conversation + [{"role": "user", "content": user_content}]

        with self.client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def check_quadrant_completion(
        self,
        quadrant_key: str,
        conversation: list[dict],
    ) -> dict:
        """象限の完了状態をチェック（JSON応答）"""
        quad = next(q for q in QUADRANTS if q["key"] == quadrant_key)

        history_text = "\n".join(
            f"{'AI' if m['role'] == 'assistant' else 'ユーザー'}: {m['content']}"
            for m in conversation
        )

        prompt = QUADRANT_COMPLETION_CHECK_PROMPT.format(
            quadrant_title=quad["title_ja"],
            subtopics_list="、".join(quad["subtopics"]),
            conversation_history=history_text,
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {
                "is_complete": False,
                "covered_subtopics": [],
                "remaining_subtopics": quad["subtopics"],
                "summary": "",
            }

    def synthesize_table(
        self,
        case_overview: str,
        quadrant_summaries: dict[str, str],
    ) -> dict:
        """4象限を統合して構造化テーブルを生成"""
        prompt = SYNTHESIS_PROMPT.format(
            case_overview=case_overview,
            medical_indications_summary=quadrant_summaries.get("medical_indications", "（未整理）"),
            patient_preferences_summary=quadrant_summaries.get("patient_preferences", "（未整理）"),
            qol_summary=quadrant_summaries.get("qol", "（未整理）"),
            contextual_features_summary=quadrant_summaries.get("contextual_features", "（未整理）"),
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=4096,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {
                "table": {},
                "discussion_points": ["データの解析に失敗しました。再度お試しください。"],
                "tensions": [],
            }
