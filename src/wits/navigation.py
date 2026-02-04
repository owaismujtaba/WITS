
from src.wits.handlers import ensure_popup_closed, setup_auto_close_popup

from src.wits.handlers import ensure_popup_closed, setup_auto_close_popup


def navigate_to_results(page, logger):
    """Navigates to the Results page."""
    setup_auto_close_popup(page, logger)
    page.wait_for_load_state('domcontentloaded')
    try:
        results_menu = page.locator('a.dropdown-toggle:has-text("Results")').first
        results_menu.hover(timeout=5000) 
        ensure_popup_closed(page, logger)
        trade_data_link = page.locator('#TopMenu1_DownloadandViewResults')
        trade_data_link.wait_for(state='visible', timeout=5000)
        trade_data_link.click()
        page.wait_for_load_state('networkidle')        
        return True
    except:
        return False


def navigate_to_advanced_query(page, logger):
    """Navigates to the Advanced Query page."""
    setup_auto_close_popup(page, logger)
    page.wait_for_load_state('domcontentloaded')
    try:
        advanced_query_menu = page.locator('a.dropdown-toggle:has-text("Advanced Query")').first
        advanced_query_menu.hover(timeout=5000) 
        ensure_popup_closed(page, logger)
        trade_data_link = page.locator('#TopMenu1_RawTradeData')
        trade_data_link.wait_for(state='visible', timeout=5000)
        trade_data_link.click()
        page.wait_for_load_state('networkidle')        
        return True
    except:
        return False

def select_existing_query(page, query_name, logger):
    """Selects an existing query from the dropdown and clicks Proceed."""
    ensure_popup_closed(page, logger)
    setup_auto_close_popup(page, logger)
    
    dropdown = page.locator('#MainContent_cboExistingQuery')
    dropdown.wait_for(state='visible', timeout=5000)
    dropdown.click()
    
    options = dropdown.locator('option').all()
    target_value = None
    for option in options:
        text = option.text_content().strip()
        if query_name in text:
            target_value = option.get_attribute('value')
            break
            
    if target_value:
        dropdown.select_option(value=target_value)
        # Dropdown change might trigger postback or loading
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500) # Give extra time for any UI updates
        
        ensure_popup_closed(page, logger)
        proceed_btn = page.locator('#MainContent_btnProceed')
        proceed_btn.wait_for(state='visible', timeout=5000)
        proceed_btn.click() 
        page.wait_for_load_state('networkidle')
        return True
    
    logger.warning(f"      [NAV] Query '{query_name}' not found in dropdown.")
    return False