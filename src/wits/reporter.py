from src.wits.handlers import setup_auto_close_popup
from src.wits.handlers import ensure_popup_closed

def modify_reporter(page, query_name, logger, country_code, country_name):
    """
    Handles the modification of the Reporter tab to select a specific country.
    """
    logger.info(f"Modifying Reporter for country code: {country_code}")
    
    # Check for "Modify" link in the Reporter section
    modify_link = page.locator('#divRptrmodify a')
    
    ensure_popup_closed(page, logger) # Check before interacting
    
    try:
        # Wait for modify link to be visible (max 10s)
        # This handles cases where the page takes a moment to settle after potential popup closure
        modify_link.wait_for(state='visible', timeout=5000)
    except:
        logger.warning("Modify link wait timed out. proceeding to check visibility...")
        return False
    if modify_link.is_visible():
        logger.info("\n" + "="*50)
        logger.info(f"   MODIFYING REPORTER: {country_name} ({country_code})")
        logger.info("="*50)
        
        # Setup dialog handler for the 'Are you sure' alert WITS often throws
        def handle_dialog(dialog):
            logger.info(f"   [ALERT] {dialog.message} -> Clicking OK.")
            dialog.accept()
        
        page.on("dialog", handle_dialog)
        
        # Click the link
        logger.info("-> Clicking 'Modify' link...")
        modify_link.click()
        
        # Wait for the WITS RadWindow to appear
        page.wait_for_load_state('networkidle')
        #page.wait_for_timeout(500)
        
        ensure_popup_closed(page, logger) # Check after modal opens

        # Cleanup dialog handler
        page.remove_listener("dialog", handle_dialog)
        
        # ---------------------------------------------------------
        # MODAL HANDLING (Country List / New Query)
        # ---------------------------------------------------------
        modal_content = page.locator('.rwWindowContent')
        if modal_content.is_visible():
            title_node = page.locator('.rwTitleRow')
            title = title_node.text_content().strip() if title_node.count() > 0 else "Unknown Modal"
            
            if "Country List" in title:
                iframe = page.frame_locator('iframe[src*="CountryList.aspx"]')
                
                try:
                    iframe.locator('a.clearall, input[value="Clear All"]').click()
                except Exception as e:
                    return False
                page.wait_for_timeout(300)
                
                img_lookup = iframe.locator('img#Img1, img[title="Find Country"]')
                if img_lookup.count() > 0:
                    img_lookup.first.click()
                    page.wait_for_timeout(300)
                else:
                    return False
                
                iframe.locator('textarea#txtCntry').fill(country_code)
                iframe.locator('input#btnCntryCode').click()
                page.wait_for_timeout(1000) # Wait for add to process
                
                # --- VERIFICATION LOGIC ---
                expected_id = f"{country_name} -- {country_code}"
                
                verified = False
                try:
                    # 1. Exact ID Match (Primary)
                    selected_item = iframe.locator(f"li.list-item[id='{expected_id}']")
                    if selected_item.count() > 0 and selected_item.is_visible():
                         verified = True
                         logger.info(f"      [SUCCESS] Found Exact ID Match: '{expected_id}'")
                    
                    # 2. Fallback: Text Match (for special chars like 'Åland')
                    if not verified:
                         logger.info("      [INFO] strict ID match failed. Checking Name Text...")
                         # Try matching just the name part carefully
                         fallback_name = iframe.locator(f"li.list-item:has-text('{country_name}')")
                         if fallback_name.count() > 0 and fallback_name.first.is_visible():
                            verified = True
                            logger.info(f"      [SUCCESS] Found Name Text Match: '{country_name}'")
                            click_cancel(page, logger)
                    # 3. Fallback: ISO Code Match (Robust for encoding issues)
                    if not verified:
                         logger.info("      [INFO] Name match failed. Checking ISO Suffix...")
                         # Look for " -- ISO" pattern which is standard
                         iso_pattern = f" -- {country_code}"
                         fallback_iso = iframe.locator(f"li.list-item:has-text('{iso_pattern}')")
                         if fallback_iso.count() > 0 and fallback_iso.first.is_visible():
                            verified = True
                            logger.info(f"      [SUCCESS] Found ISO Suffix Match: '{iso_pattern}'")
                            click_cancel(page, logger)
                except Exception as e:
                    return False
                if not verified:
                    logger.error(f"      [FAILURE] Could not verify selection for '{country_name}' ({country_code}).")
                    
                    try:
                        click_cancel(page, logger)
                        return False
                    except Exception as e:
                        return False

                
                # --------------------------
                
                # --------------------------

                logger.info("-> Finalizing: Clicking 'Process' button...")
                proceed_btn = iframe.locator('input#CountryList1_btnProcess')
                if proceed_btn.count() > 0:
                    proceed_btn.click()
                    page.wait_for_load_state('networkidle')
                    logger.info("="*50 + "\n")
                    return True
                return False

            elif "New Query" in title:
                # Handle query naming modal if required
                logger.info("-> Handling 'New Query' Modal...")
                for frame in page.frames:
                    target_input = frame.locator('input[type="text"]:enabled:visible').first
                    if target_input.count() > 0:
                        target_input.fill(query_name)
                        save_btn = frame.locator('input[value="Save"], button:has-text("Save")').first
                        if save_btn.count() > 0:
                             save_btn.click()
                             break
                page.wait_for_load_state('networkidle')
        
        return True
    else:
        logger.error("Modify link not found or obscured.")
        try:
             page.screenshot(path='modify_link_error.png')
        except: pass
        return False


def click_final_submit(page, logger):
    """Clicks the final Submit button, handling potential Telerik overlays."""
    ensure_popup_closed(page, logger)
    
    # Force remove stuck Telerik overlays via JS to ensure the button is clickable.
    page.evaluate("""
        document.querySelectorAll('.TelerikModalOverlay').forEach(el => el.style.display = 'none');
    """)
    
    submit_btn = page.locator('#MainContent_btnSaveExecute')
    if submit_btn.is_visible():
        ensure_popup_closed(page, logger)
        submit_btn.click()
        page.wait_for_load_state('networkidle')
        return True
    return False

def click_cancel(page, logger):
    """Clicks the Back (Cancel) button, handling potential Telerik overlays."""
    ensure_popup_closed(page, logger)
    
    # Force remove stuck Telerik overlays via JS to ensure the button is clickable.
    page.evaluate("""
        document.querySelectorAll('.TelerikModalOverlay').forEach(el => el.style.display = 'none');
    """)
    
    # In the provided HTML, the ID is 'btnBack'
    cancel_btn = page.locator('#btnBack')
    
    if cancel_btn.is_visible():
        ensure_popup_closed(page, logger)
        logger.info("Clicking the Cancel (Back) button.")
        cancel_btn.click()
        
        