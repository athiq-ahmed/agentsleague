"""
Azure OpenAI configuration loaded from environment / .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint:    str
    api_key:     str
    deployment:  str
    api_version: str

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)


def get_config() -> AzureOpenAIConfig:
    """Load Azure OpenAI settings from environment variables."""
    endpoint    = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key     = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment  = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    if not endpoint or not api_key:
        raise EnvironmentError(
            "Missing Azure OpenAI credentials.\n"
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your .env file.\n"
            "See .env.example for the required format."
        )

    return AzureOpenAIConfig(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
    )
