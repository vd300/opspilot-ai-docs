from dataclasses import dataclass

from app.router import RequestRouter


@dataclass(frozen=True)
class GraphDependencies:
    router: RequestRouter


def get_graph_dependencies() -> GraphDependencies:
    return GraphDependencies(router=RequestRouter())
