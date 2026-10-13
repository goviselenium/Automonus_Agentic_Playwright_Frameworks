import traceback
from typing import Dict, Any, Optional
from playwright.async_api import Page, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from core.browser_manager import BrowserManager
from core.dom_extractor import DOMExtractor
from schema.page_state import PageStateSnapshot


class FailureInterceptor:
    """
    Hooks Playwright runtime exceptions and extracts failure context, 
    stack trace, active DOM mutation snapshot, and screenshots.
    """

    @staticmethod
    async def capture_failure_context(
        page: Page,
        browser_manager: BrowserManager,
        step_id: str,
        exception: Exception,
        failed_locator: str
    ) -> Dict[str, Any]:
        """
        Captures full diagnostic failure state.
        """
        error_type = type(exception).__name__
        error_message = str(exception).splitlines()[0] if str(exception) else "Unknown Playwright Error"
        stack_trace = "".join(traceback.format_tb(exception.__traceback__))

        screenshot_path = ""
        try:
            screenshot_path = await browser_manager.capture_screenshot(step_id)
        except Exception as e:
            print(f"[FailureInterceptor] Could not capture screenshot: {e}")

        page_state: Optional[PageStateSnapshot] = None
        try:
            page_state = await DOMExtractor.extract_page_state(page)
        except Exception as e:
            print(f"[FailureInterceptor] Could not extract page state on failure: {e}")

        return {
            "step_id": step_id,
            "failed_locator": failed_locator,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "screenshot_path": screenshot_path,
            "page_state": page_state
        }
