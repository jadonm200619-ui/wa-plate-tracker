import os
import time
from datetime import datetime, timedelta
import pytz
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
import resend

# Read environment variables directly from GitHub Actions
SUPABASE_URL = "https://ywqbkgnkoiagimbneklv.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
resend.api_key = RESEND_API_KEY

def run_automated_checks():
    # Get current time in Pacific Time
    pacific_tz = pytz.timezone("America/Los_Angeles")
    now_pacific = datetime.now(pacific_tz)
    
    current_hour = now_pacific.strftime("%I") # e.g., "01"
    current_ampm = now_pacific.strftime("%p") # "PM"

    # Fetch active plate requests from Supabase
    response = supabase.table("plate_requests").select("*").eq("is_active", True).execute()
    requests = response.data
    
    if not requests:
        print("No active plate requests found.")
        return

    target_requests = []
    
    for req in requests:
        check_time_str = req.get("check_time", "") # e.g., "01:00 PM"
        frequency = req.get("frequency", "Once a day")
        last_checked_str = req.get("last_checked")
        
        # 1. Match the Hour and AM/PM block
        if not (current_hour in check_time_str and current_ampm in check_time_str):
            continue
            
        # 2. Check Frequency Rules if it was checked previously
        if last_checked_str:
            try:
                # Parse last checked time
                last_checked = datetime.fromisoformat(last_checked_str)
                if last_checked.tzinfo is None:
                    last_checked = pacific_tz.localize(last_checked)
                
                time_diff = now_pacific - last_checked
                
                if frequency == "Once a day" and time_diff < timedelta(hours=20):
                    continue # Skip if checked less than 20 hours ago
                elif frequency == "Every other day" and time_diff < timedelta(hours=44):
                    continue # Skip if checked less than 44 hours ago
                elif frequency == "Once a week" and time_diff < timedelta(days=6):
                    continue # Skip if checked less than 6 days ago
            except Exception as parse_err:
                print(f"Error parsing last_checked for request {req.get('id')}: {parse_err}")

        target_requests.append(req)

    if not target_requests:
        print(f"No requests due for checking at this hour ({now_pacific.strftime('%I:%M %p')}).")
        return

    print(f"Found {len(target_requests)} plates due for checking. Starting engine...")

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

        for req in target_requests:
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

                # Update last_checked timestamp regardless of taken/available status
                current_timestamp = now_pacific.isoformat()

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
                    
                    supabase.table("plate_requests").update({
                        "is_active": False,
                        "last_checked": current_timestamp
                    }).eq("id", req_id).execute()
                else:
                    print(f"Taken/Unavailable: {plate}")
                    supabase.table("plate_requests").update({
                        "last_checked": current_timestamp
                    }).eq("id", req_id).execute()

            except Exception as e:
                print(f"Error checking {plate}: {e}")
            
            time.sleep(1)

        browser.close()
        print("Automated checks completed.")

if __name__ == "__main__":
    run_automated_checks()
