#!/usr/bin/env python3
import hashlib
import io
import os
import streamlit as st
import stripe
from google import genai
from dotenv import load_dotenv
from gtts import gTTS
from supabase import create_client, Client
import urllib.parse

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
# ==========================================
# 🔄 PRODUCTION MAGIC LINK / PASSWORD RESET INTERCEPTOR
# ==========================================
# Converts the native browser URL hash '#' into a backend-readable '?' query string
st.components.v1.html(
    """
    <script>
    const currentUrl = window.parent.location.href;
    if (currentUrl.includes('#access_token=') || currentUrl.includes('#type=recovery')) {
        const cleanUrl = currentUrl.replace('#', '?');
        window.parent.location.href = cleanUrl;
    }
    </script>
    """,
    height=0,
)

url_params = st.query_params

# Fallback: Extract tokens from raw HTTP referer headers if the JavaScript block is sandboxed
raw_referer_url = st.context.headers.get("referer", "")
inbound_access_token = url_params.get("access_token")
inbound_refresh_token = url_params.get("refresh_token")
is_recovery_mode = url_params.get("type") == "recovery" or "type=recovery" in raw_referer_url

if not inbound_access_token and "#access_token=" in raw_referer_url:
    try:
        parsed_fragment = urllib.parse.urlparse(raw_referer_url).fragment
        fragment_params = urllib.parse.parse_qs(parsed_fragment)
        inbound_access_token = fragment_params.get("access_token", [None])[0]
        inbound_refresh_token = fragment_params.get("refresh_token", [None])[0]
    except Exception:
        pass

# Handoff Session validation to Supabase if an inbound token is detected
if inbound_access_token:
    try:
        response = supabase.auth.set_session(inbound_access_token, inbound_refresh_token or "")
        st.session_state.user_session = response.session
        
        # If it's a password recovery request, route them straight to update panel
        if is_recovery_mode:
            st.session_state.show_password_update = True
            st.success("Recovery token validated! Please update your password below.")
        else:
            st.success("Successfully authenticated!")
        
        # Clean up browser tracking params and refresh the application state
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Authentication failed: {e}")
    st.stop()


# ==========================================
# 📱 STREAMLIT PAGE CONFIG & LAYOUT
# ==========================================
st.set_page_config(page_title="App Authentication Portal", page_icon="🔒", layout="centered")

# Initialize fundamental layout session states
if "user_session" not in st.session_state:
    st.session_state.user_session = None
if "show_password_update" not in st.session_state:
    st.session_state.show_password_update = False


# ==========================================
# 🔑 FORCED PASSWORD UPDATE PANEL (POST-RESET CLICK)
# ==========================================
if st.session_state.show_password_update:
    st.title("🔑 Set New Password")
    st.write("Enter your new secure account password below.")
    
    new_password = st.text_input("New Password", type="password", key="new_password_field")
    confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password_field")
    
    if st.button("Update Password", use_container_width=True):
        if not new_password:
            st.error("Password cannot be blank.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                # Modifies credentials using the active verified session context
                supabase.auth.update_user({"password": new_password})
                st.success("Password updated successfully! You can now access your application.")
                st.session_state.show_password_update = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update password: {e}")
    st.stop()


# ==========================================
# 🛡️ AUTHENTICATION GATEWAY (SIGN IN / SIGN UP / FORGOT)
# ==========================================
if st.session_state.user_session is None:
    st.title("🔒 Access Gateway")
    tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Create Account"])
    
    with tab1:
        if "reset_mode" not in st.session_state:
            st.session_state.reset_mode = False

        if not st.session_state.reset_mode:
            login_email = st.text_input("Email Address", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Log In", use_container_width=True):
                    try:
                        response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_password})
                        st.session_state.user_session = response.session
                        st.success("Access Granted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login Failed: {e}")
            with col2:
                if st.button("Forgot Password?", use_container_width=True):
                    st.session_state.reset_mode = True
                    st.rerun()
        else:
            st.subheader("🔑 Reset Your Password")
            reset_email = st.text_input("Enter your account email", key="reset_email")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Send Reset Link", use_container_width=True):
                    try:
                        # Triggers an explicit recovery email link route
                        # Note: Ensure the landing page domain is whitelisted in Supabase Dashboard -> Auth
                        supabase.auth.reset_password_for_email(reset_email)
                        st.success("Password reset email dispatched! Click the link inside to modify your password.")
                    except Exception as e:
                        st.error(f"Error sending link: {e}")
            with col2:
                if st.button("Back to Login", use_container_width=True):
                    st.session_state.reset_mode = False
                    st.rerun()
                
    with tab2:
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Sign Up", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                st.success("Account created successfully! Check your email inbox for a confirmation link, then Sign In.")
            except Exception as e:
                st.error(f"Registration Error: {e}")
    st.stop()


# ==========================================
# 🚀 PROTECTED APPLICATION HOME (AUTHENTICATED ONLY)
# ==========================================
# Track active user properties globally below this boundary
user_email = st.session_state.user_session.user.email

