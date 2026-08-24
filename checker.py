import os
import time
import random
import streamlit as st
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
import resend

# 1. Connect to Database and Email using Streamlit Secrets
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
resend.api_key = st.secrets["RESEND_API_KEY"]
proxy_list = st.secrets["proxies"]

def run_automated_checks():
    # 2. Pull all active plate requests from Supabase
    response = supabase.table("plate_requests").select("*").eq("is_active", True).execute()
    requests = response.data
    
    if not requests:
        print("No active plate requests to check.")
        return

    print(f"Found {len(requests)} active requests. Starting engine...")

    # 3. Setup Proxy
    chosen_proxy = random.choice(proxy_list)
    proxy_config = {
        "server": chosen_proxy["server"],
        "username": chosen_proxy["username"],
        "password": chosen_proxy["password"]
    }

    # 4. Launch Headless Browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=proxy_config)
        page = browser.new_page()
        
        print("Connecting to WA DOL...")
        page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)

        # 5. Check each plate in the database
        for req in requests:
            plate = req["plate_string"]
            user_email = req["email"]
            req_id = req["id"]

            print(f"Checking plate: {plate} for {user_email}")

            try:
                plate_input = page.locator("input[maxlength='7']")
                plate_input.wait_for(timeout=10000)
                plate_input.fill(plate)
                
                page.locator("button:has-text('Search')").click()
                page.wait_for_timeout(1000) # 1-second rapid pause
                
                page_text = page.inner_text("body").lower()

                if "is available right now" in page_text:
                    print(f"🚨 MATCH FOUND: {plate} is AVAILABLE!")
                    
                    # 6. Fire the Email Alert!
                    email_html = f"""
                    <h2>🎉 Great News!</h2>
                    <p>The Washington personalized plate <strong>{plate}</strong> is currently AVAILABLE!</p>
                    <p>Go to the WA DOL website right now to claim it!</p>
                    """
                    
                    resend.Emails.send({
                        "from": "onboarding@resend.dev",
                        "to": user_email,
                        "subject": f"🚨 WA Plate '{plate}' is AVAILABLE!",
                        "html": email_html
                    })
                    
                    # 7. Turn off tracking for this specific plate so we don't spam the user
                    supabase.table("plate_requests").update({"is_active": False}).eq("id", req_id).execute()
                else:
                    print(f"Taken/Unavailable: {plate}")

            except Exception as e:
                print(f"Error checking {plate}: {e}")
            
            time.sleep(1)

        browser.close()
        print("Automated checks completed.")

if __name__ == "__main__":
    run_automated_checks()
