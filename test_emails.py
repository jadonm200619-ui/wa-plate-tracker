import os
import resend

# Grab your Resend API key directly from environment or paste it for testing
resend.api_key = os.environ.get("RESEND_API_KEY")

print("Sending test emails...")

try:
    # 1. Test Subscription Confirmation
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": test_email,
        "subject": "✅ TEST: WA Plate Tracker - Tracking Confirmed!",
        "html": "<h2>Test: Tracking Confirmed</h2><p>This is a test subscription confirmation email.</p>"
    })
    print("✅ Subscription confirmation email sent!")

    # 2. Test Opt-Out Confirmation
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": test_email,
        "subject": "🛑 TEST: WA Plate Tracker - Tracking Cancelled",
        "html": "<h2>Test: Tracking Cancelled</h2><p>This is a test opt-out confirmation email.</p>"
    })
    print("✅ Opt-out confirmation email sent!")

    # 3. Test Plate Match Alert
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": test_email,
        "subject": "🚨 TEST: WA Plate 'LEXUS12' is AVAILABLE!",
        "html": "<h2>Test: Match Found!</h2><p>The Washington personalized plate <strong>LEXUS12</strong> is currently AVAILABLE!</p>"
    })
    print("✅ Plate match alert email sent!")

    print("All 3 test emails dispatched successfully! Check your inbox.")

except Exception as e:
    print(f"❌ Error sending test email: {e}")
