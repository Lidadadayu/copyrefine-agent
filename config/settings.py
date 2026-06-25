from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ContentPilot"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./contentpilot.db"

    # LLM 配置
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"

    # 默认使用 DashScope OpenAI-compatible 接口；不用 SDK，直接 requests 调用
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    llm_temperature: float = 0.3
    llm_timeout: int = 60

    # 是否启用 LLM 优化节点
    enable_llm_optimize: bool = False

    # Embedding / 向量检索配置
    # 生产建议：EMBEDDING_PROVIDER=dashscope，EMBEDDING_MODEL=text-embedding-v3
    embedding_provider: str = "hash"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    embedding_timeout: int = 60
    embedding_batch_size: int = 16
    hash_embedding_dimensions: int = 64

    # LangGraph 配置
    enable_langgraph: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()