from typing import Optional

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict()
    port: int = 8085
    mongo_uri: str = "mongodb://127.0.0.1:27017/"
    mongo_database: str = "ai-sdlc-agentic-ucd-backend"
    mongo_truststore: str = "TRUSTSTORE_CDP_ROOT_CA"
    http_proxy: Optional[HttpUrl] = None
    enable_metrics: bool = False
    tracing_header: str = "x-cdp-request-id"

    # S3 Configuration
    s3_bucket_name: str = "research-analysis-bucket"
    localstack_endpoint: Optional[str] = None  # Will be set via environment
    aws_region: str = "eu-west-2"
    aws_access_key_id: str = "test"  # noqa: S105
    aws_secret_access_key: str = "test"  # noqa: S105


config = AppConfig()
