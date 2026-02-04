from playwright.sync_api import sync_playwright

class BrowserManager:
    def __init__(self, config):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = config.get('browser_settings', {}).get('headless', True)

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        return self.page

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()