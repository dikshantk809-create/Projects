"""Edge node configuration via env / .env (pydantic-settings)."""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AICAM_", env_file=".env", extra="ignore")

    site_id: str = "site-001"
    camera_id: str = "cam-01"
    source: str = "0"  # 0 = local cam; or rtsp:// URL or file path

    # model / inference
    model_path: str = "yolo11n.pt"
    backend: Literal["torch", "onnx", "hailo", "tensorrt"] = "torch"
    device: str = "cpu"          # "cpu", "0" (cuda), "hailo"
    conf: float = 0.35
    iou: float = 0.5
    imgsz: int = 640
    tracker: Literal["bytetrack", "botsort"] = "bytetrack"

    # streaming to backend
    backend_url: str = "http://localhost:8000"
    ingest_token: str = "change-me"
    fps_limit: int = 15

    # storage
    evidence_dir: str = "./evidence"
    clip_pre_roll_s: int = 5
    clip_post_roll_s: int = 10


@lru_cache
def get_settings() -> EdgeSettings:
    return EdgeSettings()
