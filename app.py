import os
import streamlit as st
import random
import time
import datetime
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
import resend

# Install the browser on the cloud server
os.system("playwright install chromium")

# --- Page Config ---
st.set_page_config(page_title="WA Plate Tracker", page_icon="🚗", layout="centered")
st.title("🚗 WA Plate Availability Tracker")

st.markdown("""
Track Washington personalized license plate availability automatically. 
Enter your email, set your schedule, and receive email alerts the moment a plate becomes available.
""")

# --- Initialize Database & Email Connections ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Database connection failed. Please check your Streamlit Secrets.")

try:
    resend.api_key = st.secrets["RESEND_API_KEY"]
except Exception as e:
    st.error("Resend connection failed. Please check your Streamlit Secrets.")

# --- Tab Navigation: Subscribe vs. Opt Out ---
tab_track, tab_optout = st.tabs(["📌 Track Plates", "🛑 Opt Out / Unsubscribe"])

# ==========================================
# TAB 1: SUBSCRIPTION FORM
# ==========================================
with tab_track:
    with st.form("plate_form"):
        email = st.text_input("Your Email Address", placeholder="name@example.com")
        plates = st.text_area(
            "Plates to Track (one per line, up to 10 plates, max 7 letters)", 
            placeholder="LEXUS12\nIS350C\nJM"
        )
        
        frequency = st.selectbox(
            "How often should we check?",
            ["Once a day", "Every other day", "Once a week"]
        )
        
        check_time = st.time_input(
            "Preferred Check Time (Pacific Time):", 
            value=datetime.time(12, 0)
        )
        
        submitted = st.form_submit_button("Start Tracking", type="primary")
        
        if submitted:
            raw_plates = [p.strip().upper() for p in plates.split('\n') if p.strip()]
            if email and raw_plates and check_time:
                formatted_time = check_time.strftime("%I:%M %p")
                
                try:
                    # 1. Save to Database
                    for plate in raw_plates[:10]:
                        supabase.table("plate_requests").insert({
                            "email": email,
                            "plate_string": plate,
                            "frequency": frequency,
                            "check_time": formatted_time,
                            "is_active": True
                        }).execute()
                        
                    # 2. Send Confirmation Email via Resend
                    email_html = f"""
                    <h2>🚗 WA Plate Tracker Confirmation</h2>
                    <p>You are all set! We will automatically check the WA DOL website for the following plates:</p>
                    <ul>
                        {''.join([f'<li><strong>{p}</strong></li>' for p in raw_plates[:10]])}
                    </ul>
                    <p><strong>Frequency:</strong> {frequency}</p>
                    <p><strong>Time:</strong> {formatted_time}</p>
                    <p>We'll email you the second one becomes available.</p>
                    """
                    
                    resend.Emails.send({
                        "from": "onboarding@resend.dev",
                        "to": email,
                        "subject": "✅ WA Plate Tracker - Tracking Confirmed!",
                        "html": email_html
                    })
                        
                    st.success(
                        f"✅ **Tracking Confirmed!** Confirmation email sent to **{email}**.\n\n"
                        f"- **Plates ({len(raw_plates[:10])}):** {', '.join(raw_plates[:10])}\n"
                        f"- **Frequency:** {frequency}\n"
                        f"- **Time:** {formatted_time}"
                    )
                except Exception as e:
                    st.error(f"Failed to process request. Make sure you are using your verified Resend email address. Error: {e}")
            else:
                st.error("Please provide a valid email, at least one plate, and select a check time.")

