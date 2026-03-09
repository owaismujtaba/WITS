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
        self.download_dir = Path("output/download")
        self.current_page = 1
        self.dialog_handled = False
        self.setup_dirs()
        
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
        dialog.accept()
        self.dialog_handled = True
        return True

    def _get_visible_pages(self):
        try:
            grid_id = "MainContent_QueryViewControl1_grdvQueryList"
            # Wait for the pager to be present
            self.page.wait_for_selector(f'#{grid_id} tr.grid-footer', timeout=5000)
            
            pager_elements_info = self.page.evaluate(f"""
                (grid_id) => {{
                    let row = document.querySelector('tr.grid-footer');
                    if (!row) {{
                       const rows = Array.from(document.querySelectorAll('#' + grid_id + ' tr'));
                       row = rows.find(r => {{
                           const links = r.querySelectorAll('a');
                           return links.length >= 2 && (r.innerText.includes('...') || 
                                  Array.from(links).some(a => !isNaN(a.innerText.trim()) && a.innerText.trim() !== ''));
                       }});
                    }}
                    if (!row) return {{ pages: [], has_ellipsis: false }};
                    const links = Array.from(row.querySelectorAll('td span, td a'));
                    return {{
                        pages: links.map(l => l.innerText.trim()).filter(t => !isNaN(t) && t !== ''),
                        has_ellipsis: Array.from(row.querySelectorAll('a')).some(a => a.innerText.includes('...'))
                    }};
                }}
            """, grid_id)
            
            visible_pages = [int(p) for p in pager_elements_info.get('pages', [])]
            return visible_pages
        except Exception as e:
            self.logger.error(f"Error getting first window pages: {e}")
            return []

    def proceed_next_window(self):
        try:
            grid_id = "MainContent_QueryViewControl1_grdvQueryList"
            # Check current visible pages
            pager_elements_info = self.page.evaluate(f"""
                (grid_id) => {{
                    let row = document.querySelector('tr.grid-footer');
                    if (!row) {{
                        const rows = Array.from(document.querySelectorAll('#' + grid_id + ' tr'));
                        row = rows.find(r => {{
                            const links = r.querySelectorAll('a');
                            return links.length >= 2 && (r.innerText.includes('...') || 
                                    Array.from(links).some(a => !isNaN(a.innerText.trim()) && a.innerText.trim() !== ''));
                        }});
                    }}
                    if (!row) return {{ pages: [], has_ellipsis: false }};
                    const links = Array.from(row.querySelectorAll('td span, td a'));
                    return {{
                        pages: links.map(l => l.innerText.trim()).filter(t => !isNaN(t) && t !== ''),
                        has_ellipsis: Array.from(row.querySelectorAll('a')).some(a => !isNaN(a.innerText) || a.innerText.includes('...'))
                    }};
                }}
            """, grid_id)
            
            visible_pages = [int(p) for p in pager_elements_info.get('pages', [])]
            has_ellipsis = pager_elements_info.get('has_ellipsis', False)
            if not visible_pages:
                self.logger.warning("No visible pages found.")
                return []
                
            if has_ellipsis:
                idx = -1
                self.logger.info(f"Moving to the next window of pages...")
                self.page.evaluate("""
                    (index) => {
                        const row = document.querySelector('tr.grid-footer');
                        const ellipses = Array.from(row.querySelectorAll('a')).filter(a => a.innerText.includes('...'));
                        if (ellipses.length > 0) {
                            const target = index === -1 ? ellipses[ellipses.length - 1] : ellipses[0];
                            target.click();
                        }
                    }
                    """, idx)
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(1000)
        
            return visible_pages
        except Exception as e:
            self.logger.error(f"Error moving to next window: {e}")
            return []
                


    def _handle_pagination(self, current_page):
        try:
            self.logger.info(f"Navigating to page: {current_page}")
            if current_page == 1:
                self.logger.info("Already on page 1")
                return True
            
            # Determine how many windows to advance
            # Assuming windows are 1-10, 11-20, etc.
            # Page 2 -> 0 advances
            # Page 11 -> 1 advance (to see 11-20)
            # Page 10 -> 0 advances? Usually 1-10 are visible.
            
            # Use dynamic navigation: check if page is visible, if not click ...
            
            max_attempts = 20 # Safety break
            for _ in range(max_attempts):
                visible_pages = self._get_visible_pages()
                if not visible_pages:
                    self.logger.error("No visible pages found during pagination.")
                    return False
                
                self.logger.info(f"Visible pages: {visible_pages}")
                
                if current_page in visible_pages:
                    # Click the page
                    self.logger.info(f"Page {current_page} is visible. Clicking...")
                    grid_id = "MainContent_QueryViewControl1_grdvQueryList"
                    
                    # Find and click logic
                    clicked = self.page.evaluate(f"""
                        (targetPage) => {{
                            const row = document.querySelector('tr.grid-footer');
                            if (!row) return false;
                            const links = Array.from(row.querySelectorAll('a'));
                            const link = links.find(a => a.innerText.trim() === targetPage.toString());
                            if (link) {{
                                link.click();
                                return true;
                            }}
                            
                            // Check spans (current page is usually a span, not a link)
                            const spans = Array.from(row.querySelectorAll('span'));
                            const span = spans.find(s => s.innerText.trim() === targetPage.toString());
                            if (span) return true; // Already on page
                            
                            return false;
                        }}
                    """, current_page)
                    
                    if clicked:
                        self.page.wait_for_load_state('networkidle')
                        self.page.wait_for_timeout(1000)
                        self.logger.info(f"Successfully clicked page {current_page}")
                        return True
                    else:
                        # If evaluate returned True but didn't click (means it's a span, already active)
                        self.logger.info(f"Page {current_page} is already active.")
                        return True

                # If not visible, check if we need to go forward or backward
                # For download bot, we usually just go forward
                if current_page > max(visible_pages):
                    self.logger.info("Target page is ahead. Clicking '...'")
                    pages = self.proceed_next_window()
                    if not pages:
                        return False
                else:
                    self.logger.error(f"Target page {current_page} is smaller than visible pages {visible_pages}. logic error?")
                    return False
            
            return False

        except Exception as e:
            self.logger.error(f"Error handling pagination: {e}")
            return False
                    
    
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

    def _handle_download_popup(self, download_icon, target):
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
            
            # ---------------------------------------------------------
            # LOGIC CORRECTION PER USER:
            # 1. Alert occurs (No data OR Already processed) -> SKIP
            # 2. iFrame loads -> SUBMIT QUERY
            # ---------------------------------------------------------

            # Step 1: Wait briefly for an immediate alert
            self.page.wait_for_timeout(2000)

            if self.dialog_handled:
                self.dialog_handled = False
                self.logger.info("Alert detected immediately (No data / Already processed). SKIPPED.")
                return "SKIPPED"

            # Step 2: If no alert, look for the iFrame
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
                self.logger.error("Popup frame not found and no alert detected.")
                return "ERROR"
            
            self.logger.info("Found selection popup frame (Valid for submission).")
            found_frame.locator('#btnMoveAll').click()
            self.logger.info("Clicked 'Move All' (>>).")
            self.page.wait_for_timeout(1000)
            
            # Step 3: Submit Query 
            try:
                # Click the final button to submit
                found_frame.locator('#RptCoulmnSelection1_btnProcessed').click()
                self.logger.info("Clicked 'Download' (Send Query) button.")
                
                # Check for any post-submission alerts (just in case), but usually this is success
                self.page.wait_for_timeout(2000)
                
                if self.dialog_handled:
                    self.logger.info("Alert detected during query submission. Marking as Done.")
                    return "DOWNLOADED"
                
                self.logger.info("Query submitted successfully.")
                return "DOWNLOADED"

            except Exception as e:
                self.logger.error(f"Error submitting query: {e}")
                return "ERROR"
        except Exception as e:
            self.logger.error("Failed to handle download popup...")
            self.logger.error(str(e))
            return "ERROR"
    
    def write_skipped_targets(self, skipped_targets):
        with open("output/download/skipped_targets.txt", "a") as f:
            for target in skipped_targets:
                f.write(target['id'] + "\n")

    def write_failed_targets(self, failed_targets):
        with open("output/download/failed_targets.txt", "a") as f:
            for target in failed_targets:
                f.write(target['id'] + "\n")

    def write_done_targets(self, done_targets):
        with open("output/download/done_targets.txt", "a") as f:
            for target in done_targets:
                f.write(target['id'] + "\n")

    def write_done_pages(self, done_pages):
        with open("output/download/done_pages.txt", "a") as f:
            for page in done_pages:
                f.write(str(page) + "\n")

    def load_done_targets(self):
        try:
            with open("output/download/done_targets.txt", "r") as f:
                return [int(line.strip()) for line in f]
        except FileNotFoundError:
            return []

    def load_done_pages(self):
        try:
            with open("output/download/done_pages.txt", "r") as f:
                try:
                    return [int(line.strip()) for line in f][-1]
                except IndexError:
                    return 1
        except FileNotFoundError:
            return 1
    
    def load_skipped_targets(self):
        try:
            with open("output/download/skipped_targets.txt", "r") as f:
                return [int(line.strip()) for line in f if line.strip()]
        except FileNotFoundError:
            return []

    def load_failed_targets(self):
        try:
            with open("output/download/failed_targets.txt", "r") as f:
                return [int(line.strip()) for line in f]
        except FileNotFoundError:
            return []
            
    def _download_target(self, target):
        try:
            self.logger.info("Downloading target {}...".format(target))
            ensure_popup_closed(self.page, self.logger)
            setup_auto_close_popup(self.page, self.logger)

            grid_selector = '#MainContent_QueryViewControl1_grdvQueryList'
            # Use a more specific selector to find the exact row matching the ID
            # Assuming the ID is in the first <td>
            target_row = self.page.locator(f'{grid_selector} tr').filter(
                has=self.page.locator('td').first,
                has_text=target['id']
            ).first

            download_icon = target_row.locator('input[src*="Download"]')
            download_icon.wait_for(state="visible", timeout=10000)
            ensure_popup_closed(self.page, self.logger)
            setup_auto_close_popup(self.page, self.logger)  
        
            status = self._handle_download_popup(download_icon, target)
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
                self.current_page = self.load_done_pages()
                current_page = self.current_page
                done_ids = self.load_done_targets()
                skipped_ids = self.load_skipped_targets()
                failed_ids = self.load_failed_targets()
                
                # Combine skipped into done to avoid retry
                processed_ids = set(done_ids)
                processed_ids.update(skipped_ids)

                while True:
                    if self._handle_pagination(current_page):
                        self.logger.info("Navigated to page {}".format(current_page))
                    else:
                        self.logger.error("Failed to navigate to page {}".format(current_page))
                        # If failed to navigate and it's > 1, prevent infinite loop if stuck
                        break
                            
                    ensure_popup_closed(self.page, self.logger)
                    
                    all_targets = self._get_download_targets()
                    
                    # Filter targets by query_name in config
                    target_query_names = self.config.get('query_name', [])
                    if isinstance(target_query_names, str):
                        target_query_names = [target_query_names]
                    
                    filtered_targets = []
                    for t in all_targets:
                        # Check if target name matches any of our config query names
                        if any(qn.lower() in t['name'].lower() for qn in target_query_names):
                            filtered_targets.append(t)
                    
                    self.logger.info(f"Found {len(all_targets)} targets, filtered down to {len(filtered_targets)} based on config.")

                    # Filter out processed ids
                    not_downloaded_targets = [t for t in filtered_targets if int(t['id']) not in processed_ids]

                    while not_downloaded_targets:
                        target = not_downloaded_targets.pop(0)
                        self.logger.info("="*60)
                        status = self._download_target(target)
                        if status == "DOWNLOADED":
                            self.write_done_targets([target])
                            ensure_popup_closed(self.page, self.logger)
                            navigate_to_results(self.page, self.logger)
                            self._handle_pagination(current_page)
                            processed_ids.add(int(target['id']))
                            self.logger.info("Downloaded target {}".format(target))
                            
                            targets = self._get_download_targets()
                            not_downloaded_targets = [t for t in targets if int(t['id']) not in processed_ids]
                            ensure_popup_closed(self.page, self.logger)
                        
                        elif status == "SKIPPED":
                            self.logger.info("Skipped target {} (Data not available or alert)".format(target))
                            # Re-enabling navigation to ensure clean state after alert/popup issues
                            ensure_popup_closed(self.page, self.logger)
                            navigate_to_results(self.page, self.logger)
                            self._handle_pagination(current_page)
                            
                            processed_ids.add(int(target['id'])) # Add to local set
                            self.write_skipped_targets([target])
                        else:
                            self.logger.error("Failed to download target {}".format(target))
                            self.write_failed_targets([target])
                            continue
                            
                    self.current_page += 1
                    current_page = self.current_page # Fix: Update local variable to prevent infinite loop
                    self.write_done_pages([current_page])
            else:
                self.logger.error("Failed to navigate to results page.")
        else:
            self.logger.error("Login failed.")
            