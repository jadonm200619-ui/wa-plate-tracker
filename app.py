import streamlit as st
from supabase import create_client, Client
import resend

# Page Config
st.set_page_config(page_title="WA Personalized Plate Tracker", page_icon="🚗", layout="centered")

# Initialize Supabase and Resend from Streamlit Secrets
SUPABASE_URL = "https://ywqbkgnkoiagimbneklv.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
RESEND_API_KEY = st.secrets["RESEND_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
resend.api_key = RESEND_API_KEY

st.title("🚗 Washington Personalized Plate Tracker")
st.write("Track availability for your favorite Washington State custom license plates and get notified instantly when they open up.")

# Tabs for registering vs managing opt-out
tab1, tab2 = st.tabs(["Register Plate", "Manage / Opt-Out"])

with tab1:
    st.subheader("Register a Plate for Tracking")
    with st.form("plate_form"):
        plate_input = st.text_input("Enter Plate Number (Max 7 characters)", max_chars=7).upper()
        email_input = st.text_input("Your Email Address")
        submit_button = st.form_submit_button("Start Tracking")

        if submit_button:
            if not plate_input or not email_input:
                st.error("Please fill in both the plate string and your email address.")
            else:
                try:
                    # Insert into Supabase
                    supabase.table("plate_requests").insert({
                        "plate_string": plate_input,
                        "email": email_input,
                        "is_active": True
                    }).execute()
                    
                    st.success(f"Successfully registered plate **{plate_input}** for tracking! We'll email you if it becomes available.")
                except Exception as e:
                    st.error(f"Error registering plate: {e}")

with tab2:
    st.subheader("Manage Active Trackers & Opt-Out")
    st.write("Enter your registered email address to view your active plates and stop tracking if desired.")
    
    lookup_email = st.text_input("Enter your registered email", key="lookup_email_input")
    
    if st.button("Find My Trackers"):
        if not lookup_email:
            st.warning("Please enter an email address.")
        else:
            response = supabase.table("plate_requests").select("*").eq("email", lookup_email).eq("is_active", True).execute()
            active_requests = response.data
            
            if not active_requests:
                st.info("No active plate requests found for this email address.")
            else:
                st.session_state["user_requests"] = active_requests

    # Display active requests if found
    if "user_requests" in st.session_state and st.session_state["user_requests"]:
        st.write("### Your Active Trackers:")
        for req in st.session_state["user_requests"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"Plate: {req['plate_string']}")
            with col2:
                if st.button(f"Opt Out", key=f"optout_{req['id']}"):
                    try:
                        # 1. Update Supabase status to inactive
                        supabase.table("plate_requests").update({"is_active": False}).eq("id", req["id"]).execute()
                        
                        # 2. Send Opt-Out Confirmation Email via Resend
                        email_html = f"""
                        <h2>Tracking Cancelled</h2>
                        <p>You have successfully opted out of tracking for the Washington personalized plate <strong>{req['plate_string']}</strong>.</p>
                        <p>You will no longer receive alerts for this plate unless you sign up again.</p>
                        """
                        
                        resend.Emails.send({
                            "from": "onboarding@resend.dev",
                            "to": req["email"],
                            "subject": f"Confirmation: Stopped tracking '{req['plate_string']}'",
                            "html": email_html
                        })
                        
                        st.success(f"Successfully opted out of **{req['plate_string']}**! Confirmation email sent.")
                        
                        # Refresh active list
                        st.session_state["user_requests"] = [r for r in st.session_state["user_requests"] if r['id'] != req['id']]
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Failed to opt out or send email: {e}")
