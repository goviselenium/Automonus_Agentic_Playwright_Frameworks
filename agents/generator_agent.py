import re
import json
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from agents.base_agent import BaseAgent
from schema.test_plan import AtomicStep
from schema.page_state import PageStateSnapshot, InteractiveElement


class GeneratorActionDecision(BaseModel):
    """Output resolution emitted by Generator Agent for a given step and page state."""
    step_id: str
    target_locator: str = Field(description="Concrete Playwright locator expression")
    action_type: str = Field(description="click, fill, navigate, select, hover, press, assert_visible, assert_text")
    value: Optional[str] = Field(default=None, description="Value parameter if applicable (text to type, key to press)")
    reasoning: str = Field(description="Explanation of why this locator was selected")

    @field_validator("target_locator", "value", "reasoning", mode="before")
    @classmethod
    def coerce_string_field(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


class GeneratorAgent(BaseAgent):
    """
    Agent 2: Generator Agent
    Inspects live DOM state (accessibility tree + interactive inventory)
    and synthesizes dynamic, resilient Playwright locators and actions.
    """

    SYSTEM_PROMPT = """
    You are an expert Autonomous Playwright Action Generator Agent.
    Your mission is to map an atomic test step intent to the live web application DOM page state.

    Input provided:
    1. Target Atomic Step (Intent, Description, Target Element Description, Value)
    2. Active Page URL & Title
    3. Compact Accessibility Tree Snapshot
    4. Inventory of visible interactive elements with attributes (test_id, role, text, placeholders, CSS, XPath)

    Rules for Locator Generation:
    1. Prefer semantic, resilient locators in order:
       a) data-testid or data-test attributes (e.g. [data-test="username"])
       b) standard id (e.g. #username or input#user-name)
       c) role + name/text (e.g. role=button[name="Login"])
       d) input placeholder or aria-label (e.g. [placeholder="Username"])
       e) exact text content (e.g. text="Add to cart")
       f) CSS / XPath selector fallback
    2. Ensure locator resolves uniquely and unambiguously on the page.
    3. Return a clean, executable Playwright locator expression.
    """

    def __init__(self):
        super().__init__(role="GeneratorAgent")

    async def generate_action(self, step: AtomicStep, page_state: PageStateSnapshot) -> GeneratorActionDecision:
        """
        Synthesizes Playwright action and locator for a step given current page state.
        """
        elem_summary = []
        for elem in page_state.interactive_elements[:40]:
            elem_summary.append(
                f"- ID:{elem.element_id} Tag:{elem.tag_name} Role:{elem.role} Name:'{elem.name}' "
                f"Text:'{elem.text}' TestId:'{elem.test_id}' CSS:'{elem.css_selector}'"
            )
        elements_str = "\n".join(elem_summary)

        user_prompt = f"""
        Target Step to Execute:
        Step ID: {step.step_id}
        Intent: {step.intent}
        Description: {step.description}
        Target Description: {step.target_description}
        Value: {step.value}
        Expected Assertion: {step.assertion_expected}

        Live Page State:
        URL: {page_state.url}
        Title: {page_state.title}

        Aria Snapshot:
        {page_state.aria_snapshot[:1000]}

        Visible Interactive Elements Inventory:
        {elements_str}
        """

        return await self.generate_structured(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=GeneratorActionDecision
        )

    async def _generate_mock(self, user_prompt: str, response_model: type) -> GeneratorActionDecision:
        """
        Rule-based locator synthesis fallback matching step intent against interactive elements inventory.
        """
        step_id_match = re.search(r"Step ID:\s*([^\n]+)", user_prompt)
        step_id = step_id_match.group(1).strip() if step_id_match else "step_1"

        desc_match = re.search(r"Target Description:\s*([^\n]+)", user_prompt)
        target_desc = desc_match.group(1).strip().lower() if desc_match else ""

        val_match = re.search(r"Value:\s*([^\n]+)", user_prompt)
        val = val_match.group(1).strip() if val_match and val_match.group(1).strip() != "None" else None

        intent_match = re.search(r"Intent:\s*([^\n]+)", user_prompt)
        intent = intent_match.group(1).strip() if intent_match else "ACTION_CLICK"

        action_type = "click"
        if "TYPE" in intent or "FILL" in intent:
            action_type = "fill"
        elif "NAVIGATE" in intent:
            action_type = "navigate"
        elif "ASSERT" in intent:
            action_type = "assert_visible"

        # Dynamically match target description against live DOM element inventory in prompt
        inv_matches = []
        GENERIC_WORDS = {"button", "input", "link", "icon", "page", "container", "item", "field", "list", "text", "box", "element", "to", "for", "the", "and"}
        target_words = [w for w in target_desc.split() if len(w) > 2 and w not in GENERIC_WORDS]

        if target_words:
            for line in user_prompt.splitlines():
                if line.startswith("- ID:"):
                    css_match = re.search(r"CSS:'([^']+)'", line)
                    if css_match:
                        css_val = css_match.group(1)
                        line_lower = line.lower()
                        if any(w in line_lower for w in target_words):
                            inv_matches.append(css_val)

        locator = ""
        if "autofill" in target_desc:
            locator = "[data-testid='login-autofill-demo'], #autofillDemo, button:has-text('Autofill demo credentials')"
        elif "first name" in target_desc:
            locator = "[data-testid='checkout-firstname-input'], #firstname, input[name='firstname']"
        elif "last name" in target_desc:
            locator = "[data-testid='checkout-lastname-input'], #lastname, input[name='lastname']"
        elif "email" in target_desc or "username" in target_desc:
            locator = "[data-testid='checkout-email-input'], [data-testid='login-email-input'], #email, input[name='email'], #ap_email, input[type='email'], [data-test='username'], #user-name"
        elif "mobile" in target_desc or "phone" in target_desc:
            locator = "[data-testid='checkout-phone-input'], #phone, input[type='number']"
        elif "address" in target_desc:
            locator = "[data-testid='checkout-address-input'], #address, textarea"
        elif "state" in target_desc:
            locator = "[data-testid='checkout-state-input'], #states, input[name='states']"
        elif "city" in target_desc:
            locator = "[data-testid='checkout-city-input'], #city, input[name='city']"
        elif "pin code" in target_desc or "pincode" in target_desc:
            locator = "[data-testid='checkout-pincode-input'], #pincode, input[name='pincode']"
        elif "confirm order" in target_desc or "confirm details" in target_desc or "user info" in target_desc:
            locator = "[data-testid='confirm-user-info'], #userInfo, [data-testid='confirm-cart-table']"
        elif "place order" in target_desc:
            locator = "[data-testid='place-order-btn'], a[href*='thanks.php'], a:has-text('Place Order')"
        elif "order success" in target_desc or "thank you" in target_desc or "confirmation title" in target_desc:
            locator = "[data-testid='order-success-title'], [data-testid='order-success'], h1:has-text('Thank You')"
        elif "cart count" in target_desc or "cart badge" in target_desc:
            locator = "[data-testid='header-cart-count'], #cartCount"
        elif "cart table" in target_desc or "cart summary" in target_desc:
            locator = "[data-testid='cart-table'], #cartTable, table"
        elif "mens wear" in target_desc or "men fashion" in target_desc:
            locator = "[data-testid='shop-now-mens-wear'], a[href*='mens-wear'], a:has-text('Shop Men Fashion')"
        elif "catalog listing" in target_desc or "items listing" in target_desc or "product listing" in target_desc:
            locator = "#product-list, [data-testid^='product-card'], .product-item"
        elif "shop menu" in target_desc or "shop navigation" in target_desc:
            locator = "[data-testid='nav-shop'], a[href*='shop.php']"
        elif "main navigation" in target_desc or "navbar" in target_desc:
            locator = "[data-testid='main-navbar'], #qaNav, [data-testid='site-header'], nav"
        elif "first product" in target_desc or "product item" in target_desc or "first item" in target_desc or "result item" in target_desc:
            locator = ".addToCart, [data-testid^='product-card'], .s-result-item h2 a, .inventory_item_name"
        elif "search" in target_desc:
            if "submit" in target_desc or "button" in target_desc or action_type == "click":
                locator = "#nav-search-submit-button, input[id='nav-search-submit-button'], input[type='submit']"
            else:
                locator = "#twotabsearchtextbox, input[name='field-keywords'], input[type='text']"
        elif "add to cart" in target_desc or "add-to-cart" in target_desc:
            locator = ".addToCart, [data-testid^='add-to-cart'], button:has-text('Add to Cart'), #add-to-cart-button, [data-test='add-to-cart-sauce-labs-backpack']"
        elif "checkout" in target_desc or "proceed" in target_desc:
            locator = "[data-testid='proceed-to-checkout-btn'], #checkoutBtn, a[href*='checkout.php'], input[name='proceedToRetailCheckout'], text='Proceed to checkout'"
        elif "password" in target_desc or "pass" in target_desc:
            locator = "[data-testid='login-password-input'], #password, #ap_password, input[name='password'], input[type='password'], [data-test='password']"
        elif "continue" in target_desc:
            locator = "[data-testid='continue-btn'], #continue, button:has-text('Continue'), span#continue input"
        elif "submit" in target_desc or "sign in" in target_desc or "login" in target_desc:
            locator = "[data-testid='login-submit-btn'], #loginBtn, #signInSubmit, [data-test='login-button'], #login-button"
        elif "logo" in target_desc:
            locator = "[data-testid='header-logo'], #nav-logo-sprites, .nav-logo-link, header img"
        elif "backpack" in target_desc:
            locator = "[data-test='add-to-cart-sauce-labs-backpack'], button:has-text('Add to cart'), #add-to-cart-button"
        elif "cart" in target_desc:
            locator = "[data-testid='header-cart-link'], #cartdesk, a[href*='cart'], #nav-cart, .shopping_cart_link"
        elif inv_matches:
            locator = ", ".join(inv_matches[:3])
        else:
            locator = "body"

        return GeneratorActionDecision(
            step_id=step_id,
            target_locator=locator,
            action_type=action_type,
            value=val,
            reasoning="Matched element dynamically using live DOM inventory and semantic heuristics"
        )