# ==========================================
# TAB 2: OPT-OUT / UNSUBSCRIBE FORM
# ==========================================
with tab_optout:
    st.subheader("Manage Subscription")
    st.write("No longer looking for plates? Enter your email address below to remove all active tracking and receive a confirmation email.")
    
    with st.form("opt_out_form"):
        optout_email = st.text_input("Registered Email Address", placeholder="name@example.com")
        optout_submitted = st.form_submit_button("Stop Tracking All Plates")
        
        if optout_submitted:
            if optout_email:
                try:
                    # 1. Update database to deactivate tracking for this email
                    supabase.table("plate_requests").update({"is_active": False}).eq("email", optout_email).execute()
                    
                    # 2. Send Opt-Out Confirmation Email via Resend
                    optout_html = f"""
                    <h2>🛑 WA Plate Tracker - Unsubscribed</h2>
                    <p>Tracking has been successfully cancelled for <strong>{optout_email}</strong>.</p>
                    <p>You will no longer receive automated alerts for your plates.</p>
                    """
                    
                    resend.Emails.send({
                        "from": "onboarding@resend.dev",
                        "to": optout_email,
                        "subject": "🛑 WA Plate Tracker - Tracking Cancelled",
                        "html": optout_html
                    })
                    
                    st.success(f"Tracking has been cancelled for **{optout_email}**. A confirmation email has been sent.")
                except Exception as e:
                    st.error(f"Failed to update database or send email. Error: {e}")
            else:
                st.error("Please enter the email address you wish to unsubscribe.")

st.divider()

# ==========================================
# SECTION 3: MANUAL CHECK (UP TO 10 PLATES)
# ==========================================
st.subheader("🔍 Run Instant Check")
st.write("Check live availability right now (up to 10 plates at once).")

manual_plates_input = st.text_area(
    "Enter plates to check (one per line, max 7 letters):", 
    placeholder="LEXUS12\nIS350C"
).upper()

if st.button("Check Availability Now", type="primary") and manual_plates_input:
    raw_plates = [p.strip() for p in manual_plates_input.split('\n') if p.strip()]
    
    if len(raw_plates) > 10:
        st.warning(f"You entered {len(raw_plates)} plates. Checking the first 10.")
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
    
    st.info(f"Connected securely via residential proxy ({chosen_proxy['server']}).")
    
    status_container = st.status("Initializing automated check...", expanded=True)
    results_display = st.container()
    
    try:
        with sync_playwright() as p:
            status_container.update(label="Launching secure headless browser...", state="running")
            browser = p.chromium.launch(headless=True, proxy=proxy_config)
            page = browser.new_page()
            
            total_plates = len(plates_to_check)
            
            status_container.update(label="Connecting to WA DOL server...", state="running")
            page.goto("https://fortress.wa.gov/dol/extdriveses/ESP/NoLogon/?Link=PersonalizedPlate", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=15000)
            
            for index, manual_plate in enumerate(plates_to_check, start=1):
                clean_plate = manual_plate[:7]
                status_container.update(
                    label=f"Checking plate {index} of {total_plates}: **{clean_plate}**...", 
                    state="running"
                )
                
                try:
                    plate_input = page.locator("input[maxlength='7']")
                    plate_input.wait_for(timeout=10000)
                    plate_input.fill(clean_plate)
                    page.locator("button:has-text('Search')").click()
                    
                    page.wait_for_timeout(1000)
                    
                    page_text = page.inner_text("body").lower()
                    
                    if "is available right now" in page_text:
                        plate_status = f"✅ **AVAILABLE:** `{clean_plate}` is available right now."
                    elif "is not available" in page_text:
                        plate_status = f"❌ **TAKEN:** Sorry, `{clean_plate}` is not available."
                    elif "is a restricted word" in page_text:
                        plate_status = f"⚠️ **RESTRICTED:** `{clean_plate}` is a restricted word."
                    elif "invalid combination" in page_text:
                        plate_status = f"🚫 **INVALID:** `{clean_plate}` uses an invalid combination of letters and numbers."
                    else:
                        plate_status = f"❓ **UNKNOWN:** Could not determine status for `{clean_plate}`."
                        
                    results_display.markdown(plate_status)
                    
                except Exception as loop_error:
                    results_display.error(f"⚠️ **ERROR:** Failed to check `{clean_plate}` ({loop_error})")
                
                if index < total_plates:
                    status_container.update(label=f"Pausing before next lookup...", state="running")
                    time.sleep(1)
            
            browser.close()
            status_container.update(label="All plate checks completed successfully!", state="complete", expanded=False)
            st.success("Lookup process complete.")
            
    except Exception as e:
        st.error(f"Playwright execution error: {e}")
