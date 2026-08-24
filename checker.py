import os
import time
import random
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
import resend

# Read secrets directly from environment variables provided by GitHub Actions
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
resend.api_key = RESEND_API_KEY

def run_automated_checks():
    response = supabase.table("plate_requests").select("*").eq("is_active", True).execute()
    requests = response.data
    
    if not requests:
        print("No active plate requests to check.")
        return

    print(f"Found {len(requests)} active requests. Starting engine...")

    # Fallback list of proxies if environment variable isn't parsed as a list
    proxy_server = os.environ.get("PROXY_SERVER", "http://31.59.20.176:6754")
    proxy_user = os.environ.get("PROXY_USER", "rzzaqqtt")
    proxy_pass = os.environ.get("PROXY_PASS", "t01ddiw0xm8n")

    proxy_config = {
        "server": proxy_server,
        "username": proxy_user,
        "password": proxy_pass
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=proxy_config)
        page = browser.new_page()
        
        print("Connecting to WA DOL...")
        page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=15000)

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
                page.wait_for_timeout(1000)
                
                page_text = page.inner_text("body").lower()

                if "is available right now" in page_text:
                    print(f"🚨 MATCH FOUND: {plate} is AVAILABLE!")
                    
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
