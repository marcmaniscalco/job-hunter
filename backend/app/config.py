"""Application configuration.

We never hardcode connection strings. `Settings` reads values from environment
variables (and a local .env file when present). In Kubernetes those env vars come
from the ConfigMap/Secret; when running locally they come from your shell or .env.
This is the same pattern the pods will use, so local and cluster behave alike.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLAlchemy database URL. The `postgresql+psycopg://` prefix tells SQLAlchemy
    # to use the psycopg (v3) driver. Default points at a port-forwarded Postgres
    # for local dev; in the cluster we override it to point at the `postgres`
    # service DNS name.
    database_url: str = "postgresql+psycopg://jobhunter:devpassword@localhost:5432/jobhunter"

    # Loads a .env file if one exists; real env vars still win over it.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# A single shared settings instance imported across the app.
settings = Settings()
