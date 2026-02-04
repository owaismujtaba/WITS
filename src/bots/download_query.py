import os
from pathlib import Path
import random
from src.utils.browser import BrowserManager
from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.utils.login import Login

from src.wits.navigation import navigate_to_results 
from src.wits.navigation import ensure_popup_closed, setup_auto_close_popup


class DownloadQueryBot:
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger("DownloadQuery")
        self.browser_manager = BrowserManager(config)
        self.browser = None
        self.page = None
        self.setup_dirs()
        
    def load_done_info(self):
        file_path = self.download_dir / 'done_pages.txt'
        if not file_path.exists():
            self.current_page = 1
            return

        with open(file_path, 'r') as f:
            page_no = f.read().splitlines()
        if page_no:
            self.current_page = int(page_no[-1])
        else:
            self.current_page = 1

    def write_done_info(self):
        with open(self.download_dir / 'done_pages.txt', 'w') as f:
            f.write(str(self.current_page)) 
            
    def setup_dirs(self):
        self.logger.info("Setting up directories...")
        cur_dir = os.getcwd()
        output_dir = Path(cur_dir) / 'output' / 'download'
        output_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir = output_dir

    def start_browser(self):
        self.logger.info("Starting browser...")
        self.browser_manager = BrowserManager(self.config)
        self.page = self.browser_manager.start()
    
    def login(self):
        self.logger.info("Performing login...")
        login_manager = Login(self.page, self.config)
        if login_manager.perform_login():
            self.logger.info("Login successful.")
            return True

    def handle_dialog(self, dialog):
        self.logger.info(f"   [ALERT] Dialog Detected: {dialog.message} -> Clicking OK.")
        dialog.accept()
        self.dialog_handled = True
        return True

    def _handle_pagination(self, current_page):
        try:
            self.logger.info("Handling pagination...")
            if current_page > 1:
                self.logger.info("Navigating to page {}...".format(current_page))
                
        except Exception as e:
            self.logger.error("Failed to handle pagination...")
            self.logger.error(str(e))
            return False    
        return True
    
    def _get_download_targets(self):
        self.logger.info("Getting download targets...")
        ensure_popup_closed(self.page, self.logger)
        setup_auto_close_popup(self.page, self.logger)

        grid_selector = '#MainContent_QueryViewControl1_grdvQueryList'
        row_locator = self.page.locator(f'{grid_selector} tr[style*="background-color:White"]')
        
        row_count = row_locator.count()
        targets = []
        for i in range(row_count):
            row = row_locator.nth(i)
            cells = row.locator('td')
            q_id = cells.nth(0).inner_text().strip()
            q_name = cells.nth(1).inner_text().strip()
            targets.append({"id": q_id, "name": q_name})
        return targets


    def _handle_download_popup(self, download_icon):
        try:
            self.logger.info("Handling download popup...")
            ensure_popup_closed(self.page, self.logger)
            setup_auto_close_popup(self.page, self.logger)
            
            # Reset flag
            self.dialog_handled = False
            
            # Setup dialog handler for potential alerts
            self.page.on("dialog", self.handle_dialog)

            download_icon.click(force=True)
            self.logger.info("Clicked download icon.")
            
            # Wait briefly to allow dialog event to fire if it exists
            self.page.wait_for_timeout(2000)

            if self.dialog_handled:
                self.dialog_handled = False
                self.logger.info("Dialog was handled (likely 'Data not available'). Skipping download popup.")
                return "SKIPPED"

            self.page.wait_for_timeout(1000)

            found_frame = None
            for _ in range(5):
                for frame in self.page.frames:
                    try:
                        if frame.locator('#btnMoveAll').is_visible():
                            found_frame = frame
                            break
                    except:
                        pass
                if found_frame:
                    break
                self.page.wait_for_timeout(1000)
            
            if not found_frame:
                self.logger.error("Popup frame not found.")
                return "ERROR"
            
            self.logger.info("Found selection popup frame.")
            found_frame.locator('#btnMoveAll').click()
            self.logger.info("Clicked 'Move All' (>>).")
            self.page.wait_for_timeout(1000)
            found_frame.locator('#RptCoulmnSelection1_btnProcessed').click()
            self.logger.info("Clicked 'Download' button.")
            self.page.wait_for_timeout(1000)
            

        except Exception as e:
            self.logger.error("Failed to handle download popup...")
            self.logger.error(str(e))
            return "ERROR"
        return "DOWNLOADED"


    def _download_target(self, target):
        try:
            self.logger.info("Downloading target {}...".format(target))
            ensure_popup_closed(self.page, self.logger)
            setup_auto_close_popup(self.page, self.logger)

            grid_selector = '#MainContent_QueryViewControl1_grdvQueryList'
            target_row = self.page.locator(f'{grid_selector} tr').filter(has_text=target['id']).first

            download_icon = target_row.locator('input[src*="Download"]')
            download_icon.wait_for(state="visible", timeout=5000)
            ensure_popup_closed(self.page, self.logger)
            setup_auto_close_popup(self.page, self.logger)  
        
            status = self._handle_download_popup(download_icon)
            return status
            
        except Exception as e:
            self.logger.error("Failed to download target {}...".format(target))
            self.logger.error(str(e))
            return "ERROR"




    def execute(self):
        self.start_browser()
        if self.login():
            self.logger.info("\n" + "="*60)
            self.logger.info("   WITS AUTOMATION: STARTING EXECUTION")
            self.logger.info("="*60 + "\n")
            if navigate_to_results(self.page, self.logger):
                self.logger.info("Navigated to results page.")
                self.load_done_info()
                current_page = self.current_page
                while True:
                    if self._handle_pagination(current_page):
                        self.logger.info("Navigated to page {}".format(current_page))
                    else:
                        self.logger.error("Failed to navigate to page {}".format(current_page))
                        break
                    ensure_popup_closed(self.page, self.logger)
                    done_targets = []
                    failed_targets = []
                    download_targets = self._get_download_targets()
                    not_downloaded_targets = download_targets - done_targets
                    
                    for target in not_downloaded_targets:
                        status = self._download_target(target)
                        if status == "DOWNLOADED":
                            self._handle_pagination(current_page)
                            self.logger.info("Downloaded target {}".format(target))
                            targets = self._get_download_targets()  
                            not_downloaded_targets = targets-done_targets
                            done_targets.append(target)
                        elif status == "SKIPPED":
                            self.logger.info("Skipped target {} (Data not available)".format(target))
                            not_downloaded_targets = targets-done_targets
                            done_targets.append(target)
                        else:
                            self.logger.error("Failed to download target {}".format(target))
                            failed_targets.append(target)
                            continue

                    
                    self.current_page += 1
                    self.write_done_info()

                    break   
            else:
                self.logger.error("Failed to navigate to results page.")
        else:
            self.logger.error("Login failed.")
            