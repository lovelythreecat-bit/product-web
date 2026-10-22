"""Authenticated projection of the video service's current public input choices."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.agents.media_connection import read_media_connection
from app.agents.media_http import MediaClient, MediaServiceError
from app.common.types import DTO

Ratio = Literal["9:16", "16:9", "1:1", "4:5", "3:4", "4:3", "3:2", "2:3"]
Seconds = Annotated[int, Field(strict=True, ge=1, le=30)]


class VideoOptionsView(DTO):
    duration_tiers: list[Seconds] = Field(min_length=1, max_length=30)
    default_duration: Seconds
    aspect_ratios: list[Ratio] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def valid_choices(self):
        if (self.default_duration not in self.duration_tiers
                or len(set(self.duration_tiers)) != len(self.duration_tiers)
                or len(set(self.aspect_ratios)) != len(self.aspect_ratios)):
            raise ValueError("Invalid video capabilities")
        return self


def read_video_options(session, settings):
    connection = read_media_connection(session, settings, "video")
    payload = MediaClient(connection.base_url, connection.service_key, timeout=10).json(
        "GET", "/api/v1/capabilities"
    )
    try:
        return VideoOptionsView(**{key: payload[key] for key in (
            "duration_tiers", "default_duration", "aspect_ratios"
        )})
    except (KeyError, TypeError, ValueError):
        raise MediaServiceError(public_message="视频参数暂时无法读取，请稍后重试。") from None
