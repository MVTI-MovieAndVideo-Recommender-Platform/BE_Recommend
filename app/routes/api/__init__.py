from fastapi.routing import APIRoute
from routes.api.recommend_media import (
    re_recommendation_endpoint,
    recommendation_endpoint,
)

recommend_route = APIRoute(
    path="/first_recommend", endpoint=recommendation_endpoint, methods=["POST"]
)

re_recommend_route = APIRoute(
    path="/re_recommend", endpoint=re_recommendation_endpoint, methods=["POST"]
)
