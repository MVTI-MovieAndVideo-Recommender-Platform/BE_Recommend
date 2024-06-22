import os

from resources.load_resource import Recommender

base_path = os.path.dirname(os.path.abspath(__file__))
print(base_path)
recommend_helper = Recommender(
    f"{base_path}/data/mbti_embeddings_dict.pkl",
    f"{base_path}/data/contents_embeddings_dict.pkl",
    f"{base_path}/data/gbm_model.pkl",
    f"{base_path}/data/media_data.csv",
)
