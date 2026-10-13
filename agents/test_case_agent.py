import html
import json
import os
import re
import subprocess
import tempfile
import xml.sax.saxutils as saxutils
from typing import List, Optional, Dict
from agents.base_agent import BaseAgent
from agents.azure_user_story_agent import AzureUserStoryAgent
from schema.azure_work_item import (
    ParsedUseCase,
    AzureTestCasePayload,
    CreatedWorkItem,
    AzureCreationSummary,
)

DEFAULT_PAT = ""


class TestCaseCreateAgent(BaseAgent):
    __test__ = False
    """
    Agent 6: TestCaseCreate Agent
    Parses Use Case Test Plans (specs/use-case-plan.md) and creates detailed Test Cases in
    Azure DevOps Boards with structured XML test steps according to CreateTestCases.md.
    Automatically links each Test Case to its corresponding User Story.
    """

    SYSTEM_PROMPT = """
    You are an expert QA Test Automation and Azure DevOps Test Management Agent.
    Your mission is to parse technical Use Case plans and create production-grade Azure DevOps
    Test Cases with:
    - Structured XML Test Steps in Microsoft.VSTS.TCM.Steps
    - Both ActionStep and ValidateStep types
    - Automated status assignment
    - Traceability links to User Stories
    - Markdown test case audit reporting
    """

    def __init__(
        self,
        organization: str = "govidev",
        project: str = "Frameworks",
        pat: Optional[str] = None
    ):
        super().__init__(role="TestCaseCreateAgent")
        self.organization = organization
        self.project = project
        self.pat = pat or os.getenv("AZURE_DEVOPS_PAT") or DEFAULT_PAT
        self.story_agent = AzureUserStoryAgent(organization=self.organization, project=self.project, pat=self.pat)

    # =========================================================================
    # TEST STEPS XML GENERATOR
    # =========================================================================

    def generate_steps_xml(self, uc: ParsedUseCase) -> str:
        """
        Builds the Azure DevOps Microsoft.VSTS.TCM.Steps XML payload conforming to CreateTestCases.md.
        - Steps starting with Verify/Assert/Check become 'ValidateStep'.
        - Standard execution steps become 'ActionStep'.
        - The final step verifies the primary expected outcome.
        """
        steps = uc.main_steps if uc.main_steps else ["Navigate to target application", "Verify application outcome"]
        last_id = len(steps) + 1  # 1-based indexing offset by 1 (starts at id 2)

        xml_lines = [f'<steps id="0" last="{last_id}">']

        for idx, step_text in enumerate(steps, 2):
            is_last = (idx == last_id)
            step_clean = saxutils.escape(step_text.strip())

            # Check if step is a validation step or final assertion
            is_validation = (
                is_last or 
                step_text.lower().startswith(("verify", "assert", "check", "ensure", "validate"))
            )

            if is_validation:
                if is_last and uc.expected_outcome:
                    expected_xml = saxutils.escape(uc.expected_outcome)
                else:
                    expected_xml = saxutils.escape(f"{step_text} passes and displays as expected.")

                xml_lines.append(
                    f'<step id="{idx}" type="ValidateStep">'
                    f'<parameterizedString isformatted="true">{step_clean}</parameterizedString>'
                    f'<parameterizedString isformatted="true">{expected_xml}</parameterizedString>'
                    f'</step>'
                )
            else:
                xml_lines.append(
                    f'<step id="{idx}" type="ActionStep">'
                    f'<parameterizedString isformatted="true">{step_clean}</parameterizedString>'
                    f'<description/>'
                    f'</step>'
                )

        xml_lines.append('</steps>')
        return "".join(xml_lines)

    # =========================================================================
    # USER STORY MAPPING & TRACEABILITY
    # =========================================================================

    def load_user_story_mappings(self, stories_report_path: str = "specs/azure-user-stories.md") -> Dict[str, int]:
        """Reads specs/azure-user-stories.md to extract existing User Story IDs for linking."""
        mappings: Dict[str, int] = {}
        if not os.path.exists(stories_report_path):
            return mappings

        with open(stories_report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Matches lines like: | **#7** | `UC-01` | [UC-01] ...
        matches = re.findall(r'\|\s*\*\*#(\d+)\*\*\s*\|\s*`(UC-\d+)`', content)
        for wid, ucid in matches:
            mappings[ucid] = int(wid)

        return mappings

    # =========================================================================
    # TEST CASE FORMATTING
    # =========================================================================

    def format_test_case(
        self,
        uc: ParsedUseCase,
        linked_story_id: Optional[int] = None
    ) -> AzureTestCasePayload:
        """Formats a ParsedUseCase into an AzureTestCasePayload conforming to CreateTestCases.md."""
        tc_num = uc.scenario_id.replace("UC-", "")
        tc_title = f"[TC-{tc_num}] {uc.title}"

        # Rich HTML Description
        desc_parts = [
            "<div>",
            f"<h3>Test Case Objective</h3>",
            f"<p>Verify that {html.escape(uc.actor)} can successfully complete <strong>{html.escape(uc.title)}</strong>.</p>",
            f"<h3>Preconditions</h3>",
            f"<p><code>{html.escape(uc.preconditions)}</code></p>"
        ]

        if uc.alt_flows:
            desc_parts.extend([
                "<h3>Alternate / Exception Handling</h3>",
                "<ul>"
            ])
            for alt in uc.alt_flows:
                desc_parts.append(f"  <li>{html.escape(alt)}</li>")
            desc_parts.append("</ul>")

        desc_parts.append("</div>")
        description_html = "\n".join(desc_parts)

        steps_xml = self.generate_steps_xml(uc)

        return AzureTestCasePayload(
            scenario_id=uc.scenario_id,
            title=tc_title,
            description_html=description_html,
            steps_xml=steps_xml,
            tags=f"Playwright; Automation; TestCase; {uc.scenario_id}",
            priority=1,
            linked_story_id=linked_story_id
        )

    # =========================================================================
    # AZURE DEVOPS REST API INTEGRATION
    # =========================================================================

    def create_test_case(self, payload: AzureTestCasePayload) -> CreatedWorkItem:
        """
        Creates a 'Test Case' work item in Azure DevOps with XML test steps via REST API.
        Optionally links to parent User Story if linked_story_id is provided.
        """
        url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/$Test%20Case?api-version=7.1"

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
                "path": "/fields/Microsoft.VSTS.Common.Priority",
                "value": payload.priority
            },
            {
                "op": "add",
                "path": "/fields/System.Tags",
                "value": payload.tags
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.Steps",
                "value": payload.steps_xml
            }
        ]

        # Link to parent User Story if provided
        if payload.linked_story_id:
            json_patch.append({
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                    "url": f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workItems/{payload.linked_story_id}",
                    "attributes": {
                        "comment": f"Linked to Parent User Story #{payload.linked_story_id}"
                    }
                }
            })

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
            state = data.get("fields", {}).get("System.State", "Design")

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
        stories_report_path: str = "specs/azure-user-stories.md",
        report_output: str = "specs/azure-test-cases.md"
    ) -> AzureCreationSummary:
        """
        Parses all scenarios from use-case-plan.md, associates each with existing User Stories,
        creates Test Cases in Azure DevOps with XML test steps, and outputs a Markdown summary.
        """
        scenarios = self.story_agent.parse_use_case_markdown(plan_path)
        story_mappings = self.load_user_story_mappings(stories_report_path)
        created_test_cases: List[CreatedWorkItem] = []

        print(f"\n[TEST CASE AGENT] Parsed {len(scenarios)} Use Cases from '{plan_path}'.")
        print(f"[TEST CASE AGENT] Loaded {len(story_mappings)} User Story traceability mappings from '{stories_report_path}'.")
        print(f"[TEST CASE AGENT] Publishing Test Cases to Azure DevOps ({self.organization}/{self.project})...\n")

        for idx, sc in enumerate(scenarios, 1):
            linked_story = story_mappings.get(sc.scenario_id)
            tc_payload = self.format_test_case(sc, linked_story_id=linked_story)
            item = self.create_test_case(tc_payload)
            created_test_cases.append(item)

            link_msg = f"(Linked to Story #{linked_story})" if linked_story else "(No story link)"
            print(f"  [{idx}/{len(scenarios)}] OK: Created Test Case #{item.id} - '{item.title}' {link_msg}")
            print(f"         Link: {item.web_url}")

        summary = AzureCreationSummary(
            organization=self.organization,
            project=self.project,
            total_parsed=len(scenarios),
            total_created=len(created_test_cases),
            work_items=created_test_cases,
            markdown_report_path=report_output
        )

        # Generate Markdown Summary Report
        if report_output:
            self._save_summary_markdown(summary, report_output, plan_path, story_mappings)
            print(f"\n[TEST CASE AGENT] Test Cases Report saved to: '{report_output}'")

        return summary

    def _save_summary_markdown(
        self,
        summary: AzureCreationSummary,
        output_path: str,
        plan_path: str,
        story_mappings: Dict[str, int]
    ) -> None:
        """Saves a Markdown summary linking all created Azure DevOps Test Cases."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        lines = [
            "# Azure DevOps Test Cases - Test Plan Implementation",
            f"**Azure DevOps Organization:** `{summary.organization}`  ",
            f"**Project:** `{summary.project}`  ",
            f"**Source Test Plan:** [`{plan_path}`](file:///{os.path.abspath(plan_path).replace(os.sep, '/')})  ",
            f"**Total Test Cases Created:** `{summary.total_created}`  ",
            "",
            "---",
            "",
            "| Test Case ID | Scenario | Title | Linked User Story | State | Azure DevOps Link |",
            "| :---: | :---: | :--- | :---: | :---: | :--- |"
        ]

        for item in summary.work_items:
            linked_id = story_mappings.get(item.scenario_id)
            story_str = f"[#{linked_id}](https://dev.azure.com/{summary.organization}/{summary.project}/_workitems/edit/{linked_id})" if linked_id else "None"
            lines.append(f"| **#{item.id}** | `{item.scenario_id}` | {item.title} | {story_str} | `{item.state}` | [View Test Case]({item.web_url}) |")

        lines.extend([
            "",
            "---",
            "*Generated autonomously by `TestCaseCreateAgent` conforming to `CreateTestCases.md`.*"
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


# Standalone CLI Entry Point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Azure DevOps Test Case Creator Agent")
    parser.add_argument("--plan", type=str, default="specs/use-case-plan.md", help="Path to use case plan markdown")
    parser.add_argument("--stories", type=str, default="specs/azure-user-stories.md", help="Path to user stories report")
    parser.add_argument("--org", type=str, default="govidev", help="Azure DevOps organization name")
    parser.add_argument("--project", type=str, default="Frameworks", help="Azure DevOps project name")
    parser.add_argument("--pat", type=str, default=None, help="Personal Access Token")
    parser.add_argument("--output", type=str, default="specs/azure-test-cases.md", help="Markdown summary output path")

    args = parser.parse_args()
    agent = TestCaseCreateAgent(organization=args.org, project=args.project, pat=args.pat)
    summary = agent.publish_all_from_plan(
        plan_path=args.plan,
        stories_report_path=args.stories,
        report_output=args.output
    )
    print(f"\nSuccessfully created {summary.total_created} Test Cases in Azure DevOps!")
