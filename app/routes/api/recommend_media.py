from database import mysql_conn
from fastapi import BackgroundTasks, Depends, Request
from routes.apihelper import recommend_media_helper
from sqlalchemy.ext.asyncio import AsyncSession


async def recommendation_endpoint(
    background_tasks: BackgroundTasks,
    request: Request,
    mysql_db: AsyncSession = Depends(mysql_conn.get_db),
):
    body = await request.json()
    recommender_input = {
        "user_mbti": body.get("user_mbti"),
        "input_media_title": body.get("input_media_title"),
        "previous_recommendations": None,
    }
    recommend_list = await recommend_media_helper.process_recommendations(
        request, recommender_input, mysql_db, background_tasks
    )
    return {"result": recommend_list}


async def re_recommendation_endpoint(
    background_tasks: BackgroundTasks,
    request: Request,
    mysql_db: AsyncSession = Depends(mysql_conn.get_db),
):
    body = await request.json()
    recommender_input = {
        "user_mbti": body.get("user_mbti"),
        "input_media_title": body.get("input_media_title"),
        "previous_recommendations": body.get("previous_recommendations"),
    }
    recommend_list = await recommend_media_helper.process_recommendations(
        request, recommender_input, mysql_db, background_tasks, re_recommend=True
    )
    return {"result": recommend_list}
