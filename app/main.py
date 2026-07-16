from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.investigations import router as investigations_router
from app.api.routes.router import router as request_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.graph.dependencies import GraphDependencies, get_graph_dependencies
from app.middleware.request_id import RequestIdMiddleware


def create_app(graph_dependencies: GraphDependencies | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    dependencies = graph_dependencies or get_graph_dependencies()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.state.graph_dependencies = dependencies
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(request_router)
    app.include_router(investigations_router)
    return app


app = create_app()
