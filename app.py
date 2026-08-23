import os
import streamlit as st
import random
import time
from playwright.sync_api import sync_playwright

# Install the browser
os.system("playwright install chromium")

st.set_page_config(page_title="WA Plate Alert", page_icon="🚗")
st.title("🚗 WA Plate Availability Tracker")

st.markdown("""
Want a specific personalized license plate in Washington? 
Enter your email and the plates you want. We will automatically check the WA DOL website and email you the moment one becomes available!
""")

# --- 1. The Subscription Form ---
with st.form("plate_form"):
    email = st.text_input("Your Email Address")
    plates = st.text_area("Plates to Track (one per line, max 7 letters)", placeholder="LEXUS12\nIS350C\nTEST123")
    
    # New Frequency Feature
    frequency = st.selectbox("How often should we check?", ["1 time per day", "2 times per day", "3 times per day"])
    
    submitted = st.form_submit_button("Start Tracking")
    
    if submitted:
        if email and plates:
            st.success(f"Success! We will notify you at {email}. Checking {frequency}.")
            # Next phase: Save this to a database!
        else:
            st.error("Please enter both an email and at least one plate.")

st.divider()

# --- 2. Manual Check Feature (Using Proxies) ---
st.subheader("Manual Check")
st.write("Want to see if a plate is available right now?")
manual_plate = st.text_input("Enter a single plate to check:", max_chars=7).upper()

if st.button("Check Availability Now", type="primary") and manual_plate:
    # Securely load the proxies and pick one at random
    proxy_list = st.secrets["proxies"]
    chosen_proxy = random.choice(proxy_list)
    
    proxy_config = {
        "server": chosen_proxy["server"],
        "username": chosen_proxy["username"],
        "password": chosen_proxy["password"]
    }
    
    st.info(f"Connecting securely via residential proxy...")
    
    try:
        with sync_playwright() as p:
            # Launch the hidden browser using the chosen proxy
            browser = p.chromium.launch(headless=True, proxy=proxy_config)
            page = browser.new_page()
            
            # Go to the WA DOL site
            page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
            
            # (We will add the exact HTML clicking logic for WA DOL later)
            time.sleep(2)
            
            # Dummy logic to test the UI
            result = "Available 🟢" if len(manual_plate) % 2 == 0 else "Taken 🔴"
            
            st.success(f"Result for {manual_plate}: **{result}**")
            browser.close()
            
    except Exception as e:
        st.error(f"Failed to check plate: {e}")
