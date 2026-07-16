from app.core.config import Settings
from app.llm.models import (
    FakeStructuredModel,
    ModelConfiguration,
    OpenAIResponsesStructuredModel,
    StructuredModel,
)


def create_structured_model(settings: Settings) -> StructuredModel | None:
    if settings.model_provider == "stub":
        return FakeStructuredModel()
    if settings.model_provider == "openai":
        if not settings.model_api_key:
            return None
        return OpenAIResponsesStructuredModel(
            ModelConfiguration(
                provider=settings.model_provider,
                model_name=settings.model_name,
                api_key=settings.model_api_key,
                base_url=settings.model_base_url,
                timeout_seconds=settings.model_timeout_seconds,
            )
        )
    return None
