import asyncio
import json
from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from curl_cffi import requests
from app.core.config import settings, logger

LOGIN_URL = "https://www.teamblind.com/sign-in"

_cookies: Optional[Dict[str, str]] = None

async def fetch_cookies() -> Dict[str, str]:
    global _cookies
    if _cookies is not None:
        logger.info("Reusing existing cookies.")
        return _cookies
    logger.info("Logging in to fetch new cookies.")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])

        context = await browser.new_context(
            user_agent=settings.User_Agent,
            locale="en-US",
            viewport={"width":1280, "height":800},
            timezone_id="Asia/Dhaka",
            extra_http_headers={
                "sec-ch-ua": '"Chromium";v="133", " Not A;Brand";v="99"',
                "sec-ch-ua-platform": '"Linux"'
            }
        )

        page = await context.new_page()
        # Stealth overrides:
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        await page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});")
        await page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
            Object.defineProperty(navigator, 'mimeTypes', {get: () => [1,2,3]});
        """)

        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await page.fill("input[name=email]", settings.TEAMBLIND_USER_EMAIL)
        await page.fill("input[name=password]", settings.TEAMBLIND_USER_PASS)
        await page.locator("button[type=submit]").click()

        await page.wait_for_url("https://www.teamblind.com/", timeout=60_000)

        # Persist state if you want to reuse later
        await context.storage_state(path="auth_state.json")

        # Extract cookies
        cookies = await context.cookies()
        _cookies = {c["name"]: c["value"] for c in cookies}
        logger.info("Fetched and stored new cookies.")

        # Clean up
        await context.close()
        await browser.close()

        return _cookies