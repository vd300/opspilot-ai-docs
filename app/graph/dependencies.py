from dataclasses import dataclass

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import get_settings
from app.llm import StructuredModel, create_structured_model
from app.persistence import InvestigationRepository, SQLiteInvestigationRepository
from app.router import RequestRouter
from app.router.llm_classifier import LLMRouteClassifier


@dataclass
class GraphDependencies:
    router: RequestRouter
    reasoning_model: StructuredModel | None = None
    investigation_repository: InvestigationRepository | None = None
    checkpointer: InMemorySaver | None = None


def get_graph_dependencies() -> GraphDependencies:
    settings = get_settings()
    model = create_structured_model(settings)
    classifier = LLMRouteClassifier(model) if model is not None else None
    return GraphDependencies(
        router=RequestRouter(classifier=classifier),
        reasoning_model=model,
        investigation_repository=SQLiteInvestigationRepository(
            settings.persistence_database_path
        ),
        checkpointer=InMemorySaver(),
    )
