import os
import time
from typing import Optional
from rich.console import Console
from rich.table import Table

from config.settings import settings
from schema.test_plan import TestPlan, AtomicStep, StepIntent
from schema.execution_result import (
    TestExecutionReport,
    StepExecutionResult,
    StepStatus,
    SelfHealingAuditEntry
)
from core.browser_manager import BrowserManager
from core.dom_extractor import DOMExtractor
from core.locator_registry import LocatorRegistry
from core.reporter import Reporter
from agents.planner_agent import PlannerAgent
from agents.generator_agent import GeneratorAgent
from agents.healer_agent import HealerAgent
from engine.executor import ActionExecutor
from engine.failure_interceptor import FailureInterceptor

# Use emoji=False and safe console settings for cross-platform Windows terminal encoding compatibility
console = Console(emoji=False, highlight=False)


class AutonomousTestRunner:
    """
    Main Orchestrator Pipeline:
    Requirement Ingestion -> Planning -> Live Page Generation -> Playwright Execution -> Self-Healing -> Persistence & Reporting
    """

    def __init__(self):
        self.planner = PlannerAgent()
        self.generator = GeneratorAgent()
        self.healer = HealerAgent()
        self.registry = LocatorRegistry()
        self.browser_manager = BrowserManager()

    async def run(
        self,
        requirement_input: str,
        target_url: Optional[str] = None,
        plan_output: str = "specs/use-case-plan.md",
        plan_only: bool = False
    ) -> TestExecutionReport:
        """
        Executes an end-to-end requirement input against target web application.
        """
        start_time_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        start_timestamp = time.time()

        # Step 1: Ingest requirement if given file path
        requirement_text = requirement_input
        req_path = requirement_input
        if not os.path.exists(req_path) and "use-case-plan.md" in req_path:
            alt = "specs/use-case-plan.md" if "tests" in req_path else "tests/specs/use-case-plan.md"
            if os.path.exists(alt):
                req_path = alt

        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8") as f:
                requirement_text = f.read()

        console.print("[bold cyan][PLANNER] Phase 1: Planning - Decomposing Requirements into Atomic Steps...[/bold cyan]")
        plan: TestPlan = await self.planner.plan_requirement(requirement_text, target_url=target_url)

        base_url = target_url or plan.target_url or "https://www.saucedemo.com"
        plan.target_url = base_url

        # Override first navigation step target URL if runtime target_url is provided
        if target_url and plan.all_steps() and plan.all_steps()[0].intent == StepIntent.ACTION_NAVIGATE:
            plan.all_steps()[0].value = target_url

        console.print(f"[bold green]OK: Planned {len(plan.all_steps())} Atomic Steps for scenario: '{plan.title}'[/bold green]")
        for s in plan.all_steps():
            console.print(f"  * [{s.step_id}] [yellow]{s.intent.value}[/yellow] - {s.description}")

        # Automatically export and save Use Case Test Plan markdown adhering to exact template
        if plan_output:
            saved_path = self.planner.save_use_case_plan(
                output_path=plan_output,
                plan=plan,
                requirement_text=requirement_text,
                base_url=base_url
            )
            console.print(f"[bold green]OK: Saved Use Case Test Plan to: '{saved_path}'[/bold green]")

        if plan_only:
            end_time_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            duration_total = round(time.time() - start_timestamp, 2)
            report = TestExecutionReport(
                test_id=plan.plan_id,
                title=plan.title,
                target_url=base_url,
                overall_status=StepStatus.PASSED,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_seconds=duration_total,
                total_steps=len(plan.all_steps()),
                passed_steps=len(plan.all_steps()),
                failed_steps=0,
                healed_steps=0,
                skipped_steps=0,
                step_results=[
                    StepExecutionResult(
                        step_id=s.step_id,
                        intent=s.intent.value,
                        description=s.description,
                        status=StepStatus.PASSED,
                        duration_ms=0.0
                    ) for s in plan.all_steps()
                ]
            )
            console.print(f"[bold green]OK: Planning completed in plan-only mode. Exiting without browser execution.[/bold green]")
            return report

        # Step 2: Start Browser Session
        console.print("[bold cyan][ENGINE] Phase 2: Launching Playwright Resilient Engine...[/bold cyan]")
        page = await self.browser_manager.start()

        step_results: list[StepExecutionResult] = []
        healing_audits: list[SelfHealingAuditEntry] = []

        total_steps = len(plan.all_steps())
        passed_count = 0
        failed_count = 0
        healed_count = 0
        skipped_count = 0

        overall_status = StepStatus.PASSED

        # Step 3: Execute Atomic Steps Graph
        for step in plan.all_steps():
            # Auto-switch to newly opened tab if target opened in new window/tab
            if page.context and len(page.context.pages) > 1:
                page = page.context.pages[-1]
                await page.bring_to_front()
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=4000)
                except Exception:
                    pass

            console.print(f"\n[bold blue]-> Executing [{step.step_id}]: {step.description}[/bold blue]")
            step_start = time.time()

            # Check Locator Registry for previously healed locator
            cached_healed_loc = self.registry.get_healed_locator(step.target_description)
            used_locator = cached_healed_loc

            # Extract page state
            page_state = await DOMExtractor.extract_page_state(page)

            action_type = "click"
            val = step.value

            if not used_locator:
                decision = await self.generator.generate_action(step, page_state)
                used_locator = decision.target_locator
                action_type = decision.action_type
                val = decision.value or step.value

            # Attempt Execution
            step_failed = False
            error_msg = None
            exec_details = {}

            try:
                exec_details = await ActionExecutor.execute_step_action(
                    page=page,
                    step=step,
                    locator_str=used_locator,
                    action_type=action_type,
                    value=val
                )
                
                # Auto-switch page context if click opened new tab
                if page.context and len(page.context.pages) > 1:
                    page = page.context.pages[-1]
                    await page.bring_to_front()
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except Exception:
                        pass
                console.print(f"  [green]OK: Passed[/green] ({exec_details.get('duration_ms', 0)} ms) using: [dim]{used_locator}[/dim]")
                status = StepStatus.HEALED if cached_healed_loc else StepStatus.PASSED
                if status == StepStatus.HEALED:
                    healed_count += 1
                else:
                    passed_count += 1

                step_results.append(StepExecutionResult(
                    step_id=step.step_id,
                    intent=step.intent.value,
                    description=step.description,
                    status=status,
                    used_locator=used_locator,
                    action_taken=exec_details.get("action_taken", ""),
                    duration_ms=exec_details.get("duration_ms", 0.0)
                ))

            except Exception as ex:
                step_failed = True
                error_msg = str(ex).splitlines()[0] if str(ex) else "Execution failed"
                console.print(f"  [bold red]X Step Execution Intercepted Error:[/bold red] {error_msg}")

            # Step 4: Self-Healing Pipeline if step failed
            if step_failed:
                healed_successfully = False
                if settings.ENABLE_SELF_HEAL:
                    console.print("  [bold yellow][HEALER] Intercepted Exception - Invoking Healer Agent...[/bold yellow]")
                    
                    # Failure diagnostic context capture
                    failure_ctx = await FailureInterceptor.capture_failure_context(
                        page=page,
                        browser_manager=self.browser_manager,
                        step_id=step.step_id,
                        exception=Exception(error_msg),
                        failed_locator=used_locator
                    )

                    refreshed_page_state = failure_ctx["page_state"] or page_state

                    heal_decision = await self.healer.heal_failure(
                        step=step,
                        failed_locator=used_locator,
                        error_message=error_msg,
                        page_state=refreshed_page_state
                    )

                    console.print(f"  [yellow]Healer Candidate Locators:[/yellow] {heal_decision.replacement_candidates}")

                    # Attempt verification and re-execution with candidate locators
                    for candidate in heal_decision.replacement_candidates:
                        console.print(f"  [dim]Testing candidate locator: '{candidate}'...[/dim]")
                        is_valid = await ActionExecutor.verify_locator_candidate(page, candidate, step)
                        if is_valid:
                            try:
                                retry_exec = await ActionExecutor.execute_step_action(
                                    page=page,
                                    step=step,
                                    locator_str=candidate,
                                    action_type=action_type,
                                    value=val
                                )
                                console.print(f"  [bold green]OK: Self-Healing SUCCESS! Step repaired with locator:[/bold green] '{candidate}'")
                                
                                # Register healed locator to persistent JSON storage
                                self.registry.register_heal(
                                    target_description=step.target_description,
                                    original_locator=used_locator,
                                    healed_locator=candidate,
                                    strategy=heal_decision.strategy_used,
                                    confidence=heal_decision.confidence_score,
                                    verified=True
                                )

                                audit_entry = SelfHealingAuditEntry(
                                    step_id=step.step_id,
                                    failed_locator=used_locator,
                                    error_message=error_msg,
                                    error_type=error_msg.split(":")[0] if ":" in error_msg else "ExecutionError",
                                    dom_diff_summary=heal_decision.dom_drift_analysis,
                                    healed_locator=candidate,
                                    strategy_used=heal_decision.strategy_used,
                                    confidence_score=heal_decision.confidence_score,
                                    verified=True,
                                    timestamp=time.time()
                                )
                                healing_audits.append(audit_entry)

                                healed_count += 1
                                step_results.append(StepExecutionResult(
                                    step_id=step.step_id,
                                    intent=step.intent.value,
                                    description=step.description,
                                    status=StepStatus.HEALED,
                                    used_locator=candidate,
                                    action_taken=f"Healed: {retry_exec.get('action_taken')}",
                                    duration_ms=retry_exec.get("duration_ms", 0.0),
                                    healing_audit=audit_entry
                                ))
                                healed_successfully = True
                                break
                            except Exception:
                                continue

                if not healed_successfully:
                    failed_count += 1
                    overall_status = StepStatus.FAILED
                    screenshot_path = await self.browser_manager.capture_screenshot(step.step_id)
                    step_results.append(StepExecutionResult(
                        step_id=step.step_id,
                        intent=step.intent.value,
                        description=step.description,
                        status=StepStatus.FAILED,
                        used_locator=used_locator,
                        error_message=error_msg,
                        screenshot_path=screenshot_path,
                        duration_ms=round((time.time() - step_start) * 1000, 2)
                    ))
                    console.print(f"  [bold red]X Step [{step.step_id}] Unrecoverable Failure.[/bold red]")

        # Step 5: Stop session and capture artifacts
        console.print("\n[bold cyan][REPORT] Phase 3: Finalizing Execution Artifacts & Reports...[/bold cyan]")
        artifacts = await self.browser_manager.stop(save_trace=settings.ENABLE_TRACING)

        end_time_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        duration_total = round(time.time() - start_timestamp, 2)

        report = TestExecutionReport(
            test_id=plan.plan_id,
            title=plan.title,
            target_url=base_url,
            overall_status=overall_status if failed_count == 0 else StepStatus.FAILED,
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_seconds=duration_total,
            total_steps=total_steps,
            passed_steps=passed_count,
            failed_steps=failed_count,
            healed_steps=healed_count,
            skipped_steps=skipped_count,
            trace_path=artifacts.get("trace_path"),
            video_path=artifacts.get("video_path"),
            step_results=step_results,
            healing_audits=healing_audits
        )

        html_report_path = Reporter.generate_html_report(report)
        console.print(f"[bold green]OK: HTML Execution Report saved to:[/bold green] {html_report_path}")
        console.print(f"[bold green]OK: Locator Registry updated at:[/bold green] {settings.REGISTRY_FILE}")

        # Display rich summary table in console
        self._print_terminal_summary(report)

        return report

    def _print_terminal_summary(self, report: TestExecutionReport) -> None:
        table = Table(title="Autonomous Framework Execution Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="dim", width=20)
        table.add_column("Value", justify="right")

        table.add_row("Scenario Title", report.title)
        table.add_row("Target URL", report.target_url)
        table.add_row("Overall Status", f"[bold green]{report.overall_status.value}[/bold green]" if report.overall_status == StepStatus.PASSED else f"[bold red]{report.overall_status.value}[/bold red]")
        table.add_row("Total Steps", str(report.total_steps))
        table.add_row("Passed", f"[green]{report.passed_steps}[/green]")
        table.add_row("Self-Healed", f"[yellow]{report.healed_steps}[/yellow]")
        table.add_row("Failed", f"[red]{report.failed_steps}[/red]")
        table.add_row("Duration", f"{report.duration_seconds} seconds")

        console.print(table)
