#!/usr/bin/env python3
import hashlib
import io
import os
import streamlit as st
import stripe
from google import genai
from dotenv import load_dotenv

from supabase import create_client, Client
from streamlit_local_storage import LocalStorage
#!/usr/bin/env python3
import io
import os
import time
import stripe
import streamlit as st
from dotenv import load_dotenv

from google import genai
from google.genai import types
from gtts import gTTS
from supabase import create_client, Client

# Load environment variables securely from .env file
load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
stripe_secret_key = os.environ.get("STRIPE_SANDBOX_API_KEY")
stripe_price_id = os.environ.get("STRIPE_PRICE_ID")

# Initialize the Stripe SDK key
stripe.api_key = stripe_secret_key

# Safely initialize the Supabase client to prevent connection overloads
@st.cache_resource
def get_supabase() -> Client:
    return create_client(supabase_url, supabase_key)

supabase = get_supabase()
url_params = st.query_params

# ==========================================
# 📱 STREAMLIT PAGE CONFIG & MOBILE STYLING
# ==========================================
st.set_page_config(page_title="Point, shoot, listen", page_icon="🔊", layout="centered")
st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    div[data-testid="stCameraInput"] { width: 100% !important; }
    div[data-testid="stCameraInput"] video { width: 100% !important; height: auto !important; }
    div[data-testid="stCameraInput"] img { width: 100% !important; height: auto !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🔊 Point, shoot, listen")

# ==========================================
# 🆕 TRACK ANONYMOUS SESSIONS (FREE TRIAL)
# ==========================================
local_storage = LocalStorage()
 #👇 PASTE THIS LINE TEMPORARILY TO WIPE THE BAD DATA
#local_storage.setItem("anon_scan_count", 0)

ip_hash = None
FREE_LIMIT = 1
anon_scans = 0
ip_hash = None

# ✅ INITIALIZE SESSION STATE KEYS TO PREVENT CRASHES
if "anon_scans" not in st.session_state:
    st.session_state.anon_scans = 0
if "fallback_anon_scans" not in st.session_state:
    st.session_state.fallback_anon_scans = 0

# Check authentication status safely
is_authenticated = "user_session" in st.session_state and st.session_state.user_session is not None

# 🚀 STEP 3 FIX: Look for a forwarded network signature first, fall back to native context rules
forwarded_header = st.context.headers.get("x-forwarded-for")
if forwarded_header:
    # Extract the true client origin address if sitting behind a web proxy cloud cluster
    user_ip = forwarded_header.split(",")[0].strip()
else:
    user_ip = st.context.ip_address

if not is_authenticated:
    # Handle development fallbacks if running on your local machine
    if user_ip is None or user_ip == "127.0.0.1" or user_ip == "::1" or user_ip == "DEV_LOCAL_MACHINE_IP":
        user_ip = "DEV_LOCAL_MACHINE_IP"
        
    # Securely hash the IP so you aren't storing raw personal identifiers in plain text
    ip_hash = hashlib.sha256(user_ip.encode()).hexdigest()
    
    # 🔒 SECURE REFRESH LOCK
    try:
        res = supabase.table("device_tracking").select("scan_count").eq("ip_hash", ip_hash).maybe_single().execute()
        if res.data:
            anon_scans = int(res.data.get("scan_count", 0))
            # ✅ Sync state to the true database number immediately
            st.session_state.anon_scans = anon_scans
            st.session_state.fallback_anon_scans = anon_scans
        else:
            supabase.table("device_tracking").insert({"ip_hash": ip_hash, "scan_count": 0}).execute()
            anon_scans = 0
            st.session_state.anon_scans = 0
            st.session_state.fallback_anon_scans = 0
    except Exception:
        anon_scans = st.session_state.get("fallback_anon_scans", 0)

allow_anonymous_processing = anon_scans < FREE_LIMIT and not is_authenticated# Helper to clear stashed AI solutions during login transitions
def clear_active_solution():
    st.session_state.latest_solution_text = None
    st.session_state.latest_solution_audio = None
# ==========================================
# 🔐 THE LOGIN GATEWAY (ONLY TRIGGERED AFTER 5 FREE SCANS)
# ==========================================
if not allow_anonymous_processing and not is_authenticated:
    st.warning("⚠️ Free Limit Reached: Create a free account or sign in to continue using the scanner.")
    
    # Inbound password reset interceptor
    if "type" in url_params and url_params["type"] == "recovery":
        st.subheader("🔄 Choose a New Password")
        new_password = st.text_input("Type your new secure password:", type="password")
        confirm_password = st.text_input("Confirm your new password:", type="password")
        
        if st.button("Update Password and Log In", use_container_width=True):
            if len(new_password) < 6:
                st.warning("Password must be at least 6 characters long.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    supabase.auth.update_user({"password": new_password})
                    st.success("Password updated successfully!")
                    st.query_params.clear()
                    clear_active_solution()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update password: {e}")
        st.stop()

    tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Create Account"])
    
    with tab1:
        login_email = st.text_input("Email Address", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Log In", use_container_width=True):
            try:
                response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_password})
                uid = response.user.id
                
                # 🔄 SYNC AT LOGIN: Fetch existing scans, merge them, and save
                res = supabase.table("profiles").select("scan_count").eq("id", uid).maybe_single().execute()
                if res.data:
                    existing_db_scans = res.data.get("scan_count", 0)
                    new_total = existing_db_scans + anon_scans
                    supabase.table("profiles").update({"scan_count": new_total}).eq("id", uid).execute()
                
                if ip_hash:
                    supabase.table("device_tracking").update({"scan_count": 0}).eq("ip_hash", ip_hash).execute()
                
                st.session_state.user_session = response.session
                st.success("Access Granted!")
                clear_active_solution()
                st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")

        # 🔄 👇 NEW: FORGOT PASSWORD REQUEST DISCOVERY
        st.markdown("---")
        with st.expander("Forgot Password?"):
            reset_email = st.text_input("Enter your account email:", key="reset_email_input")
            if st.button("Send Reset Link Email", use_container_width=True):
                if not reset_email.strip():
                    st.warning("Please provide a valid email address.")
                else:
                    try:
                        # Fires off the Supabase server email mechanism targeting your render application domain
                        supabase.auth.reset_password_for_email(
                            reset_email, 
                            options={"redirectTo": "https://onrender.com"}
                        )
                        st.success("Recovery instructions dispatched! Check your email inbox for your reset link.")
                    except Exception as reset_err:
                        st.error(f"Failed to issue reset pipeline: {reset_err}")

                
    with tab2:
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Sign Up", use_container_width=True):
            try:
                # 🔄 UPGRADED REGISTRATION HOOK
                # Passes the un-hackable server IP scan count straight into the account metadata
                supabase.auth.sign_up({
                    "email": reg_email, 
                    "password": reg_password,
                    "options": {
                        "data": {
                            "scan_count": anon_scans
                        }
                    }
                })
                
                # ✅ FIX: Update the secure database server table instead of hackable cookies
                if ip_hash:
                    supabase.table("device_tracking").update({"scan_count": 0}).eq("ip_hash", ip_hash).execute()
                
                st.success("Account created successfully! Check your email inbox for a confirmation link, then Sign In.")
            except Exception as e:
                st.error(f"Registration Error: {e}")




# ==========================================
is_premium_user = False
db_scan_count = 0
user_id = None

if is_authenticated:
    user_id = st.session_state.user_session.user.id
    
    try:
        # Pull un-hackable data records directly from your backend profile table
        res = supabase.table("profiles").select("is_subscribed", "scan_count").eq("id", user_id).maybe_single().execute()
        if res.data:
            is_premium_user = res.data.get("is_subscribed", False)
            db_scan_count = res.data.get("scan_count", 0)
    except Exception as e:
        st.error(f"Subscription Error: {e}")


    # Intercept inbound payment tokens from Stripe
    if "stripe_session_id" in url_params and not is_premium_user:
        with st.spinner("Verifying transaction credentials..."):
            try:
                stripe_session = stripe.checkout.Session.retrieve(url_params["stripe_session_id"])
                if stripe_session.payment_status == "paid":
                    supabase.table("profiles").upsert({
                        "id": user_id, 
                        "is_subscribed": True,
                        "stripe_customer_id": stripe_session.customer
                    }).execute()
                    st.success("Premium account confirmed!")
                    st.query_params.clear() 
                    st.rerun()
            except Exception as e:
                st.error(f"Transaction confirmation fault: {e}")

# 🎟️ THE STRIPE REDIRECT (Triggers if they aren't premium, whether logged in OR anonymous!)
if not is_premium_user:
    st.warning("⚠️ Access Restricted: Premium subscription needed to unlock scanning engine assets.")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url='https://onrender.com?stripe_session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://onrender.com?stripe_session_id={CHECKOUT_SESSION_ID}',
            client_reference_id=user_id if user_id else "anonymous_guest"
        )
        st.link_button("🎟️ Upgrade to Premium Now", session.url, use_container_width=True)
    except Exception as stripe_err:
        st.error(f"Stripe Session Generation Failed: {stripe_err}")

    if is_authenticated:
        if st.sidebar.button("Log Out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user_session = None
            st.rerun()
            
    st.stop()
# ==========================================
# 🚀 RUNTIME SIDEBAR & DASHBOARD DISPLAY
# ==========================================
def get_user_billing_portal_url(uid):
    """Fetches customer ID from Supabase and requests a short-lived Stripe portal session link"""
    try:
        res = supabase.table("profiles").select("stripe_customer_id").eq("id", uid).maybe_single().execute()
        if res.data and res.data.get("stripe_customer_id"):
            cust_id = res.data["stripe_customer_id"]
            portal_session = stripe.billing_portal.Session.create(
                customer=cust_id,
                return_url='https://ai-vision-scanner.onrender.com/'
            )
            return portal_session.url
    except Exception as e:
        pass
    return None

if is_premium_user:
    st.sidebar.subheader("🌟 Premium Account Active")
    st.sidebar.text(f"Logged in: {st.session_state.user_session.user.email}")
    management_url = get_user_billing_portal_url(user_id)
    if management_url:
        st.sidebar.link_button("💳 Manage Subscription", management_url, use_container_width=True)
        
    # 🆕 RENDER PREMIUM HISTORY ACCORDION TIMELINE
    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 Your Saved Scans History")
    try:
        history_res = supabase.table("scans").select("solution_text", "created_at").order("created_at", descending=True).execute()
        if history_res.data:
            for idx, item in enumerate(history_res.data):
                # Format timestamps cleanly into a readable tag header
                timestamp_string = item["created_at"][:10] + " " + item["created_at"][11:16]
                
                # Create dropdown expanders for each historical scan
                with st.sidebar.expander(f"🔍 Scan ({timestamp_string})"):
                    # Slice text preview or show the whole text entry
                    st.write(item["solution_text"])
        else:
            st.sidebar.caption("No previous scans found yet. Take your first snapshot!")
    except Exception:
        pass


# ==========================================
# 🔮 ORIGINAL PIPELINE (YOUR ENGINE, KEEPING gTTS & SPLITTING LOGIC)
# ==========================================
st.write("Snap a photo to instantly see and hear the technical solution.")
client = genai.Client()

@st.cache_data(show_spinner=True)
def generate_solution_and_audio(image_bytes_hash, image_bytes):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            genai.types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
            """
            You are a premium, direct technical problem solver. 
            Analyze the question, formula, or problem visible in this image.
            
            Provide your response in EXACTLY the following format:
            ---VISUAL_START---
            [Provide a clear, brief, incremental step-by-step solution path using markdown format here.]
            ---VISUAL_END---
            ---SPOKEN_START---
            [Provide the exact same solution, but written exclusively for an audio reader. 
            Use simple English sentences. Spell out words instead of symbols. No math symbols, no equations, no markdown, no code blocks.]
            ---SPOKEN_END---
            """
        ]
    )
    
    raw_response = response.text if response.text else ""
    
        # 🎯 Correct array indices added to extract text inside matching tag indicators
    if "---VISUAL_START---" in raw_response and "---VISUAL_END---" in raw_response:
        text_content = raw_response.split("---VISUAL_START---")[1].split("---VISUAL_END---")[0].strip()
    else:
        text_content = raw_response
        
    if "---SPOKEN_START---" in raw_response and "---SPOKEN_END---" in raw_response:
        spoken_text = raw_response.split("---SPOKEN_START---")[1].split("---SPOKEN_END---")[0].strip()
    else:
        spoken_text = text_content


    spoken_text = spoken_text.replace("#", "").replace("*", "").replace("`", "")
    spoken_text = spoken_text.replace("→", " leads to ").replace("=>", " implies ")
    spoken_text = spoken_text.replace("=", " equals ").replace("+", " plus ")
    spoken_text = spoken_text.replace("-", " minus ").replace("/", " divided by ")
    
    spoken_text = "".join(c for c in spoken_text if ord(c) < 128)
    spoken_text = " ".join(spoken_text.split())
    
    if not spoken_text.strip():
        spoken_text = "Analysis complete. Please see the screen for details."

    tts = gTTS(text=spoken_text, lang='en', tld='com')
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_bytes = audio_buffer.getvalue()
    
    return text_content, audio_bytes

