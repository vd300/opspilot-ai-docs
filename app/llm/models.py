import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelConfiguration:
    provider: str
    model_name: str
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 20.0


@runtime_checkable
class StructuredModel(Protocol):
    def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredOutput],
    ) -> StructuredOutput:
        """Return provider output validated as the requested Pydantic model."""


class FakeStructuredModel:
    def __init__(self, outputs: Mapping[str, BaseModel | dict[str, Any] | BaseException] | None = None) -> None:
        self.outputs = dict(outputs or {})
        self.calls: list[dict[str, str]] = []

    def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredOutput],
    ) -> StructuredOutput:
        self.calls.append(
            {
                "task": task,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model.__name__,
            }
        )
        output = self.outputs.get(task) or self.outputs.get(response_model.__name__)
        if output is None:
            raise ModelUnavailableError(f"No fake model output configured for {task}.")
        if isinstance(output, BaseException):
            raise output
        if isinstance(output, response_model):
            return output
        return response_model.model_validate(output)


class OpenAIResponsesStructuredModel:
    def __init__(self, config: ModelConfiguration) -> None:
        if not config.api_key:
            raise ModelUnavailableError("OpenAI model provider requires APP_MODEL_API_KEY.")
        self.config = config

    def generate_structured(
        self,
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredOutput],
    ) -> StructuredOutput:
        payload = {
            "model": self.config.model_name,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(response_model),
                    "schema": _strict_json_schema(response_model),
                    "strict": True,
                }
            },
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/responses",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ModelUnavailableError(f"Model provider returned HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ModelUnavailableError(f"Model provider request failed: {exc.reason!r}.") from exc

        output_text = _extract_output_text(response_data)
        try:
            return response_model.model_validate_json(output_text)
        except ValueError as exc:
            raise ModelUnavailableError(f"Model returned invalid structured output for {task}.") from exc


def _schema_name(response_model: type[BaseModel]) -> str:
    return response_model.__name__[:64]


def _strict_json_schema(response_model: type[BaseModel]) -> dict[str, Any]:
    schema = response_model.model_json_schema()
    _make_schema_strict(schema)
    return schema


def _make_schema_strict(schema: Any) -> None:
    if isinstance(schema, dict):
        schema.pop("default", None)
        if schema.get("type") == "object" or "properties" in schema:
            properties = schema.get("properties") or {}
            schema["additionalProperties"] = False
            schema["required"] = list(properties)
        for value in schema.values():
            _make_schema_strict(value)
    elif isinstance(schema, list):
        for item in schema:
            _make_schema_strict(item)


def _extract_output_text(response_data: Mapping[str, Any]) -> str:
    direct_text = response_data.get("output_text")
    if isinstance(direct_text, str):
        return direct_text

    for item in response_data.get("output", []):
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content", []):
            if isinstance(content, Mapping) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ModelUnavailableError("Model response did not contain output_text.")
