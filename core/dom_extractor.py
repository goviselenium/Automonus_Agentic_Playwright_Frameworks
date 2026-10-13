import time
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from schema.page_state import InteractiveElement, PageStateSnapshot


class DOMExtractor:
    """
    Inspects live page state and distills it into compact accessibility trees 
    and interactive element inventories for context-efficient LLM consumption.
    """

    @staticmethod
    async def extract_page_state(page: Page) -> PageStateSnapshot:
        """
        Extracts page title, URL, aria tree representation, and visible interactive element inventory.
        """
        url = page.url
        title = await page.title()

        # Compact aria summary fallback
        aria_snapshot = f"Page Title: {title}\nURL: {url}"

        # Client-side DOM traversal script for visible interactive elements
        js_script = """
        () => {
            const isVisible = (elem) => {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                const rect = elem.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            };

            const getCssSelector = (el) => {
                if (el.id) return `#${el.id}`;
                if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
                if (el.getAttribute('data-test')) return `[data-test="${el.getAttribute('data-test')}"]`;
                if (el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name="${el.getAttribute('name')}"]`;
                
                let path = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.tagName.toLowerCase();
                    if (el.id) {
                        selector += `#${el.id}`;
                        path.unshift(selector);
                        break;
                    } else {
                        let sib = el, nth = 1;
                        while (sib = sib.previousElementSibling) {
                            if (sib.tagName.toLowerCase() == selector) nth++;
                        }
                        if (nth != 1) selector += `:nth-of-type(${nth})`;
                    }
                    path.unshift(selector);
                    el = el.parentNode;
                }
                return path.join(' > ');
            };

            const getXPath = (el) => {
                if (el.id) return `//*[@id="${el.id}"]`;
                if (el.getAttribute('data-testid')) return `//*[@data-testid="${el.getAttribute('data-testid')}"]`;
                
                let parts = [];
                for (; el && el.nodeType === Node.ELEMENT_NODE; el = el.parentNode) {
                    let id = el.id ? `[@id="${el.id}"]` : '';
                    let tag = el.tagName.toLowerCase();
                    let siblings = el.parentNode ? Array.from(el.parentNode.children).filter(child => child.tagName.toLowerCase() === tag) : [];
                    let index = siblings.length > 1 ? `[${siblings.indexOf(el) + 1}]` : '';
                    parts.unshift(`${tag}${id}${index}`);
                    if (el.id) break;
                }
                return parts.length ? '/' + parts.join('/') : '';
            };

            const selectors = [
                'button', 'a', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[role="textbox"]',
                '[role="combobox"]', '[role="checkbox"]', '[role="radio"]',
                '[role="tab"]', '[role="menuitem"]', '[data-testid]', '[data-test]',
                'h1', 'h2', 'h3', '.title', '.header', '.price', '.inventory_item_name'
            ];

            const elements = Array.from(document.querySelectorAll(selectors.join(',')));
            const items = [];
            let count = 0;

            for (const el of elements) {
                if (!isVisible(el)) continue;
                
                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || (tag === 'button' ? 'button' : (tag === 'input' ? 'input' : (tag === 'a' ? 'link' : null)));
                const text = (el.innerText || el.textContent || '').trim().substring(0, 100);
                const value = el.value || null;
                const placeholder = el.getAttribute('placeholder') || null;
                const ariaLabel = el.getAttribute('aria-label') || null;
                const testId = el.getAttribute('data-testid') || el.getAttribute('data-test') || el.getAttribute('id');
                const idAttr = el.id || null;
                const classAttr = el.className && typeof el.className === 'string' ? el.className.trim() : null;
                const href = el.getAttribute('href') || null;
                const typeAttr = el.getAttribute('type') || null;
                const name = el.getAttribute('name') || ariaLabel || (tag === 'input' && placeholder ? placeholder : text);

                items.push({
                    element_id: `elem_${count++}`,
                    tag_name: tag,
                    role: role,
                    name: name,
                    text: text,
                    placeholder: placeholder,
                    value: value,
                    test_id: testId,
                    id_attr: idAttr,
                    class_attr: classAttr,
                    href: href,
                    type_attr: typeAttr,
                    aria_label: ariaLabel,
                    css_selector: getCssSelector(el),
                    xpath_selector: getXPath(el),
                    is_visible: true,
                    is_enabled: !el.disabled
                });

                if (count >= 50) break; // Limit elements to keep context compact
            }
            return items;
        }
        """

        raw_elements: List[Dict[str, Any]] = []
        try:
            raw_elements = await page.evaluate(js_script)
        except Exception as e:
            print(f"[DOMExtractor] Warning: JS evaluation failed: {e}")

        interactive_elements = [InteractiveElement(**elem) for elem in raw_elements]

        # Build clean aria snapshot text representation from extracted elements
        aria_lines = [f"Page: {title} ({url})"]
        for elem in interactive_elements:
            aria_lines.append(f"  - {elem.role or elem.tag_name} '{elem.name or elem.text}' [id={elem.id_attr or elem.test_id}]")
        aria_snapshot = "\n".join(aria_lines)

        return PageStateSnapshot(
            url=url,
            title=title,
            aria_snapshot=aria_snapshot,
            interactive_elements=interactive_elements,
            timestamp=time.time()
        )
