from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CyberSentinel AI"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/cybersentinel",
        description="Async PostgreSQL connection URL",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4.1-mini"

    # Qdrant
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
    )
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant API key (optional for local)")
    QDRANT_COLLECTION: str = "cybersentinel_incidents"

    # Neo4j
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j password")

    # Clerk Auth
    CLERK_SECRET_KEY: str = Field(default="", description="Clerk secret key")
    CLERK_PUBLISHABLE_KEY: str = Field(default="", description="Clerk publishable key")
    CLERK_JWT_ISSUER: str = Field(
        default="https://clerk.your-app.com",
        description="Clerk JWT issuer URL",
    )

    # ML
    ML_MODEL_PATH: str = "models/threat_classifier.joblib"

    # OpenClaw — Jira integration
    JIRA_BASE_URL: str = Field(default="", description="Jira base URL e.g. https://yourcompany.atlassian.net")
    JIRA_EMAIL: str = Field(default="", description="Jira account email")
    JIRA_API_TOKEN: str = Field(default="", description="Jira API token from id.atlassian.com/manage-profile/security/api-tokens")
    JIRA_PROJECT_KEY: str = Field(default="CS", description="Default Jira project key for incident tickets")
    OPENCLAW_API_KEY: str = Field(default="", description="OpenClaw API key (optional — enables OpenClaw gateway)")
    OPENCLAW_WEBHOOK_URL: str = Field(default="", description="Slack-compatible webhook URL for incident notifications")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton instance — import this everywhere
settings = Settings()
