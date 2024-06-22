from database import mongo_conn
from fastapi import BackgroundTasks, HTTPException, Request
from routes.apihelper import base64_to_uuid, recommend_media_helper


async def recommendation_endpoint(background_tasks: BackgroundTasks, request: Request):
    body = await request.json()
    if request.state.token and (user_id := base64_to_uuid(request.state.token)):
        if (
            user_mbti := await mongo_conn.member.user.find_one(
                {"_id": user_id}, {"_id": 1, "mbti": 1}
            )
        ) and user_mbti.get("mbti"):
            recommender_input = {
                "user_id": user_mbti.get("_id"),
                "user_mbti": user_mbti.get("mbti"),
                "input_media_title": body.get("input_media_title"),
                "previous_recommendations": None,
            }
        else:
            raise HTTPException(status_code=400, detail="mbti정보가 없습니다.")
    else:
        recommender_input = {
            "user_mbti": body.get("user_mbti"),
            "input_media_title": body.get("input_media_title"),
            "previous_recommendations": None,
        }
    recommend_list = await recommend_media_helper.process_recommendations(
        recommender_input, background_tasks
    )
    return {"result": recommend_list}


async def re_recommendation_endpoint(background_tasks: BackgroundTasks, request: Request):
    body = await request.json()
    if request.state.token and (user_id := base64_to_uuid(request.state.token)):
        if (
            user_mbti := await mongo_conn.member.user.find_one(
                {"_id": user_id}, {"_id": 1, "mbti": 1}
            )
        ) and user_mbti.get("mbti"):
            recommender_input = {
                "user_id": user_mbti.get("_id"),
                "user_mbti": user_mbti.get("mbti"),
                "input_media_title": body.get("input_media_title"),
                "previous_recommendations": body.get("previous_recommendations"),
            }
        else:
            raise HTTPException(status_code=400, detail="mbti정보가 없습니다.")
    else:
        recommender_input = {
            "user_mbti": body.get("user_mbti"),
            "input_media_title": body.get("input_media_title"),
            "previous_recommendations": body.get("previous_recommendations"),
        }
    recommend_list = await recommend_media_helper.process_recommendations(
        recommender_input, background_tasks, re_recommend=True
    )
    return {"result": recommend_list}
