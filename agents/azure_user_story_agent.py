import html
import json
import os
import re
import subprocess
import tempfile
from typing import List, Optional
from agents.base_agent import BaseAgent
from schema.azure_work_item import (
    ParsedUseCase,
    AzureUserStoryPayload,
    CreatedWorkItem,
    AzureCreationSummary,
)

DEFAULT_PAT = ""


class AzureUserStoryAgent(BaseAgent):
    """
    Agent 5: Azure User Story Agent
    Parses Use Case Test Plans (e.g. specs/use-case-plan.md) and transforms every scenario
    into an Agile User Story, publishing them directly to Azure DevOps Boards via REST API.
    """

    SYSTEM_PROMPT = """
    You are an expert Agile Product Owner and Azure DevOps Integration Agent.
    Your mission is to parse technical Use Case test plans and transform every scenario into
    a professional, production-grade Agile User Story with:
    - User Story statement (As an... I want to... So that...)
    - Business Preconditions
    - Numbered Main Execution Flow
    - Alternate & Exception Paths
    - Clear Acceptance Criteria
    - Azure DevOps Work Item integration
    """

    def __init__(
        self,
        organization: str = "govidev",
        project: str = "Frameworks",
        pat: Optional[str] = None
    ):
        super().__init__(role="AzureUserStoryAgent")
        self.organization = organization
        self.project = project
        self.pat = pat or os.getenv("AZURE_DEVOPS_PAT") or DEFAULT_PAT

    # =========================================================================
    # PARSING ENGINE
    # =========================================================================

    def parse_use_case_markdown(self, markdown_input: str) -> List[ParsedUseCase]:
        """
        Parses specs/use-case-plan.md into structured ParsedUseCase models.
        Supports file path or direct markdown text content.
        """
        content = markdown_input
        if os.path.exists(markdown_input):
            with open(markdown_input, "r", encoding="utf-8") as f:
                content = f.read()

        scenarios: List[ParsedUseCase] = []
        # Split markdown by H2 scenario headers: "## UC-..." or "## [UC-..."
        raw_sections = re.split(r'\n(?=##\s+)', content)

        for sec in raw_sections:
            sec = sec.strip()
            if not sec.startswith("##"):
                continue

            lines = sec.splitlines()
            header_line = lines[0].lstrip("#").strip()

            # Extract Scenario ID and Title
            match_header = re.match(r'\[?(UC-\d+)\]?:?\s*(.*)', header_line)
            if match_header:
                scenario_id = match_header.group(1).strip()
                title = match_header.group(2).strip()
            else:
                scenario_id = f"UC-{len(scenarios) + 1:02d}"
                title = header_line

            actor = "Registered User"
            preconditions = ""
            main_steps: List[str] = []
            alt_flows: List[str] = []
            expected_outcome = ""

            current_mode = None
            for line in lines[1:]:
                line_stripped = line.strip()

                if line_stripped.startswith("- **Actor:**"):
                    actor = line_stripped.replace("- **Actor:**", "").strip()
                    current_mode = None
                elif line_stripped.startswith("- **Preconditions:**"):
                    preconditions = line_stripped.replace("- **Preconditions:**", "").strip()
                    current_mode = None
                elif line_stripped.startswith("- **Main Flow / Steps:**"):
                    current_mode = "steps"
                elif line_stripped.startswith("- **Alternate / Exception Flows:**"):
                    current_mode = "alt"
                elif line_stripped.startswith("- **Expected Outcome:**"):
                    expected_outcome = line_stripped.replace("- **Expected Outcome:**", "").strip()
                    current_mode = None
                elif current_mode == "steps" and re.match(r'^\d+\.\s+', line_stripped):
                    step_text = re.sub(r'^\d+\.\s+', '', line_stripped).strip()
                    main_steps.append(step_text)
                elif current_mode == "alt" and line_stripped.startswith("-"):
                    alt_text = line_stripped.lstrip("-").strip()
                    alt_flows.append(alt_text)

            scenarios.append(ParsedUseCase(
                scenario_id=scenario_id,
                title=title,
                actor=actor,
                preconditions=preconditions,
                main_steps=main_steps,
                alt_flows=alt_flows,
                expected_outcome=expected_outcome
            ))

        return scenarios

    # =========================================================================
    # USER STORY FORMATTING ENGINE
    # =========================================================================

    def format_user_story(self, uc: ParsedUseCase) -> AzureUserStoryPayload:
        """Transforms a ParsedUseCase into an Agile Azure User Story payload."""
        # Derive capability summary
        capability = uc.title.lower()
        if capability.startswith("demo ") or capability.startswith("header "):
            capability_text = f"interact with {capability}"
        else:
            capability_text = f"execute {capability}"

        story_title = f"[{uc.scenario_id}] {uc.title}"

        # Build Rich HTML Description for Azure DevOps Boards
        desc_parts = [
            "<div>",
            "<h3>User Story Statement</h3>",
            f"<p><strong>As an</strong> {html.escape(uc.actor)},<br/>",
            f"<strong>I want to</strong> {html.escape(capability_text)},<br/>",
            f"<strong>So that</strong> {html.escape(uc.expected_outcome)}.</p>",
            "",
            "<h3>Preconditions</h3>",
            f"<p><code>{html.escape(uc.preconditions)}</code></p>",
            "",
            "<h3>Main Execution Flow</h3>",
            "<ol>"
        ]
        for step in uc.main_steps:
            desc_parts.append(f"  <li>{html.escape(step)}</li>")
        desc_parts.append("</ol>")

        if uc.alt_flows:
            desc_parts.extend([
                "",
                "<h3>Alternate & Exception Flows</h3>",
                "<ul>"
            ])
            for alt in uc.alt_flows:
                desc_parts.append(f"  <li>{html.escape(alt)}</li>")
            desc_parts.append("</ul>")

        desc_parts.append("</div>")
        description_html = "\n".join(desc_parts)

        # Build Acceptance Criteria HTML
        ac_parts = [
            "<div>",
            "<h4>Acceptance Criteria & Verification</h4>",
            "<ul>",
            f"  <li><strong>Primary Expected Outcome:</strong> {html.escape(uc.expected_outcome)}</li>",
            f"  <li><strong>Atomic Steps Execution:</strong> All {len(uc.main_steps)} step assertions must pass without unhandled errors.</li>"
        ]
        if uc.alt_flows:
            ac_parts.append("  <li><strong>Exception Resilience:</strong> System must gracefully handle alternate flows and provide clear user feedback.</li>")
        ac_parts.extend([
            "  <li><strong>Automation Coverage:</strong> Covered by Autonomous Playwright Test Automation graph.</li>",
            "</ul>",
            "</div>"
        ])
        acceptance_criteria_html = "\n".join(ac_parts)

        # Estimate Story Points based on complexity
        story_points = 3 if len(uc.main_steps) <= 5 else 5

        return AzureUserStoryPayload(
            scenario_id=uc.scenario_id,
            title=story_title,
            description_html=description_html,
            acceptance_criteria_html=acceptance_criteria_html,
            tags=f"Playwright; Automation; E2E; Use-Case; {uc.scenario_id}",
            priority=2,
            story_points=story_points
        )

    # =========================================================================
    # AZURE DEVOPS REST API INTEGRATION
    # =========================================================================

    def create_work_item(self, payload: AzureUserStoryPayload) -> CreatedWorkItem:
        """
        Creates a 'User Story' work item in Azure DevOps via REST API.
        Uses temporary payload file to safely handle multi-line HTML on Windows.
        """
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$User%20Story?api-version=7.1"

        json_patch = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": payload.title
            },
            {
                "op": "add",
                "path": "/fields/System.Description",
                "value": payload.description_html
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                "value": payload.acceptance_criteria_html
            },
            {
                "op": "add",
                "path": "/fields/System.Tags",
                "value": payload.tags
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.Priority",
                "value": payload.priority
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints",
                "value": payload.story_points
            }
        ]

        # Use temporary file to pass JSON patch safely to curl without escaping issues
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as temp_f:
            json.dump(json_patch, temp_f, ensure_ascii=False)
            temp_path = temp_f.name

        try:
            cmd = [
                "curl.exe", "-s", "-X", "POST", url,
                "-H", "Content-Type: application/json-patch+json",
                "-u", f":{self.pat}",
                "-d", f"@{temp_path}"
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

            if proc.returncode != 0:
                raise RuntimeError(f"curl command failed: {proc.stderr}")

            data = json.loads(proc.stdout)
            if "id" not in data:
                raise RuntimeError(f"Azure DevOps API returned error: {proc.stdout[:300]}")

            work_item_id = data["id"]
            web_url = data.get("_links", {}).get("html", {}).get("href") or f"https://dev.azure.com/{self.organization}/{self.project}/_workitems/edit/{work_item_id}"
            state = data.get("fields", {}).get("System.State", "New")

            return CreatedWorkItem(
                id=work_item_id,
                title=payload.title,
                scenario_id=payload.scenario_id,
                state=state,
                web_url=web_url,
                api_url=data.get("url"),
                created_at=data.get("fields", {}).get("System.CreatedDate")
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def publish_all_from_plan(
        self,
        plan_path: str = "specs/use-case-plan.md",
        report_output: str = "specs/azure-user-stories.md"
    ) -> AzureCreationSummary:
        """
        Parses all scenarios from use-case-plan.md and creates User Stories for each
        in Azure DevOps, outputting a complete Markdown reference report.
        """
        scenarios = self.parse_use_case_markdown(plan_path)
        created_items: List[CreatedWorkItem] = []

        print(f"\n[AZURE AGENT] Parsed {len(scenarios)} Use Cases from '{plan_path}'.")
        print(f"[AZURE AGENT] Publishing to Azure DevOps Organization: '{self.organization}', Project: '{self.project}'...\n")

        for idx, sc in enumerate(scenarios, 1):
            story_payload = self.format_user_story(sc)
            item = self.create_work_item(story_payload)
            created_items.append(item)
            print(f"  [{idx}/{len(scenarios)}] OK: Created Work Item #{item.id} - '{item.title}'")
            print(f"         Link: {item.web_url}")

        summary = AzureCreationSummary(
            organization=self.organization,
            project=self.project,
            total_parsed=len(scenarios),
            total_created=len(created_items),
            work_items=created_items,
            markdown_report_path=report_output
        )

        # Generate Markdown Summary Report
        if report_output:
            self._save_summary_markdown(summary, report_output, plan_path)
            print(f"\n[AZURE AGENT] User Stories Report saved to: '{report_output}'")

        return summary

    def _save_summary_markdown(self, summary: AzureCreationSummary, output_path: str, plan_path: str) -> None:
        """Saves a Markdown summary linking all created Azure DevOps Work Items."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        lines = [
            "# Azure DevOps User Stories - Test Plan Implementation",
            f"**Azure DevOps Organization:** `{summary.organization}`  ",
            f"**Project:** `{summary.project}`  ",
            f"**Source Test Plan:** [`{plan_path}`](file:///{os.path.abspath(plan_path).replace(os.sep, '/')})  ",
            f"**Total User Stories Created:** `{summary.total_created}`  ",
            "",
            "---",
            "",
            "| ID | Scenario | User Story Title | State | Azure DevOps Board Link |",
            "| :---: | :---: | :--- | :---: | :--- |"
        ]

        for item in summary.work_items:
            lines.append(f"| **#{item.id}** | `{item.scenario_id}` | {item.title} | `{item.state}` | [View in Azure DevOps]({item.web_url}) |")

        lines.extend([
            "",
            "---",
            "*Generated autonomously by `AzureUserStoryAgent`.*"
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


# Standalone CLI Entry Point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Azure DevOps User Story Creator Agent")
    parser.add_argument("--plan", type=str, default="specs/use-case-plan.md", help="Path to use case plan markdown")
    parser.add_argument("--org", type=str, default="govidev", help="Azure DevOps organization name")
    parser.add_argument("--project", type=str, default="Frameworks", help="Azure DevOps project name")
    parser.add_argument("--pat", type=str, default=None, help="Personal Access Token")
    parser.add_argument("--output", type=str, default="specs/azure-user-stories.md", help="Markdown summary output path")

    args = parser.parse_args()
    agent = AzureUserStoryAgent(organization=args.org, project=args.project, pat=args.pat)
    summary = agent.publish_all_from_plan(plan_path=args.plan, report_output=args.output)
    print(f"\nSuccessfully created {summary.total_created} User Stories in Azure DevOps!")
