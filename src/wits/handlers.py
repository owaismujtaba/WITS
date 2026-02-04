import logging



def handle_dialog(dialog, logger):
    logger.info(f"   [ALERT] Dialog Detected: {dialog.message} -> Clicking OK.")
    dialog.accept()

def ensure_popup_closed(page, logger):
    """
    Manually checks and closes the popup if visible. 
    Useful to call before critical actions.
    Checks main page and all frames.
    """
    try:
        # 1. Check Main Page
        no_thanks = page.get_by_role("button", name="No, thanks.")
        if no_thanks.is_visible():
            no_thanks.click()
            page.wait_for_timeout(100)
            return

        # 2. Check Frames (if popup might be inside one)
        for frame in page.frames:
            try:
                btn = frame.get_by_role("button", name="No, thanks.")
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(200)
                    return
            except: pass
    except Exception:
        pass

def setup_auto_close_popup(page, logger):
    """
    Registers a global handler that automatically clicks 'No, thanks.' 
    whenever the World Bank feedback modal appears.
    """
    no_thanks_locator = page.get_by_role("button", name="No, thanks.")
    
    try:
        page.add_locator_handler(no_thanks_locator, lambda: (
            no_thanks_locator.click()
        ))
    except Exception as e:
        logger.warning(f"   [POPUP] Warning: Auto-popup handler registration failed: {e}")
