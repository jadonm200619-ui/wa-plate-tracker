import os
import streamlit as st

# This line ensures the cloud server installs the hidden web browser
os.system("playwright install chromium")

# Set up the webpage design
st.set_page_config(page_title="WA Plate Alert", page_icon="🚗")
st.title("🚗 WA Plate Availability Tracker")

st.markdown("""
Want a specific personalized license plate in Washington? 
Enter your email and the plates you want. We will automatically check the WA DOL website 3 times a day and email you the moment one becomes available!
""")

# Create the submission form
with st.form("plate_form"):
    email = st.text_input("Your Email Address")
    plates = st.text_area("Plates to Track (one per line, max 7 letters)", placeholder="LEXUS12\nIS350C\nTEST123")
    
    submitted = st.form_submit_button("Start Tracking")
    
    if submitted:
        if email and plates:
            st.success(f"Success! We will notify you at {email} if these plates become available.")
            # Note: We will add the database logic to save this info in the next step!
        else:
            st.error("Please enter both an email and at least one plate.")
