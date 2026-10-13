import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrameworkSettings(BaseSettings):
    """
    Centralized configuration settings for the Autonomous Agentic Playwright Framework.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Browser Parameters
    BROWSER_TYPE: str = Field(default="chromium", description="chromium, firefox, or webkit")
    HEADLESS: bool = Field(default=True, description="Run browser in headless mode")
    SLOW_MO: float = Field(default=0.0, description="Slow motion delay in milliseconds")
    VIEWPORT_WIDTH: int = Field(default=1440, description="Viewport width")
    VIEWPORT_HEIGHT: int = Field(default=900, description="Viewport height")
    DEFAULT_TIMEOUT: float = Field(default=15000.0, description="Default action timeout in milliseconds")
    NAVIGATION_TIMEOUT: float = Field(default=30000.0, description="Default navigation timeout in milliseconds")

    # LLM Parameters
    LLM_PROVIDER: str = Field(default="auto", description="auto, openai, gemini, anthropic, ollama, or mock")
    LLM_MODEL: str = Field(default="llama3.2:latest", description="LLM model name")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    LLM_BASE_URL: Optional[str] = Field(default=None)
    LLM_TEMPERATURE: float = Field(default=0.1, description="Temperature for agent inference")

    # Framework Execution Parameters
    ARTIFACTS_DIR: str = Field(default="output/artifacts", description="Directory to store reports, traces, screenshots")
    REGISTRY_FILE: str = Field(default="locator.registry.json", description="Persistent locator registry path")
    ENABLE_SELF_HEAL: bool = Field(default=True, description="Enable automatic self-healing on step failure")
    MAX_HEAL_RETRIES: int = Field(default=2, description="Maximum healing attempts per step")
    ENABLE_TRACING: bool = Field(default=True, description="Record Playwright trace.zip")
    ENABLE_VIDEO: bool = Field(default=True, description="Record video for test execution")

    # Security & Masking
    MASK_SENSITIVE_DATA: bool = Field(default=True, description="Mask passwords/tokens in logs and reports")
    SENSITIVE_KEYS: List[str] = Field(
        default=["password", "pass", "secret", "token", "apiKey", "api_key", "credential", "auth"],
        description="Keys to automatically mask"
    )

    # Azure DevOps Integration
    AZURE_DEVOPS_ORG: str = Field(default="govidev", description="Azure DevOps organization")
    AZURE_DEVOPS_PROJECT: str = Field(default="Frameworks", description="Azure DevOps project")
    AZURE_DEVOPS_PAT: Optional[str] = Field(default=None, description="Azure DevOps Personal Access Token")

    def get_output_path(self, *subpaths: str) -> str:
        """Utility to get an absolute output subpath."""
        path = os.path.join(self.ARTIFACTS_DIR, *subpaths)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path


settings = FrameworkSettings()
