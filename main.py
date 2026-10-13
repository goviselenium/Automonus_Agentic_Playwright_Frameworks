import argparse
import asyncio
import os
import sys
from config.settings import settings
from engine.runner import AutonomousTestRunner


async def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Agentic Playwright Test Automation Framework"
    )
    parser.add_argument(
        "positional_args",
        nargs="*",
        help="Optional positional arguments: [requirement_path_or_url] [target_url]"
    )
    parser.add_argument(
        "-r", "--requirement",
        type=str,
        default="tests/sample_requirements/saucedemo_checkout.md",
        help="Path to requirement file (Markdown, text, Gherkin, JSON) or direct requirement text prompt"
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        default=None,
        help="Target base URL override"
    )
    parser.add_argument(
        "-b", "--browser",
        type=str,
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser type to use"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed visual mode"
    )
    parser.add_argument(
        "--no-heal",
        action="store_true",
        help="Disable automatic self-healing on failure"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="auto",
        choices=["auto", "openai", "gemini", "anthropic", "ollama", "mock"],
        help="LLM provider for agents"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt interactively at runtime for Target Base URL and requirement"
    )
    parser.add_argument(
        "--plan-output",
        type=str,
        default="specs/use-case-plan.md",
        help="Path to save the generated Use Case test plan markdown"
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate and save the Use Case test plan without executing browser tests"
    )
    parser.add_argument(
        "--standards",
        nargs="?",
        const=".",
        default=None,
        help="Run Coding Standards Agent to audit Python files against Coding_Standards_python.md"
    )
    parser.add_argument(
        "--standards-fix",
        action="store_true",
        help="Automatically fix formatting, tabs, blank lines, and imports with Coding Standards Agent"
    )

    args = parser.parse_args()

    # Handle Coding Standards Agent CLI invocation
    if args.standards is not None:
        from agents.standards_agent import CodingStandardsAgent
        standards_agent = CodingStandardsAgent()
        target_path = os.path.abspath(args.standards)
        
        if args.standards_fix:
            if os.path.isfile(target_path):
                res = standards_agent.fix_file(target_path)
                print(f"[STANDARDS] Fixed {target_path}: {len(res.applied_changes)} changes applied.")
            else:
                for root, _, files in os.walk(target_path):
                    if any(p in root for p in ["venv", ".git", "__pycache__"]):
                        continue
                    for f in files:
                        if f.endswith(".py"):
                            standards_agent.fix_file(os.path.join(root, f))
                print(f"[STANDARDS] Auto-fixed Python files in {target_path}.")

        if os.path.isfile(target_path):
            file_violations = standards_agent.audit_file(target_path)
            print(f"[STANDARDS] Audit complete for {target_path}: {len(file_violations)} violations found.")
            for v in file_violations:
                print(f"  * Line {v.line_number} [{v.violation_type.value}]: {v.message}")
        else:
            rep = standards_agent.audit_directory(target_path)
            print(f"\n[STANDARDS] Audit complete: Scanned {rep.total_files_scanned} files. Compliance: {rep.compliance_score_percent}% ({rep.total_violations} violations).")
            report_md_path = "output/artifacts/standards_report.md"
            os.makedirs(os.path.dirname(os.path.abspath(report_md_path)), exist_ok=True)
            with open(report_md_path, "w", encoding="utf-8") as f_out:
                f_out.write(standards_agent.generate_markdown_report(rep))
            print(f"[STANDARDS] Detailed Markdown Audit Report written to: {report_md_path}")
        sys.exit(0)

    # Override settings from CLI flags
    settings.BROWSER_TYPE = args.browser
    if args.headed:
        settings.HEADLESS = False
    if args.no_heal:
        settings.ENABLE_SELF_HEAL = False
    if args.provider:
        settings.LLM_PROVIDER = args.provider

    requirement_input = args.requirement
    target_url = args.url

    # Process positional arguments if supplied (e.g. python main.py https://amazon.co.in)
    if args.positional_args:
        pos_1 = args.positional_args[0].strip()
        is_url = pos_1.startswith("http://") or pos_1.startswith("https://") or "amazon" in pos_1.lower() or "saucedemo" in pos_1.lower()
        
        if is_url and not os.path.exists(pos_1):
            target_url = pos_1
            if not target_url.startswith("http"):
                target_url = f"https://{target_url}"
            if "amazon" in target_url.lower() and requirement_input == "tests/sample_requirements/saucedemo_checkout.md":
                requirement_input = "tests/sample_requirements/amazon_shopping.md"
        else:
            requirement_input = pos_1
            if len(args.positional_args) > 1:
                target_url = args.positional_args[1].strip()

    # Interactive runtime URL prompt if requested or in interactive TTY session without explicit URL
    if args.interactive or (not target_url and sys.stdin.isatty() and not args.positional_args):
        try:
            print("\n-----------------------------------------------------------")
            print("🤖 Autonomous Agentic Playwright Framework - Runtime Setup")
            print("-----------------------------------------------------------")
            input_url = input("🌐 Enter Target Base URL (leave blank to infer from requirement): ").strip()
            if input_url:
                target_url = input_url
        except (EOFError, KeyboardInterrupt):
            pass

    runner = AutonomousTestRunner()
    report = await runner.run(
        requirement_input=requirement_input,
        target_url=target_url,
        plan_output=args.plan_output,
        plan_only=args.plan_only
    )

    if report.overall_status.value == "FAILED":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
