import asyncio

from database import mongo_conn, mysql_conn
from fastapi import BackgroundTasks
from model.table import RecommendORM
from resources import recommend_helper
from routes.apihelper import base64_to_uuid, message, produce_message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def insert_recommend_db(model_orm: RecommendORM, mysql_db: AsyncSession):
    mysql_db.add(model_orm)
    await mysql_db.commit()
    result = await get_recommend(model_orm, mysql_db)
    return result
    # return message("insert", "preference", result)


async def get_recommend(model_orm: RecommendORM, mysql_db: AsyncSession):
    query = (
        select(RecommendORM)
        .where(RecommendORM.user_id == model_orm.user_id)
        .order_by(RecommendORM.recommendation_id.desc())
        .limit(1)
    )
    return (await mysql_db.execute(query)).scalar_one_or_none()


async def get_media_ids_from_titles(titles):
    return await mongo_conn.content.media.find(
        {"title": {"$in": titles}}, {"_id": 0, "id": 1}
    ).to_list(length=None)


async def get_recommendations_with_details(titles, length=20):
    return await mongo_conn.content.media.find(
        {"title": {"$in": titles}}, {"_id": 0, "id": 1, "title": 1, "posterurl_count": 1}
    ).to_list(length=length)


async def save_recommendation_to_db(recommend_orm, get_db):
    async for session in get_db():
        db_result = await insert_recommend_db(recommend_orm, session)
        await produce_message(message("insert", "recommendation", db_result))
        break  # To exit the async generator


async def process_recommendations(
    recommender_input: dict,
    background_tasks: BackgroundTasks,
    re_recommend=False,
):
    result, re_recommend = await recommend_helper.get_recommendations(
        recommender_input=recommender_input
    )

    input_media_cursor = get_media_ids_from_titles(recommender_input["input_media_title"])
    recommend_cursor = get_recommendations_with_details(result)

    input_media_id_list, recommend_list = await asyncio.gather(input_media_cursor, recommend_cursor)
    if recommender_input.get("user_id"):
        recommend_orm = RecommendORM(
            user_id=recommender_input["user_id"],
            user_mbti=recommender_input["user_mbti"].upper(),
            input_media_id=", ".join([str(id.get("id")) for id in input_media_id_list]),
            recommended_media_id=", ".join([str(i.get("id")) for i in recommend_list]),
            re_recommendation=re_recommend,
        )
        background_tasks.add_task(save_recommendation_to_db, recommend_orm, mysql_conn.get_db)

    return recommend_list
