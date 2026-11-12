from __future__ import annotations

from typing import Any

from ..models import ActionProposal, NarrativeProposal


class GeminiIntentClient:
    """Thin async adapter around google-genai with no game-state authority."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        client: Any | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
            self._types = None
            return

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only in a misconfigured deployment
            raise RuntimeError("google-genai is required when Gemini is configured") from exc

        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    async def propose(self, system_instruction: str, prompt: str) -> str:
        if self._types is None:
            response = await self._client.propose(system_instruction, prompt)
            return response

        config = self._types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=ActionProposal.model_json_schema(),
            temperature=0,
            max_output_tokens=200,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        text = response.text
        if not text:
            raise ValueError("Gemini returned an empty response")
        return text


class GeminiNarrativeClient:
    """Structured narrative adapter kept separate from intent classification."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        client: Any | None = None,
    ) -> None:
        self.model = model
        if client is not None:
            self._client = client
            self._types = None
            return

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - deployment configuration failure
            raise RuntimeError("google-genai is required when Gemini is configured") from exc

        self._types = types
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    async def narrate(self, system_instruction: str, prompt: str) -> str:
        if self._types is None:
            return await self._client.narrate(system_instruction, prompt)

        config = self._types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=NarrativeProposal.model_json_schema(),
            temperature=0.7,
            max_output_tokens=220,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        text = response.text
        if not text:
            raise ValueError("Gemini returned an empty narrative")
        return text


