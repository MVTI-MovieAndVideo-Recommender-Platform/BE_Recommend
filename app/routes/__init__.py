from fastapi import APIRouter
from routes.api import re_recommend_route, recommend_route

router = APIRouter(tags=["Recommendation"])

router.routes.append(recommend_route)
router.routes.append(re_recommend_route)
