from typing import List, Optional

from model import Base
from pydantic import BaseModel
from sqlalchemy import CHAR, VARCHAR, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class RecommendORM(Base):
    __tablename__ = "recommendation"
    recommendation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    user_mbti: Mapped[str] = mapped_column(CHAR(4), nullable=False)
    input_media_id: Mapped[str] = mapped_column(VARCHAR(1000), nullable=False)
    recommended_media_id: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    re_recommendation: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation_time: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
