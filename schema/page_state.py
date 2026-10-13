from typing import Optional, List
from pydantic import BaseModel, Field


class InteractiveElement(BaseModel):
    """Extracted representation of an interactive or assertion element on the live DOM."""
    element_id: str = Field(description="Temporary ID assigned during extraction, e.g. elem_1")
    tag_name: str
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    placeholder: Optional[str] = None
    value: Optional[str] = None
    test_id: Optional[str] = None
    id_attr: Optional[str] = None
    class_attr: Optional[str] = None
    href: Optional[str] = None
    type_attr: Optional[str] = None
    aria_label: Optional[str] = None
    css_selector: str
    xpath_selector: str
    is_visible: bool = True
    is_enabled: bool = True

    def get_best_locator_hint(self) -> str:
        """Returns the most resilient Playwright locator expression candidate."""
        if self.test_id:
            return f"[data-testid='{self.test_id}']"
        if self.id_attr:
            return f"#{self.id_attr}"
        if self.role and self.name:
            return f"role={self.role}[name='{self.name}']"
        if self.placeholder:
            return f"[placeholder='{self.placeholder}']"
        if self.aria_label:
            return f"[aria-label='{self.aria_label}']"
        if self.text and len(self.text.strip()) > 0 and len(self.text.strip()) < 50:
            return f"text='{self.text.strip()}'"
        return self.css_selector


class PageStateSnapshot(BaseModel):
    """Compact summary of the page state for LLM context optimization."""
    url: str
    title: str
    aria_snapshot: str = Field(description="Playwright aria snapshot tree string")
    interactive_elements: List[InteractiveElement] = Field(default_factory=list)
    timestamp: float
