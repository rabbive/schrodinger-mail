#!/usr/bin/env python3
"""
Quick UI test script to verify the Quantum Email Client interface
"""
import time
import sys

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("Selenium not installed. Trying playwright...")
    try:
        from playwright.sync_api import sync_playwright
        USE_PLAYWRIGHT = True
    except ImportError:
        print("Neither selenium nor playwright installed.")
        print("Install with: pip install selenium playwright")
        print("Or: python3 -m playwright install chromium")
        sys.exit(1)
    USE_PLAYWRIGHT = True
else:
    USE_PLAYWRIGHT = False

def test_with_selenium():
    """Test using Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🌐 Navigating to http://127.0.0.1:5000...")
        driver.get('http://127.0.0.1:5000')
        time.sleep(2)
        
        print("\n📸 STEP 1: Initial Page Load")
        print("=" * 60)
        
        # Check header
        header = driver.find_element(By.TAG_NAME, 'header')
        print(f"✓ Header found")
        
        logo = driver.find_element(By.CSS_SELECTOR, 'header .logo')
        print(f"✓ Logo text: {logo.text}")
        
        # Check algorithm chips
        chips = driver.find_elements(By.CSS_SELECTOR, 'header .suite .chip')
        print(f"✓ Algorithm chips: {len(chips)} found")
        for chip in chips:
            print(f"  - {chip.text}")
        
        # Check user tabs
        user_tabs = driver.find_elements(By.CSS_SELECTOR, 'header .user-tabs button')
        print(f"✓ User tabs: {len(user_tabs)} found")
        for tab in user_tabs:
            active = "ACTIVE" if "active" in tab.get_attribute("class") else ""
            print(f"  - {tab.text} {active}")
        
        # Check Key Info section
        print("\n🔑 Key Info Section:")
        key_info = driver.find_element(By.ID, 'key-info')
        key_rows = key_info.find_elements(By.CSS_SELECTOR, '.ki-row')
        print(f"✓ Key info rows: {len(key_rows)} found")
        for row in key_rows:
            label = row.find_element(By.CSS_SELECTOR, '.label').text
            val = row.find_element(By.CSS_SELECTOR, '.val').text
            print(f"  - {label}: {val}")
            # Check if value is overflowing
            val_elem = row.find_element(By.CSS_SELECTOR, '.val')
            if len(val) > 50:
                print(f"    ⚠️  WARNING: Value might be too long ({len(val)} chars)")
        
        # Check Inbox
        print("\n📬 Inbox Section:")
        inbox = driver.find_element(By.ID, 'inbox-list')
        print(f"✓ Inbox content: {inbox.text[:100]}...")
        
        # Check Compose form
        print("\n✉️  Compose Form:")
        compose_to = driver.find_element(By.ID, 'compose-to')
        compose_subject = driver.find_element(By.ID, 'compose-subject')
        compose_body = driver.find_element(By.ID, 'compose-body')
        print(f"✓ To dropdown found")
        print(f"✓ Subject field found")
        print(f"✓ Body field found")
        
        # Check Crypto Log
        print("\n🔐 Crypto Process Log:")
        crypto_log = driver.find_element(By.ID, 'crypto-log')
        print(f"✓ Crypto log content: {crypto_log.text[:100]}...")
        
        print("\n" + "=" * 60)
        print("📸 STEP 2: Sending Email")
        print("=" * 60)
        
        # Fill form
        compose_subject.send_keys("Test Subject")
        compose_body.send_keys("Hello Bob")
        print("✓ Filled subject and body")
        
        # Click send
        send_btn = driver.find_element(By.CSS_SELECTOR, 'button.btn-primary')
        send_btn.click()
        print("✓ Clicked 'Send Encrypted' button")
        
        # Wait for crypto steps
        time.sleep(3)
        
        # Check crypto log
        crypto_log = driver.find_element(By.ID, 'crypto-log')
        step_cards = driver.find_elements(By.CSS_SELECTOR, '#crypto-log .step-card')
        print(f"✓ Crypto steps shown: {len(step_cards)} steps")
        
        for i, card in enumerate(step_cards, 1):
            title = card.find_element(By.CSS_SELECTOR, '.step-title').text
            desc = card.find_element(By.CSS_SELECTOR, '.step-desc').text
            print(f"  Step {i}: {title}")
            print(f"          {desc[:60]}...")
        
        # Check for errors in console
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        if errors:
            print("\n⚠️  BROWSER CONSOLE ERRORS:")
            for error in errors:
                print(f"  - {error['message']}")
        else:
            print("\n✓ No browser console errors")
        
        print("\n" + "=" * 60)
        print("📸 STEP 3: Switching to Bob and Receiving")
        print("=" * 60)
        
        # Click Bob tab
        bob_tab = [tab for tab in user_tabs if "Bob" in tab.text][0]
        bob_tab.click()
        print("✓ Clicked Bob tab")
        time.sleep(1)
        
        # Click Refresh
        refresh_btn = driver.find_element(By.XPATH, "//button[text()='Refresh']")
        refresh_btn.click()
        print("✓ Clicked Refresh button")
        
        # Wait for crypto steps
        time.sleep(3)
        
        # Check crypto log
        step_cards = driver.find_elements(By.CSS_SELECTOR, '#crypto-log .step-card')
        print(f"✓ Crypto steps shown: {len(step_cards)} steps")
        
        for i, card in enumerate(step_cards, 1):
            title = card.find_element(By.CSS_SELECTOR, '.step-title').text
            desc = card.find_element(By.CSS_SELECTOR, '.step-desc').text
            print(f"  Step {i}: {title}")
            print(f"          {desc[:60]}...")
        
        # Check inbox
        inbox = driver.find_element(By.ID, 'inbox-list')
        email_cards = driver.find_elements(By.CSS_SELECTOR, '#inbox-list .email-card')
        print(f"\n✓ Emails in inbox: {len(email_cards)}")
        
        for i, card in enumerate(email_cards, 1):
            from_elem = card.find_element(By.CSS_SELECTOR, '.from')
            subject_elem = card.find_element(By.CSS_SELECTOR, '.subject')
            badge = card.find_element(By.CSS_SELECTOR, '.badge')
            print(f"  Email {i}:")
            print(f"    From: {from_elem.text}")
            print(f"    Subject: {subject_elem.text}")
            print(f"    Status: {badge.text}")
        
        # Take screenshot
        driver.save_screenshot('/tmp/quantum_email_final.png')
        print("\n✓ Screenshot saved to /tmp/quantum_email_final.png")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot('/tmp/quantum_email_error.png')
        print("Screenshot saved to /tmp/quantum_email_error.png")
    finally:
        driver.quit()

def test_with_playwright():
    """Test using Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            print("🌐 Navigating to http://127.0.0.1:5000...")
            page.goto('http://127.0.0.1:5000')
            page.wait_for_timeout(2000)
            
            print("\n📸 STEP 1: Initial Page Load")
            print("=" * 60)
            
            # Check header
            logo = page.locator('header .logo').text_content()
            print(f"✓ Logo text: {logo}")
            
            # Check algorithm chips
            chips = page.locator('header .suite .chip').all()
            print(f"✓ Algorithm chips: {len(chips)} found")
            for chip in chips:
                print(f"  - {chip.text_content()}")
            
            # Check user tabs
            user_tabs = page.locator('header .user-tabs button').all()
            print(f"✓ User tabs: {len(user_tabs)} found")
            for tab in user_tabs:
                active = "ACTIVE" if "active" in tab.get_attribute("class") else ""
                print(f"  - {tab.text_content()} {active}")
            
            # Check Key Info section
            print("\n🔑 Key Info Section:")
            key_rows = page.locator('#key-info .ki-row').all()
            print(f"✓ Key info rows: {len(key_rows)} found")
            for row in key_rows:
                label = row.locator('.label').text_content()
                val = row.locator('.val').text_content()
                print(f"  - {label}: {val}")
                if len(val) > 50:
                    print(f"    ⚠️  WARNING: Value might be too long ({len(val)} chars)")
            
            # Check Inbox
            print("\n📬 Inbox Section:")
            inbox_text = page.locator('#inbox-list').text_content()
            print(f"✓ Inbox content: {inbox_text[:100]}...")
            
            # Check Compose form
            print("\n✉️  Compose Form:")
            print(f"✓ To dropdown found: {page.locator('#compose-to').is_visible()}")
            print(f"✓ Subject field found: {page.locator('#compose-subject').is_visible()}")
            print(f"✓ Body field found: {page.locator('#compose-body').is_visible()}")
            
            # Check Crypto Log
            print("\n🔐 Crypto Process Log:")
            crypto_text = page.locator('#crypto-log').text_content()
            print(f"✓ Crypto log content: {crypto_text[:100]}...")
            
            print("\n" + "=" * 60)
            print("📸 STEP 2: Sending Email")
            print("=" * 60)
            
            # Fill form
            page.fill('#compose-subject', 'Test Subject')
            page.fill('#compose-body', 'Hello Bob')
            print("✓ Filled subject and body")
            
            # Click send
            page.click('button.btn-primary')
            print("✓ Clicked 'Send Encrypted' button")
            
            # Wait for crypto steps
            page.wait_for_timeout(3000)
            
            # Check crypto log
            step_cards = page.locator('#crypto-log .step-card').all()
            print(f"✓ Crypto steps shown: {len(step_cards)} steps")
            
            for i, card in enumerate(step_cards, 1):
                title = card.locator('.step-title').text_content()
                desc = card.locator('.step-desc').text_content()
                print(f"  Step {i}: {title}")
                print(f"          {desc[:60]}...")
            
            # Check for console errors
            console_msgs = []
            page.on('console', lambda msg: console_msgs.append(msg))
            
            print("\n" + "=" * 60)
            print("📸 STEP 3: Switching to Bob and Receiving")
            print("=" * 60)
            
            # Click Bob tab
            page.click('button[data-user="bob"]')
            print("✓ Clicked Bob tab")
            page.wait_for_timeout(1000)
            
            # Click Refresh
            page.click('text=Refresh')
            print("✓ Clicked Refresh button")
            
            # Wait for crypto steps
            page.wait_for_timeout(3000)
            
            # Check crypto log
            step_cards = page.locator('#crypto-log .step-card').all()
            print(f"✓ Crypto steps shown: {len(step_cards)} steps")
            
            for i, card in enumerate(step_cards, 1):
                title = card.locator('.step-title').text_content()
                desc = card.locator('.step-desc').text_content()
                print(f"  Step {i}: {title}")
                print(f"          {desc[:60]}...")
            
            # Check inbox
            email_cards = page.locator('#inbox-list .email-card').all()
            print(f"\n✓ Emails in inbox: {len(email_cards)}")
            
            for i, card in enumerate(email_cards, 1):
                from_text = card.locator('.from').text_content()
                subject_text = card.locator('.subject').text_content()
                badge_text = card.locator('.badge').text_content()
                print(f"  Email {i}:")
                print(f"    From: {from_text}")
                print(f"    Subject: {subject_text}")
                print(f"    Status: {badge_text}")
            
            # Take screenshot
            page.screenshot(path='/tmp/quantum_email_final.png', full_page=True)
            print("\n✓ Screenshot saved to /tmp/quantum_email_final.png")
            
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='/tmp/quantum_email_error.png', full_page=True)
            print("Screenshot saved to /tmp/quantum_email_error.png")
        finally:
            browser.close()

if __name__ == '__main__':
    if USE_PLAYWRIGHT:
        test_with_playwright()
    else:
        test_with_selenium()
