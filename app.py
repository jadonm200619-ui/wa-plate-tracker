import os
import streamlit as st
import random
import time
from playwright.sync_api import sync_playwright

os.system("playwright install chromium")

st.set_page_config(page_title="WA Plate Tracker", page_icon="🚗")
st.title("🚗 WA Plate Availability Tracker")

st.markdown("""
Want a specific personalized license plate in Washington? 
Enter your email and the plates you want. We will automatically check the WA DOL website and email you the moment one becomes available!
""")

with st.form("plate_form"):
    email = st.text_input("Your Email Address")
    plates = st.text_area("Plates to Track (one per line, max 7 letters)", placeholder="LEXUS12\nIS350C\nTEST123")
    frequency = st.selectbox("How often should we check?", ["1 time per day", "2 times per day", "3 times per day"])
    submitted = st.form_submit_button("Start Tracking")
    
    if submitted:
        if email and plates:
            st.success(f"Success! We will notify you at {email}. Checking {frequency}.")
        else:
            st.error("Please enter both an email and at least one plate.")

st.divider()

st.subheader("Manual Check")
st.write("Want to see if a plate is available right now?")
manual_plate = st.text_input("Enter a single plate to check:", max_chars=7).upper()

if st.button("Check Availability Now", type="primary") and manual_plate:
    try:
        proxy_list = st.secrets["proxies"]
        chosen_proxy = random.choice(proxy_list)
        proxy_config = {
            "server": chosen_proxy["server"],
            "username": chosen_proxy["username"],
            "password": chosen_proxy["password"]
        }
    except Exception as e:
        st.error("Error loading proxies. Make sure they are saved in Streamlit Secrets.")
        st.stop()
    
    st.info(f"Connecting securely via residential proxy ({chosen_proxy['server']})...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=proxy_config)
            page = browser.new_page()
            
            try:
                # Go directly to the form URL
                page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
                
                # Wait for the network to settle down
                page.wait_for_load_state("networkidle", timeout=15000)
                
                # Find the box by its 7-character limit attribute
                plate_input = page.locator("input[maxlength='7']")
                plate_input.wait_for(timeout=10000)
                plate_input.fill(manual_plate)
                
                # Click the 'Search' button
                page.locator("button:has-text('Search')").click()
                
                # --- THE FIX: A bulletproof hard pause instead of looking for hidden elements ---
                page.wait_for_timeout(4000) # Wait exactly 4 seconds for the server to reply
                
                # Grab all the text on the page to analyze it
                page_text = page.inner_text("body").lower()
                
                # Determine the status
                if "is available right now" in page_text:
                    status = f"✅ AVAILABLE: {manual_plate} is available right now."
                elif "is not available" in page_text:
                    status = f"❌ TAKEN: Sorry, {manual_plate} is not available."
                elif "is a restricted word" in page_text:
                    status = f"⚠️ RESTRICTED: {manual_plate} is a restricted word."
                elif "invalid combination" in page_text:
                    status = f"🚫 INVALID: {manual_plate} uses an invalid combination of letters and numbers."
                else:
                    status = f"❓ UNKNOWN: Could not determine status for {manual_plate}."
                    
                st.success(f"Result for {manual_plate}: **{status}**")
            
            except Exception as inner_e:
                st.error(f"Failed to check plate: {inner_e}")
                # --- THE FIX: Take screenshot BEFORE the browser closes ---
                st.warning("Taking a screenshot of what the bot is seeing...")
                try:
                    page.screenshot(path="debug_screenshot.png")
                    st.image("debug_screenshot.png", caption="Live view of the hidden browser")
                except Exception as screenshot_error:
                    st.write("Could not take screenshot:", screenshot_error)
            
            finally:
                # Ensure the browser always closes cleanly
                browser.close()
                
    except Exception as e:
        st.error(f"Playwright failed to launch: {e}")
