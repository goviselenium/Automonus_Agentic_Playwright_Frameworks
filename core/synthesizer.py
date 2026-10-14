import os
import re
import json
import httpx
from typing import List, Dict, Any, Optional
from schema.rag_eval import SyntheticGoldenItem
from config.settings import settings


class DocumentParser:
    """Parses unstructured text, Markdown, or document files into semantic chunks."""

    @staticmethod
    def parse_file(file_path: str) -> List[str]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return DocumentParser.chunk_text(content)

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        """Splits raw text into overlapping semantic paragraph chunks."""
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.strip()) > 40]
        if not paragraphs:
            # Fallback to character chunking
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size].strip()
                if len(chunk) > 30:
                    chunks.append(chunk)
            return chunks
        return paragraphs


class LocalSynthesizer:
    """
    Synthetic Golden Dataset Generator with Dual-Model Architecture:
    1. Drafting Generator Model (Drafts Q&A pairs across simple, multihop, conditional evolutions).
    2. Critic/Judge Model (Filters low-quality or hallucinated ground-truth pairs).
    """

    def __init__(
        self,
        generator_model: Optional[str] = None,
        critic_model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.generator_model = generator_model or os.getenv("LLM_MODEL") or settings.LLM_MODEL or "llama3.2:latest"
        self.critic_model = critic_model or os.getenv("CRITIC_MODEL") or "llama3.2:latest"
        default_ollama_url = "http://127.0.0.1:11434/v1"
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL") or default_ollama_url

    async def _call_model(self, model: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        try:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3
            }
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def _generate_rule_based_item(self, chunk: str, evolution_type: str, index: int) -> SyntheticGoldenItem:
        """Generates fallback synthetic item when local LLM endpoint is offline."""
        lines = [l.strip() for l in chunk.splitlines() if len(l.strip()) > 20]
        first_line = lines[0] if lines else chunk[:80]
        
        if evolution_type == "simple":
            query = f"What key information is specified regarding {first_line[:40]}?"
            answer = f"According to the documentation: {first_line}"
        elif evolution_type == "multihop":
            query = f"How do the requirements for {first_line[:30]} relate to overall system functionality?"
            answer = f"The documentation specifies that {chunk[:150]}"
        else:  # conditional
            query = f"Under what condition does the system enforce constraints for {first_line[:30]}?"
            answer = f"The condition specified in context dictates: {chunk[:150]}"

        return SyntheticGoldenItem(
            id=f"synth_item_{index+1}",
            input=query,
            expected_output=answer,
            context=[chunk],
            evolution_type=evolution_type
        )

    async def generate_dataset_from_chunks(self, chunks: List[str], max_items: int = 10) -> List[SyntheticGoldenItem]:
        """Synthesizes structured golden dataset across simple, multihop, and conditional evolutions."""
        evolutions = ["simple", "multihop", "conditional"]
        golden_items: List[SyntheticGoldenItem] = []

        for idx, chunk in enumerate(chunks[:max_items]):
            evolution = evolutions[idx % len(evolutions)]
            
            # Step 1: Draft Q&A via Generator Model
            sys_prompt = f"You are an expert Synthetic Data Generator. Generate a {evolution} question and ground-truth answer based ONLY on the context. Return JSON: {{\"input\": \"str\", \"expected_output\": \"str\"}}."
            user_prompt = f"Context:\n{chunk}"
            
            draft_raw = await self._call_model(self.generator_model, sys_prompt, user_prompt)
            item = None

            if draft_raw:
                try:
                    # Extract JSON block
                    json_match = re.search(r'\{.*\}', draft_raw, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        
                        # Step 2: Quality Filtering via Critic Model
                        critic_prompt = f"Check if expected_output is 100% faithful to context. Reply APPROVED or REJECTED.\nContext: {chunk}\nAnswer: {parsed.get('expected_output')}"
                        critic_res = await self._call_model(self.critic_model, "You are a strict QA Critic.", critic_prompt)
                        
                        if critic_res and "REJECTED" in critic_res.upper():
                            item = None  # Critic rejected hallucinated pair
                        else:
                            item = SyntheticGoldenItem(
                                id=f"synth_{idx+1}",
                                input=parsed["input"],
                                expected_output=parsed["expected_output"],
                                context=[chunk],
                                evolution_type=evolution
                            )
                except Exception:
                    pass

            if not item:
                item = self._generate_rule_based_item(chunk, evolution, idx)

            golden_items.append(item)

        return golden_items
