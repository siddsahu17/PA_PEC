import json
import logging
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


class DiagramRAGAgent:
    """
    Retrieves factual diagram data from JSON files in backend/data/.
    Uses LLM-assisted matching to find the best diagram for a user query.
    Add a new diagram by dropping a JSON file into backend/data/.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._index: dict[str, dict] = {}
        self._load_index()

    def _load_index(self):
        if not DATA_DIR.exists():
            logger.warning("Data directory not found: %s — no diagrams loaded", DATA_DIR)
            return
        for json_file in DATA_DIR.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                self._index[json_file.stem] = data
                logger.info("Loaded diagram: %s", json_file.stem)
            except Exception as e:
                logger.error("Failed to load %s: %s", json_file.name, e)

    def retrieve(self, query: str, topic_hint: Optional[str] = None) -> Optional[dict]:
        """
        Return the best matching diagram dict for the given query.

        Args:
            query: The full user utterance (used for LLM matching fallback).
            topic_hint: Snake_case key returned by IntentRouter (e.g. 'digestive_system').
                        When provided, direct and partial matching are tried first.

        Returns:
            The diagram JSON dict, or None if no match found.
        """
        if not self._index:
            logger.error("No diagrams loaded — add JSON files to %s", DATA_DIR)
            return None

        # 1. Exact key match from router hint
        if topic_hint and topic_hint in self._index:
            logger.info("Direct key match: %s", topic_hint)
            return self._index[topic_hint]

        # 2. Partial key match (handles slight naming variations)
        if topic_hint:
            hint = topic_hint.lower().replace(" ", "_")
            for key in self._index:
                if hint in key or key in hint:
                    logger.info("Partial key match: %s -> %s", hint, key)
                    return self._index[key]

        # 3. Keyword scan over the raw query
        query_lower = query.lower()
        for key, data in self._index.items():
            keywords: list[str] = data.get("keywords", [])
            if any(kw.lower() in query_lower for kw in keywords):
                logger.info("Keyword match: %s", key)
                return data

        # 4. LLM matching as final fallback
        return self._llm_match(query)

    def _llm_match(self, query: str) -> Optional[dict]:
        available = "\n".join(
            f"- {key}: {data.get('topic', key)} "
            f"(keywords: {', '.join(data.get('keywords', [])[:6])})"
            for key, data in self._index.items()
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Match the user query to exactly one diagram key from the list. "
                            "Return ONLY the key string (e.g. 'digestive_system'). "
                            "If no diagram is a reasonable match, return 'none'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\n\nAvailable diagrams:\n{available}",
                    },
                ],
                max_tokens=30,
                temperature=0,
            )
            key = response.choices[0].message.content.strip().lower().replace(" ", "_")
            if key == "none":
                return None
            matched = self._index.get(key)
            if matched:
                logger.info("LLM matched query to: %s", key)
            return matched
        except Exception as e:
            logger.error("LLM diagram matching failed: %s", e)
            return None

    @property
    def available_topics(self) -> list[str]:
        return list(self._index.keys())
