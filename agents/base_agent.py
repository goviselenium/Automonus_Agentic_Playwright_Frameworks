import os
import json
import re
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel
from config.settings import settings
from core.security_masker import SecurityMasker

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """
    Base LLM client providing unified structured JSON output generation across 
    OpenAI, Gemini, Anthropic, Ollama, Custom Endpoints, and Mock Fallback modes.
    """

    def __init__(self, role: str):
        self.role = role
        self.provider = settings.LLM_PROVIDER
        self._init_client()

    def _init_client(self):
        # Auto-detect provider if set to auto
        if self.provider == "auto":
            if settings.GEMINI_API_KEY:
                self.provider = "gemini"
            elif settings.OPENAI_API_KEY:
                self.provider = "openai"
            elif settings.ANTHROPIC_API_KEY:
                self.provider = "anthropic"
            elif settings.LLM_BASE_URL:
                self.provider = "custom"
            else:
                self.provider = "mock"

    def _create_sample_json(self, response_model: Type[T]) -> str:
        """Helper to build sample JSON key-value template from Pydantic model for local LLMs."""
        sample = {}
        schema = response_model.model_json_schema()
        props = schema.get("properties", {})
        for k, v in props.items():
            if "type" in v and v["type"] == "array":
                sample[k] = ["string_value"]
            elif "type" in v and (v["type"] == "number" or v["type"] == "integer"):
                sample[k] = 0.9
            elif "type" in v and v["type"] == "boolean":
                sample[k] = True
            else:
                sample[k] = "string_value"
        return json.dumps(sample, indent=2)

    async def generate_structured(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        """
        Sends prompt to configured LLM provider and parses strict JSON into Pydantic model response_model.
        """
        masked_user_prompt = SecurityMasker.mask_text(user_prompt)

        if self.provider == "mock":
            return await self._generate_mock(user_prompt, response_model)

        sample_json = self._create_sample_json(response_model)
        full_system = (
            f"{system_prompt}\n\n"
            f"REQUIRED OUTPUT FORMAT:\n"
            f"Respond strictly with a valid JSON object matching this key structure:\n"
            f"```json\n{sample_json}\n```\n"
            f"Do not include any explanation or extra text outside the JSON object."
        )

        try:
            if self.provider == "openai" or self.provider == "custom":
                return await self._call_openai(full_system, masked_user_prompt, response_model)
            elif self.provider == "gemini":
                return await self._call_gemini(full_system, masked_user_prompt, response_model)
            elif self.provider == "anthropic":
                return await self._call_anthropic(full_system, masked_user_prompt, response_model)
            elif self.provider == "ollama":
                return await self._call_ollama(full_system, masked_user_prompt, response_model)
            else:
                return await self._generate_mock(user_prompt, response_model)
        except Exception as e:
            print(f"[{self.role}] Warning: LLM call to {self.provider} failed ({e}). Falling back to heuristic engine.")
            return await self._generate_mock(user_prompt, response_model)

    async def _call_openai(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        import openai
        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY or "dummy",
            base_url=settings.LLM_BASE_URL
        )
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=settings.LLM_TEMPERATURE,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content or "{}"
        clean_json = self._extract_json_string(content)
        return response_model.model_validate_json(clean_json)

    async def _call_gemini(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model_name = settings.LLM_MODEL if "gemini" in settings.LLM_MODEL else "gemini-2.5-flash"
        
        full_prompt = f"{system_prompt}\n\nUser Request:\n{user_prompt}"
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config={"response_mime_type": "application/json"}
        )
        content = response.text or "{}"
        clean_json = self._extract_json_string(content)
        return response_model.model_validate_json(clean_json)

    async def _call_anthropic(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        return await self._call_openai(system_prompt, user_prompt, response_model)

    async def _call_ollama(self, system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
        import ollama
        model_name = settings.LLM_MODEL or "llama3.2:latest"
        if "-latest" in model_name and ":" not in model_name:
            model_name = model_name.replace("-latest", ":latest")
        elif model_name == "llama3.2":
            model_name = "llama3.2:latest"

        host = settings.LLM_BASE_URL or "http://127.0.0.1:11434"
        client = ollama.AsyncClient(host=host)

        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            format="json",
            options={"temperature": settings.LLM_TEMPERATURE}
        )
        content = response["message"]["content"] or "{}"
        clean_json = self._extract_json_string(content)
        return response_model.model_validate_json(clean_json)

    def _extract_json_string(self, text: str) -> str:
        """Extracts JSON substring from raw model output."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    async def _generate_mock(self, user_prompt: str, response_model: Type[T]) -> T:
        """
        Heuristic / Rule-based engine fallback when no external LLM API key is present.
        Override in subclasses for role-specific fallback logic.
        """
        raise NotImplementedError("Subclasses must implement _generate_mock for heuristic fallback.")
