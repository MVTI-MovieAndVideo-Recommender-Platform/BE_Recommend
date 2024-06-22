import asyncio
from concurrent.futures import ThreadPoolExecutor

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler


class Recommender:
    def __init__(self, mbti_embedding, contents_embedding, best_gbm, media_data):
        self.media_data_path = media_data
        self.user_embedding_path = mbti_embedding
        self.contents_embedding_path = contents_embedding
        self.best_gbm_path = best_gbm
        self.media_data = None
        self.user_embedding = None
        self.contents_embedding = None
        self.best_gbm = None
        self.contents = None
        self.genres = None
        self.cbf_model_input_scaled = None
        self.executor = ThreadPoolExecutor(max_workers=20)  # 비동기 작업을 위한 ThreadPoolExecutor

    async def init_data(self):
        await self._load_data()
        loop = asyncio.get_event_loop()
        self.contents = await loop.run_in_executor(self.executor, self._normalize_popularity_score)
        self.genres = await loop.run_in_executor(self.executor, self._get_genres)
        self.cbf_model_input_scaled = await loop.run_in_executor(
            self.executor, self._scale_features
        )

    def _read_csv_with_encoding(self, path):
        return pd.read_csv(path, encoding="utf-8-sig")

    async def _load_data(self):
        loop = asyncio.get_event_loop()
        self.media_data, self.user_embedding, self.contents_embedding, self.best_gbm = (
            await asyncio.gather(
                loop.run_in_executor(
                    self.executor, self._read_csv_with_encoding, self.media_data_path
                ),
                loop.run_in_executor(self.executor, joblib.load, self.user_embedding_path),
                loop.run_in_executor(self.executor, joblib.load, self.contents_embedding_path),
                loop.run_in_executor(self.executor, joblib.load, self.best_gbm_path),
            )
        )

    def _normalize_popularity_score(self):
        content = self.media_data[
            ["Title", "Genres", "Overview", "Rating Value", "Rating Count"]
        ].copy()
        scaler = MinMaxScaler()
        content["Normalized Popularity Score"] = scaler.fit_transform(content[["Rating Count"]])
        return content

    def _get_genres(self):
        return self.contents["Genres"].str.get_dummies(sep=", ")

    def _scale_features(self):
        return StandardScaler().fit_transform(
            np.hstack([self.genres.values, self.contents["Rating Value"].values.reshape(-1, 1)])
        )

    def calculate_similarity(self, embedding, user_embedding):
        return np.dot(embedding, user_embedding) / (
            np.linalg.norm(embedding) * np.linalg.norm(user_embedding)
        )

    async def recommend_contents_by_mbti(
        self, user_embedding, popular_content_embeddings_dict, top_n=100
    ):
        loop = asyncio.get_event_loop()
        similarities = await loop.run_in_executor(
            self.executor,
            lambda: [
                (content, self.calculate_similarity(embedding, user_embedding))
                for content, embedding in popular_content_embeddings_dict.items()
            ],
        )
        recommended_contents = sorted(similarities, key=lambda x: x[1], reverse=True)
        return recommended_contents[:top_n]

    async def recommend_similar_contents(
        self, preferred_contents, popular_content_embeddings_dict, top_n=100
    ):
        loop = asyncio.get_event_loop()
        similar_contents = await loop.run_in_executor(
            self.executor,
            self._calculate_similarities,
            preferred_contents,
            popular_content_embeddings_dict,
        )
        similar_contents = sorted(similar_contents.items(), key=lambda x: x[1], reverse=True)
        return similar_contents[:top_n]

    def _calculate_similarities(self, preferred_contents, popular_content_embeddings_dict):
        similar_contents = {}
        for preferred_content in preferred_contents:
            if preferred_content in self.contents_embedding:
                preferred_embedding = self.contents_embedding[preferred_content]
                for other_content, embedding in popular_content_embeddings_dict.items():
                    if other_content not in preferred_contents:
                        similarity = similarity = np.dot(preferred_embedding, embedding) / (
                            np.linalg.norm(preferred_embedding) * np.linalg.norm(embedding)
                        )
                        if other_content not in similar_contents:
                            similar_contents[other_content] = 0
                        similar_contents[other_content] += similarity

        # for content in preferred_contents:
        #     contents_embedding = self.contents_embedding[content]
        #     for other_content, embedding in self.contents_embedding.items():
        #         if other_content not in preferred_contents:
        #             similarity = np.dot(contents_embedding, embedding) / (
        #                 np.linalg.norm(contents_embedding) * np.linalg.norm(embedding)
        #             )
        #             if other_content not in similar_contents:
        #                 similar_contents[other_content] = 0
        #             similar_contents[other_content] += similarity
        return similar_contents

    async def calculate_score(
        self, recommendations, filtered_content_ids, weight, combined_recommendations
    ):
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            self.executor,
            lambda: [
                score for content_id, score in recommendations if content_id in filtered_content_ids
            ],
        )
        std = np.std(scores)
        scores_normalized = [score / std for score in scores]

        for (content_id, _), score in zip(recommendations, scores_normalized):
            if content_id in filtered_content_ids:
                combined_recommendations[content_id] += weight * score
        return combined_recommendations

    async def get_recommendations(
        self, recommender_input, weight_mbti=0.4, weight_similar=0.5, weight_model=0.1, top_n=20
    ):
        new_user_embedding = self._get_user_embedding(recommender_input)
        popular_content_embeddings_dict = self._get_popular_content_embeddings_dict(
            recommender_input
        )

        mbti_recommendations_task = self.recommend_contents_by_mbti(
            new_user_embedding, popular_content_embeddings_dict
        )
        similar_contents_recommendations_task = self.recommend_similar_contents(
            recommender_input.get("input_media_title"), popular_content_embeddings_dict
        )

        mbti_recommendations, similar_contents_recommendations = await asyncio.gather(
            mbti_recommendations_task, similar_contents_recommendations_task
        )

        all_recommendations = self._get_all_recommendations(
            mbti_recommendations, similar_contents_recommendations
        )
        filtered_content_ids = self._filter_content_ids(recommender_input, all_recommendations)
        combined_recommendations = self._initialize_combined_recommendations(filtered_content_ids)

        combined_recommendations = await self.calculate_score(
            mbti_recommendations, filtered_content_ids, weight_mbti, combined_recommendations
        )
        combined_recommendations = await self.calculate_score(
            similar_contents_recommendations,
            filtered_content_ids,
            weight_similar,
            combined_recommendations,
        )
        combined_recommendations = self._update_with_model_scores(
            filtered_content_ids, combined_recommendations, weight_model
        )

        final_recommendations = self._filter_and_sort_recommendations(
            combined_recommendations, top_n
        )
        re_recommendation = bool(recommender_input.get("previous_recommendations", None))

        return final_recommendations, re_recommendation

    def _get_user_embedding(self, recommender_input):
        return self.user_embedding[recommender_input.get("user_mbti").upper()]

    def _get_popular_content_embeddings_dict(self, recommender_input):
        popularity_threshold = self.contents["Normalized Popularity Score"].quantile(0.9)
        popular_content = self.contents[
            self.contents["Normalized Popularity Score"] >= popularity_threshold
        ]

        popular_content_embeddings_dict = {
            title: self.contents_embedding[title]
            for title in popular_content["Title"].values
            if title in self.contents_embedding
        }
        for title in recommender_input.get("input_media_title"):
            if title in self.contents_embedding:
                popular_content_embeddings_dict[title] = self.contents_embedding[title]

        return popular_content_embeddings_dict

    def _get_all_recommendations(self, mbti_recommendations, similar_contents_recommendations):
        return set(
            [content_id for content_id, _ in mbti_recommendations]
            + [content_id for content_id, _ in similar_contents_recommendations]
        )

    def _filter_content_ids(self, recommender_input, all_recommendations):
        if recommender_input.get("previous_recommendations", None):
            return {
                content_id
                for content_id in all_recommendations
                if content_id not in recommender_input.get("previous_recommendations", None)
                and content_id not in recommender_input.get("input_media_title")
            }
        else:
            return {
                content_id
                for content_id in all_recommendations
                if content_id not in recommender_input.get("input_media_title")
            }

    def _initialize_combined_recommendations(self, filtered_content_ids):
        return {content_id: 0 for content_id in filtered_content_ids}

    def _update_with_model_scores(
        self, filtered_content_ids, combined_recommendations, weight_model
    ):
        content_indices = [
            self.contents.index[self.contents["Title"] == content_id][0]
            for content_id in filtered_content_ids
        ]

        if content_indices:
            content_features = self.cbf_model_input_scaled[content_indices]
            model_scores = self.best_gbm.predict(content_features).flatten()
            model_std = np.std(model_scores)
            model_scores_normalized = [score / model_std for score in model_scores]

            for content_id, model_score in zip(filtered_content_ids, model_scores_normalized):
                combined_recommendations[content_id] += weight_model * model_score

        return combined_recommendations

    def _filter_and_sort_recommendations(self, combined_recommendations, top_n):
        filtered_recommendations = {
            content: score
            for content, score in combined_recommendations.items()
            if self.contents.loc[self.contents["Title"] == content, "Rating Value"].values[0] >= 3.5
        }

        sorted_recommendations = sorted(
            filtered_recommendations.items(), key=lambda x: x[1], reverse=True
        )
        return [content for content, _ in sorted_recommendations[:top_n]]
