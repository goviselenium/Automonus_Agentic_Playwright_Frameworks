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
            "input": item.input,
            "expected_output": item.expected_output,
            "context": item.context,
            "evolution_type": item.evolution_type
        }
        for item in golden_items
    ]

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"[SYNTHESIZER] OK: Generated {len(output_data)} synthetic golden items saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
