import os
import time
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from config.settings import settings


class BrowserManager:
    """
    Manages Playwright browser lifecycle, isolated contexts, page sessions,
    tracing, video, and screenshot captures.
    """

    def __init__(self):
        os.environ["NODE_OPTIONS"] = "--max-old-space-size=4096"
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.trace_path: Optional[str] = None
        self.video_dir: Optional[str] = None

    async def start(
        self,
        browser_type: Optional[str] = None,
        headless: Optional[bool] = None,
        viewport: Optional[dict] = None
    ) -> Page:
        """
        Launches Playwright browser and returns an active page.
        """
        b_type = browser_type or settings.BROWSER_TYPE
        is_headless = settings.HEADLESS if headless is None else headless
        
        self.playwright = await async_playwright().start()

        if b_type.lower() == "firefox":
            launcher = self.playwright.firefox
        elif b_type.lower() == "webkit":
            launcher = self.playwright.webkit
        else:
            launcher = self.playwright.chromium

        self.browser = await launcher.launch(
            headless=is_headless,
            slow_mo=settings.SLOW_MO
        )

        vp = viewport or {"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT}
        
        self.video_dir = settings.get_output_path("videos") if settings.ENABLE_VIDEO else None

        context_kwargs = {
            "viewport": vp,
            "record_video_dir": self.video_dir
        }

        self.context = await self.browser.new_context(**context_kwargs)
        self.context.set_default_timeout(settings.DEFAULT_TIMEOUT)
        self.context.set_default_navigation_timeout(settings.NAVIGATION_TIMEOUT)

        if settings.ENABLE_TRACING:
            await self.context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True
            )

        self.page = await self.context.new_page()
        return self.page

    async def stop(self, save_trace: bool = True) -> dict:
        """
        Stops browser session and returns paths to collected trace and video.
        """
        artifacts = {"trace_path": None, "video_path": None}

        if self.context and settings.ENABLE_TRACING and save_trace:
            timestamp = int(time.time())
            trace_filename = f"trace_{timestamp}.zip"
            self.trace_path = settings.get_output_path("traces", trace_filename)
            await self.context.tracing.stop(path=self.trace_path)
            artifacts["trace_path"] = self.trace_path
        elif self.context and settings.ENABLE_TRACING:
            await self.context.tracing.stop()

        if self.page and self.video_dir:
            video = self.page.video
            if video:
                try:
                    artifacts["video_path"] = await video.path()
                except Exception:
                    pass

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        return artifacts

    async def capture_screenshot(self, step_id: str) -> str:
        """Captures a screenshot of the current page state."""
        if not self.page:
            return ""
        filename = f"screenshot_{step_id}_{int(time.time())}.png"
        filepath = settings.get_output_path("screenshots", filename)
        await self.page.screenshot(path=filepath, full_page=True)
        return filepath