captured_image = st.camera_input(" ", key="main_camera_input")

# Ensure state placeholders exist in memory
if "latest_solution_text" not in st.session_state:
    st.session_state.latest_solution_text = None
if "latest_solution_audio" not in st.session_state:
    st.session_state.latest_solution_audio = None

# 4. Trigger Execution Pipeline on Capture
if captured_image is not None:
    # 🛑 THE GATEKEEPER: Stop process if anonymous limit reached and user isn't authenticated
    if not is_authenticated and anon_scans >= FREE_LIMIT:
        st.error("⚠️ Free limit reached. Please sign in or create an account above to process this scan.")
        st.stop()
    raw_bytes = captured_image.getvalue()
    bytes_hash = hashlib.md5(raw_bytes).hexdigest()
    
    with st.spinner("Analyzing problem parameters and rendering vocal tracks..."):
        try:
            # Execute processing core metrics
            solution_text, solution_audio = generate_solution_and_audio(bytes_hash, raw_bytes)
            
            # 💾 STASH RESULTS IN MEMORY BEFORE RERUNNING
            st.session_state.latest_solution_text = solution_text
            st.session_state.latest_solution_audio = solution_audio
            
            # 🔄 TRANSACTION AND UI RE-RENDER HOOK
            if not is_authenticated and allow_anonymous_processing:
                # Advance tracking metrics digits
                anon_scans += 1
                st.session_state.fallback_anon_scans = anon_scans
                if ip_hash:
                    supabase.table("device_tracking").update({"scan_count": anon_scans}).eq("ip_hash", ip_hash).execute()
                if "main_camera_input" in st.session_state:
                    del st.session_state["main_camera_input"]
            
            elif is_authenticated and not is_premium_user:
                db_scan_count += 1
                supabase.table("profiles").update({"scan_count": db_scan_count}).eq("id", user_id).execute()
                
                # 🆕 SAVE LOG TO CLOUD HISTORY FOR FREE REGISTERED USERS
                supabase.table("scans").insert({"user_id": user_id, "solution_text": solution_text}).execute()
                
                if "main_camera_input" in st.session_state:
                    del st.session_state["main_camera_input"]
            
            elif is_authenticated and is_premium_user:
                # 🆕 SAVE LOG TO CLOUD HISTORY FOR PREMIUM USERS
                supabase.table("scans").insert({"user_id": user_id, "solution_text": solution_text}).execute()
                
                if "main_camera_input" in st.session_state:
                    del st.session_state["main_camera_input"]
            
                if not is_authenticated and allow_anonymous_processing:
                    st.session_state.anon_scans = anon_scans
                    local_storage.setItem("anon_scan_count", anon_scans)
    
                # Clear out the photo file buffer seamlessly
                if "main_camera_input" in st.session_state:
                    del st.session_state["main_camera_input"]
            
        except Exception as e:
            st.error(f"Processing Engine Error: {e}")

# ==========================================
# 📺 RENDERING ENGINE (EVERYONE COMES HERE FIRST)
# ==========================================
if st.session_state.latest_solution_text is not None:
    st.markdown("---")
    
    if st.session_state.latest_solution_audio:
        st.subheader("🔊 Listen to Solution:")
        st.audio(st.session_state.latest_solution_audio, format="audio/mp3", autoplay=True)
    
    st.subheader("📝 Visual Text Breakdown:")
    st.markdown(st.session_state.latest_solution_text)
    
    # ⚠️ LIMIT CHECK GATEWAY (MOVED TO BOTTOM BUTTON CONTROL)
    if not is_authenticated and anon_scans >= FREE_LIMIT:
        st.warning("⚠️ You have officially used your free scan!")
        if st.button("Unlock Unlimited Premium Usage Now", use_container_width=True):
            # Clean values out before routing to login gateways on rerun
            st.session_state.latest_solution_text = None
            st.session_state.latest_solution_audio = None
            st.rerun()
    
    # Optional UI Synchronizer Button for earlier scans
    elif not is_authenticated:
        if st.button("🔄 Sync App UI Counter View", use_container_width=True):
            st.rerun()
            
        