st.title("🎉 Welcome to the Secure App Room")
st.write(f"Hello, **{user_email}**! You have cleared security validation.")

# Sidebar Controls
st.sidebar.subheader("Account Session")
st.sidebar.text(f"Logged in: {user_email}")

if st.sidebar.button("Log Out", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.user_session = None
    st.session_state.show_password_update = False
    st.rerun()

# --- PLACE YOUR CORE PROTECTED APPLICATION CODE BELOW HERE ---
st.info("💡 Drop your functional application tools right here inside this protected workspace frame.")


# ==========================================
# 💳 GATEWAY 2: STRIPE PAYWALL GATEKEEPER
# ==========================================
def check_active_subscription(uid):
    """Queries the profiles table to see if user has access"""
    try:
        res = supabase.table("profiles").select("is_subscribed").eq("id", uid).maybe_single().execute()
        if res.data and res.data.get("is_subscribed") == True:
            return True
    except Exception:
        pass
    return False

def generate_stripe_checkout(uid):
    """Generates a secure checkout link custom mapped to the user ID"""
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price': stripe_price_id, 'quantity': 1}],
        mode='subscription',
        success_url='https://aivisionscanner-ijwbtsdtyhpi39pap32sst.streamlit.app/?stripe_session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://aivisionscanner-ijwbtsdtyhpi39pap32sst.streamlit.app/',
        client_reference_id=uid
    )
    return session.url

# Read active payment metadata state
is_premium_user = check_active_subscription(user_id)

# Intercept inbound payment tokens from Stripe
if "stripe_session_id" in url_params and not is_premium_user:
    with st.spinner("Verifying transaction credentials..."):
        try:
            stripe_session = stripe.checkout.Session.retrieve(url_params["stripe_session_id"])
            if stripe_session.payment_status == "paid":
                cust_id = stripe_session.customer
                
                # Record both active premium clearance and the Customer ID in your profile row
                supabase.table("profiles").upsert({
                    "id": user_id, 
                    "is_subscribed": True,
                    "stripe_customer_id": cust_id
                }).execute()
                
                st.success("Premium account confirmed!")
                st.query_params.clear() 
                st.rerun()
        except Exception as e:
            st.error(f"Transaction confirmation fault: {e}")

# If they aren't premium, lock down the camera widget and display the pricing link
if not is_premium_user:
    st.warning("⚠️ Access Restricted: Premium subscription needed to unlock scanning engine assets.")
    checkout_url = generate_stripe_checkout(user_id)
    st.link_button("🎟️ Upgrade to Premium Now", checkout_url, use_container_width=True)
    
    if st.sidebar.button("Log Out", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user_session = None
        st.rerun()
    st.stop()

# ==========================================
# 🚀 CORE APPLICATION PIPELINE (PREMIUM USERS ONLY)
# ==========================================
def get_user_billing_portal_url(uid):
    """Fetches customer ID from Supabase and requests a short-lived Stripe portal session link"""
    try:
        res = supabase.table("profiles").select("stripe_customer_id").eq("id", uid).maybe_single().execute()
        if res.data and res.data.get("stripe_customer_id"):
            cust_id = res.data["stripe_customer_id"]
            portal_session = stripe.billing_portal.Session.create(
                customer=cust_id,
                return_url='https://aivisionscanner-ijwbtsdtyhpi39pap32sst.streamlit.app/'
            )
            return portal_session.url
    except Exception as e:
        pass
    return None

st.sidebar.subheader("Premium Account Active")
st.sidebar.text(f"Logged in: {st.session_state.user_session.user.email}")

# Generate the portal url reactively
management_url = get_user_billing_portal_url(user_id)
if management_url:
    st.sidebar.link_button("💳 Manage Subscription", management_url, use_container_width=True)
else:
    st.sidebar.caption("Billing sync pending next transaction cycle.")

if st.sidebar.button("Log Out", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.user_session = None
    st.rerun()
    
st.write("Snap a photo to instantly see and hear the technical solution.")

# Initialize the Gemini client (automatically inherits GEMINI_API_KEY from .env)
client = genai.Client()

# 2. Optimized Pipeline with Smart Image Caching
@st.cache_data(show_spinner=False)
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

# 3. Native Mobile Camera Input Widget
captured_image = st.camera_input(" ")

# 4. Trigger Execution Pipeline on Capture
if captured_image is not None:
    raw_bytes = captured_image.getvalue()
    bytes_hash = hashlib.md5(raw_bytes).hexdigest()
    
    with st.spinner("Analyzing problem parameters and rendering vocal tracks..."):
        try:
            solution_text, solution_audio = generate_solution_and_audio(bytes_hash, raw_bytes)
            st.markdown("---")
            
            if solution_audio:
                st.subheader("🔊 Listen to Solution:")
                st.audio(solution_audio, format="audio/mp3")
            
            st.subheader("📝 Visual Text Breakdown:")
            st.markdown(solution_text)
            
        except Exception as e:
            st.error(f"Processing Engine Error: {e}")
