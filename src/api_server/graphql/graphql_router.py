"""GraphQL router for the API server."""

import strawberry
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from strawberry.fastapi import GraphQLRouter

from api_server.database import get_db_session
from api_server.graphql.context import GraphQLContext
from api_server.graphql.schema import Mutation, Query

# Create a module-level dependency for the database session
db_dependency = Depends(get_db_session)


async def get_context(
    request: Request,
    db_session: Session = db_dependency,
) -> GraphQLContext:
    """Get the GraphQL context with database session.

    Args:
        request: The FastAPI request
        db_session: The database session from the dependency

    Returns:
        A GraphQLContext instance for GraphQL resolvers
    """
    # Create a GraphQLContext instance with the database session and request
    # The service registry is automatically accessed by the context
    return GraphQLContext(db_session=db_session, request=request)


def create_graphql_router() -> APIRouter:
    """Create a GraphQL router for the API service.

    Returns:
        The GraphQL router
    """
    schema = strawberry.Schema(query=Query, mutation=Mutation)
    graphql_router = GraphQLRouter(
        schema,
        context_getter=get_context,
        graphql_ide="graphiql",
        tags=["GraphQL"],
    )
    return graphql_router
