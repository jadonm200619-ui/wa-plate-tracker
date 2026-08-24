import os
import streamlit as st
import random
import time
from playwright.sync_api import sync_playwright

# Install the browser on the cloud server
os.system("playwright install chromium")

# --- Page Config ---
st.set_page_config(page_title="WA Plate Tracker", page_icon="🚗")
st.title("🚗 WA Plate Availability Tracker")

st.markdown("""
Want a specific personalized license plate in Washington? 
Enter your email and the plates you want. We will automatically check the WA DOL website and email you the moment one becomes available!
""")

# --- 1. The Subscription Form ---
with st.form("plate_form"):
    email = st.text_input("Your Email Address")
    plates = st.text_area("Plates to Track (one per line, max 7 letters)", placeholder="LEXUS12\nIS350C\nTEST123")
    
    # New Specific Time Selection Feature
    check_times = st.multiselect(
        "Select the times you want us to check (Pacific Time):", 
        ["8:00 AM", "12:00 PM", "4:00 PM", "8:00 PM"],
        default=["8:00 AM"]
    )
    
    submitted = st.form_submit_button("Start Tracking")
    
    if submitted:
        if email and plates and check_times:
            # Join the times together for a clean success message
            times_str = ", ".join(check_times)
            st.success(f"Success! We will check your plates at {times_str} and notify {email} if any become available.")
            # Note: Database integration for saving this info will go here.
        else:
            st.error("Please enter an email, at least one plate, and select at least one time.")

st.divider()

# --- 2. Manual Check Feature (Using Proxies) ---
st.subheader("Manual Check")
st.write("Want to see if plates are available right now?")

# Changed to a text_area to accept multiple plates
manual_plates_input = st.text_area("Enter up to 10 plates to check (one per line, max 7 letters):", placeholder="LEXUS12\nIS350C").upper()

if st.button("Check Availability Now", type="primary") and manual_plates_input:
    # Clean up the input into a list of plates
    raw_plates = [p.strip() for p in manual_plates_input.split('\n') if p.strip()]
    
    # Restrict to 10 plates max to prevent timeout limits
    if len(raw_plates) > 10:
        st.warning(f"You entered {len(raw_plates)} plates. We are only checking the first 10.")
        plates_to_check = raw_plates[:10]
    else:
        plates_to_check = raw_plates
        
    if not plates_to_check:
        st.error("Please enter at least one valid plate.")
        st.stop()
        
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
    
    st.info(f"Connecting securely via residential proxy ({chosen_proxy['server']}). Checking {len(plates_to_check)} plate(s)...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=proxy_config)
            page = browser.new_page()
            
            # Loop through each plate the user entered
            for manual_plate in plates_to_check:
                # Ensure it is 7 characters max just in case
                manual_plate = manual_plate[:7]
                
                try:
                    # Reload the main form page fresh for EACH plate to avoid hidden HTML traps
                    page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    
                    # Find the box by its 7-character limit attribute
                    plate_input = page.locator("input[maxlength='7']")
                    plate_input.wait_for(timeout=10000)
                    plate_input.fill(manual_plate)
                    
                    # Click the 'Search' button
                    page.locator("button:has-text('Search')").click()
                    
                    # Hard pause to let the server reply
                    page.wait_for_timeout(4000) 
                    
                    # Grab all the text on the page to analyze it
                    page_text = page.inner_text("body").lower()
                    
                    # Determine the status
                    if "is available right now" in page_text:
                        status = f"✅ AVAILABLE: **{manual_plate}** is available right now."
                    elif "is not available" in page_text:
                        status = f"❌ TAKEN: Sorry, **{manual_plate}** is not available."
                    elif "is a restricted word" in page_text:
                        status = f"⚠️ RESTRICTED: **{manual_plate}** is a restricted word."
                    elif "invalid combination" in page_text:
                        status = f"🚫 INVALID: **{manual_plate}** uses an invalid combination of letters and numbers."
                    else:
                        status = f"❓ UNKNOWN: Could not determine status for **{manual_plate}**."
                        
                    # Output the result immediately to the dashboard
                    st.write(status)
                    
                except Exception as loop_error:
                    st.error(f"⚠️ ERROR: Failed to check **{manual_plate}**")
                
                # Brief 1.5-second pause between checks so we don't hammer the DOL server too fast
                time.sleep(1.5)
            
            browser.close()
            st.success("All checks completed!")
            
    except Exception as e:
        st.error(f"Playwright failed to launch: {e}")
