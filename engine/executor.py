import time
from typing import Optional, Dict, Any
from playwright.async_api import Page, expect
from schema.test_plan import AtomicStep, StepIntent


class ActionExecutor:
    """
    Playwright Action Dispatcher handling dynamic execution, auto-waiting,
    assertions, and fallback locator resolution.
    """

    @staticmethod
    async def execute_step_action(
        page: Page,
        step: AtomicStep,
        locator_str: str,
        action_type: str,
        value: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches Playwright execution action for a single step.
        """
        start_time = time.time()
        action_desc = f"{action_type} on '{locator_str}'"
        if value:
            action_desc += f" with value '{value}'"

        # Handle navigation action
        if step.intent == StepIntent.ACTION_NAVIGATE or action_type == "navigate":
            target_url = value or step.value or "https://www.saucedemo.com"
            await page.goto(target_url, wait_until="domcontentloaded")
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "success": True,
                "action_taken": f"Navigated to {target_url}",
                "duration_ms": duration_ms
            }

        # Resolve locator against page (supporting comma-separated fallback list)
        locators_to_try = [loc.strip(" '\"`") for loc in locator_str.split(",") if loc.strip(" '\"`")]
        target_locator = None

        for loc_candidate in locators_to_try:
            try:
                locator_obj = page.locator(loc_candidate).first
                # Check if visible and count > 0
                if await locator_obj.count() > 0 and await locator_obj.is_visible():
                    target_locator = locator_obj
                    locator_str = loc_candidate
                    break
            except Exception:
                continue

        if target_locator is None:
            # Default to full locator string
            target_locator = page.locator(locators_to_try[0] if locators_to_try else locator_str).first

        # Dispatch action based on step intent or action_type
        if step.intent == StepIntent.ACTION_CLICK or action_type == "click":
            await target_locator.click(timeout=8000)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=2500)
            except Exception:
                pass

        elif step.intent == StepIntent.ACTION_TYPE or action_type == "fill":
            fill_val = value or step.value or ""
            await target_locator.fill(fill_val, timeout=8000)

        elif step.intent == StepIntent.ACTION_SELECT or action_type == "select":
            select_val = value or step.value or ""
            await target_locator.select_option(value=select_val, timeout=8000)

        elif step.intent == StepIntent.ACTION_HOVER or action_type == "hover":
            await target_locator.hover(timeout=8000)

        elif step.intent == StepIntent.ACTION_PRESS_KEY or action_type == "press":
            key_val = value or step.value or "Enter"
            await target_locator.press(key_val, timeout=8000)

        elif step.intent in [StepIntent.ASSERT_VISIBLE, StepIntent.ASSERT_TEXT_EQUALS, StepIntent.ASSERT_TEXT_CONTAINS] or "assert" in action_type:
            await expect(target_locator).to_be_visible(timeout=8000)
            if step.intent == StepIntent.ASSERT_TEXT_EQUALS and step.assertion_expected:
                await expect(target_locator).to_have_text(step.assertion_expected, timeout=8000)
            elif step.intent == StepIntent.ASSERT_TEXT_CONTAINS and step.assertion_expected:
                await expect(target_locator).to_contain_text(step.assertion_expected, timeout=8000)

        else:
            # Fallback action
            await target_locator.click(timeout=8000)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": True,
            "used_locator": locator_str,
            "action_taken": action_desc,
            "duration_ms": duration_ms
        }

    @staticmethod
    async def verify_locator_candidate(page: Page, locator_candidate: str, step: Optional[AtomicStep] = None) -> bool:
        """
        Verifies if a locator candidate exists and is actionable on the live page context.
        """
        cand_clean = locator_candidate.strip(" '\"`").lower() if locator_candidate else ""
        GENERIC_TAGS = {
            "body", "html", "head", "header", "footer", "input", "button", "a",
            "div", "span", "p", "label", "form", "section", "article", "img",
            "tr", "td", "li", "ul", "main", "nav", "aside", ""
        }
        
        is_interactive = False
        if step:
            intent_upper = str(step.intent).upper()
            if any(k in intent_upper for k in ["CLICK", "TYPE", "FILL", "SELECT", "PRESS"]):
                is_interactive = True
        else:
            is_interactive = True

        if cand_clean in GENERIC_TAGS and is_interactive:
            return False

        try:
            locators = [l.strip(" '\"`") for l in locator_candidate.split(",") if l.strip(" '\"`")]
            for loc in locators:
                loc_clean = loc.strip(" '\"`").lower()
                if loc_clean in GENERIC_TAGS and is_interactive:
                    continue
                loc_obj = page.locator(loc).first
                if await loc_obj.count() > 0 and await loc_obj.is_visible():
                    return True
            return False
        except Exception:
            return False
