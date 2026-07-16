from dataclasses import dataclass

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import get_settings
from app.persistence import InvestigationRepository, SQLiteInvestigationRepository
from app.router import RequestRouter


@dataclass
class GraphDependencies:
    router: RequestRouter
    investigation_repository: InvestigationRepository | None = None
    checkpointer: InMemorySaver | None = None


def get_graph_dependencies() -> GraphDependencies:
    settings = get_settings()
    return GraphDependencies(
        router=RequestRouter(),
        investigation_repository=SQLiteInvestigationRepository(
            settings.persistence_database_path
        ),
        checkpointer=InMemorySaver(),
    )
