"""Root GraphQL schema. Each app exposes `Query` / `Mutation` in its `schema.py`;
add them to the lists below to merge them into the API."""

import strawberry
from strawberry.tools import merge_types
from strawberry_django.optimizer import DjangoOptimizerExtension

from project.users import schema as users_schema

Query = merge_types("Query", (users_schema.Query,))
Mutation = merge_types("Mutation", (users_schema.Mutation,))

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[DjangoOptimizerExtension],
)
