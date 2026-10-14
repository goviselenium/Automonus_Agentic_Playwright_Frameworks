import os
import sys
import json
import asyncio
import argparse
from core.synthesizer import DocumentParser, LocalSynthesizer


async def main():
    parser = argparse.ArgumentParser(description="Synthetic Golden Dataset Generator for RAG Testing")
    parser.add_argument("-d", "--doc", type=str, default="tests/sample_requirements/amazon_20_requirements.md", help="Path to input unstructured document (.md, .txt, .pdf)")
    parser.add_argument("-o", "--output", type=str, default="test_rag_data.json", help="Path to output golden dataset JSON file")
    parser.add_argument("-m", "--max-items", type=int, default=10, help="Maximum number of synthetic items to generate")
    args = parser.parse_args()

    print(f"[SYNTHESIZER] Parsing document: {args.doc}")
    chunks = DocumentParser.parse_file(args.doc)
    print(f"[SYNTHESIZER] Extracted {len(chunks)} semantic chunks.")

    synthesizer = LocalSynthesizer()
    print(f"[SYNTHESIZER] Generating golden Q&A dataset via Dual-Model Architecture...")
    golden_items = await synthesizer.generate_dataset_from_chunks(chunks, max_items=args.max_items)

    output_data = [
        {
            "id": getattr(item, "id", f"synth_{idx+1}"),
            "input": item.input,
            "actual_output": getattr(item, "expected_output", ""),
            "expected_output": item.expected_output,
            "retrieval_context": item.context,
            "context": item.context,
            "evolution_type": item.evolution_type,
            "tags": ["synthetic", item.evolution_type]
        }
        for idx, item in enumerate(golden_items)
    ]

    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"[SYNTHESIZER] OK: Generated {len(output_data)} synthetic golden items saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
