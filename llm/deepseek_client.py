import json

from loguru import logger
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.settings import settings


class DeepSeekClient:
    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        self._model = settings.deepseek_model

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def _call(self, **kwargs):
        return self._client.chat.completions.create(**kwargs)

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        resp = self._call(model=self._model, messages=messages, temperature=temperature)
        content = resp.choices[0].message.content or ""
        logger.debug("deepseek chat -> {} chars", len(content))
        return content

    def chat_json(self, messages: list[dict], temperature: float = 0.0) -> dict:
        resp = self._call(
            model=self._model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or "{}"
        return json.loads(text)
