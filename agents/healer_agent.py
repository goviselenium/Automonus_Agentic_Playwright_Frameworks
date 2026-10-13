import re
import json
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from agents.base_agent import BaseAgent
from schema.page_state import PageStateSnapshot
from schema.test_plan import AtomicStep


class HealingDecision(BaseModel):
    """Output resolution emitted by Healer Agent when diagnosing and repairing a failed locator."""
    step_id: str
    failed_locator: str
    error_message: str
    dom_drift_analysis: str = Field(description="Diagnosis of what changed in the DOM (e.g. ID renamed, structure altered)")
    replacement_candidates: List[str] = Field(description="Ordered list of candidate replacement locators")
    best_healed_locator: str = Field(description="Top choice replacement locator")
    strategy_used: str = Field(description="Healing strategy (e.g. Attribute Fallback, Accessibility Text Search, Semantic Role Match)")
    confidence_score: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")

    @field_validator("step_id", "failed_locator", "error_message", "dom_drift_analysis", "best_healed_locator", "strategy_used", mode="before")
    @classmethod
    def coerce_string_field(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


class HealerAgent(BaseAgent):
    """
    Agent 3: Healer Agent
    Intercepts Playwright step failures, analyzes UI/DOM drift, generates alternative locators,
    and repairs broken test steps automatically.
    """

    SYSTEM_PROMPT = """
    You are an expert Autonomous Playwright Self-Healing Agent.
    A test step has failed due to a locator error (e.g. TimeoutError, ElementHandleNotFound, or ElementClickInterceptedError).

    Your task:
    1. Analyze the failed locator, exception error message, and live page state (Accessibility tree + interactive element inventory).
    2. Identify the root cause of the failure (e.g. UI drift, changed data-test or id attributes, restyled DOM hierarchy, or dynamic ID changes).
    3. Generate resilient replacement locator candidates that match the intended target element on the active page.
    4. Rank candidates by resilience (prefer test-id, role+name, standard IDs, text matching, then CSS/XPath).
    5. Emits the top choice healed locator along with a confidence score.
    """

    def __init__(self):
        super().__init__(role="HealerAgent")

    async def heal_failure(
        self,
        step: AtomicStep,
        failed_locator: str,
        error_message: str,
        page_state: PageStateSnapshot
    ) -> HealingDecision:
        """
        Diagnoses step failure and synthesizes candidate replacement locators.
        """
        elem_summary = []
        for elem in page_state.interactive_elements[:40]:
            elem_summary.append(
                f"- Tag:{elem.tag_name} Role:{elem.role} Name:'{elem.name}' Text:'{elem.text}' "
                f"TestId:'{elem.test_id}' ID:'{elem.id_attr}' CSS:'{elem.css_selector}'"
            )
        elements_str = "\n".join(elem_summary)

        user_prompt = f"""
        Failed Step Context:
        Step ID: {step.step_id}
        Description: {step.description}
        Target Description: {step.target_description}
        Failed Locator: {failed_locator}
        Error Message: {error_message}

        Current Live Page State:
        URL: {page_state.url}
        Title: {page_state.title}

        Aria Tree Snapshot:
        {page_state.aria_snapshot[:1000]}

        Current Interactive Elements:
        {elements_str}
        """

        return await self.generate_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=HealingDecision
        )

    async def _generate_mock(self, user_prompt: str, response_model: type) -> HealingDecision:
        """
        Rule-based heuristic healing engine fallback.
        Generates alternative candidate locators by analyzing element inventory and target description.
        """
        failed_loc = ""
        loc_match = re.search(r"Failed Locator:\s*([^\n]+)", user_prompt)
        if loc_match:
            failed_loc = loc_match.group(1).strip()

        step_id_match = re.search(r"Step ID:\s*([^\n]+)", user_prompt)
        step_id = step_id_match.group(1).strip() if step_id_match else "step_1"

        target_desc_match = re.search(r"Target Description:\s*([^\n]+)", user_prompt)
        target_desc = target_desc_match.group(1).strip().lower() if target_desc_match else ""

        err_match = re.search(r"Error Message:\s*([^\n]+)", user_prompt)
        error_msg = err_match.group(1).strip() if err_match else "TimeoutError: element not found"

        candidates = []

        if "autofill" in target_desc:
            candidates = ["[data-testid='login-autofill-demo']", "#autofillDemo", "button:has-text('Autofill')"]
        elif "add to cart" in target_desc or "add-to-cart" in target_desc:
            candidates = [".addToCart", "[data-testid^='add-to-cart']", "button:has-text('Add to Cart')", "#add-to-cart-button", "input[name='submit.add-to-cart']", "span#submit.add-to-cart input"]
        elif "username" in target_desc or "email" in target_desc or "user" in failed_loc.lower():
            candidates = ["[data-testid='checkout-email-input']", "[data-testid='login-email-input']", "#email", "input[name='email']", "input[type='email']", "#user-name", "[data-test='username']"]
        elif "phone" in target_desc or "mobile" in target_desc:
            candidates = ["[data-testid='checkout-phone-input']", "#phone", "input[type='number']"]
        elif "first name" in target_desc:
            candidates = ["[data-testid='checkout-firstname-input']", "#firstname"]
        elif "last name" in target_desc:
            candidates = ["[data-testid='checkout-lastname-input']", "#lastname"]
        elif "password" in target_desc or "pass" in failed_loc.lower():
            candidates = ["[data-testid='login-password-input']", "#password", "#ap_password", "input[name='password']", "input[type='password']", "[data-test='password']"]
        elif "checkout" in target_desc or "proceed" in target_desc:
            candidates = ["[data-testid='proceed-to-checkout-btn']", "#checkoutBtn", "input[name='proceedToRetailCheckout']", "a[href*='checkout.php']"]
        elif "place order" in target_desc:
            candidates = ["[data-testid='place-order-btn']", "a[href*='thanks.php']", "a:has-text('Place Order')"]
        elif "continue" in target_desc:
            candidates = ["[data-testid='continue-btn']", "#continue", "button:has-text('Continue')"]
        elif "submit" in target_desc or "login" in target_desc or "sign in" in target_desc:
            candidates = ["[data-testid='login-submit-btn']", "#loginBtn", "#signInSubmit", "#login-button", "[data-test='login-button']"]
        elif "cart" in target_desc or "backpack" in target_desc:
            candidates = ["[data-testid='header-cart-link']", "#cartdesk", "#nav-cart", ".shopping_cart_link", "a[href*='cart']"]
        else:
            candidates = ["button", "input", "a"]

        best = candidates[0] if candidates else "button"

        return HealingDecision(
            step_id=step_id,
            failed_locator=failed_loc,
            error_message=error_msg,
            dom_drift_analysis="Detected UI attribute/locator drift. Synthesized alternative element candidates.",
            replacement_candidates=candidates,
            best_healed_locator=best,
            strategy_used="Heuristic Semantic Candidate Generation",
            confidence_score=0.88
        )
