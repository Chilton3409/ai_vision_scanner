AI Mode Conversation: i need to build reusable templates for login and password reset using python and supabasei need to build reusable templates for login and password reset using python and supabaseHere is a reusable, modular implementation for a Supabase authentication backend workflow in Python. It provides cleanly structured, production-ready templates for handling login, registration, and user-initiated password resets.This backend-agnostic layout uses supabase-py and works smoothly across Python web frameworks (such as FastAPI, Flask, or Streamlit).🛠️ 1. Project SetupFirst, make sure you have the official Supabase Python Client library installed:bashpip install supabase
Use code with caution.📂 2. Reusable Auth Manager (auth_manager.py)This class abstracts away the boilerplate logic for authentication, tokens, and errors. You can import this single manager into any of your app routes.pythonimport os
from typing import Dict, Any, Optional
from supabase import create_client, Client
from gotrue.errors import AuthApiError

class SupabaseAuthManager:
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initializes the client using provided credentials or fallback environment variables."""
        url = supabase_url or os.environ.get("SUPABASE_URL")
        key = supabase_key or os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL and API Key must be provided or set as environment variables.")
            
        self.supabase: Client = create_client(url, key)

    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Registers a new user. Handles email verification requirements based on project settings."""
        try:
            response = self.supabase.auth.sign_up({"email": email, "password": password})
            return {"success": True, "data": response.user, "error": None}
        except AuthApiError as e:
            return {"success": False, "data": None, "error": e.message}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticates a user with email and password, returning a valid session token."""
        try:
            response = self.supabase.supabase.auth.sign_in_with_password({"email": email, "password": password})
            return {"success": True, "session": response.session, "user": response.user, "error": None}
        except AuthApiError as e:
            return {"success": False, "session": None, "user": None, "error": e.message}

    def request_password_reset(self, email: str, redirect_url: str) -> Dict[str, Any]:
        """
        Triggers a reset link email. 
        redirect_url must be whitelisted in your Supabase Auth > Redirect URLs panel.
        """
        try:
            # Sends the recovery magic link or OTP token depending on project configuration
            self.supabase.auth.reset_password_for_email(email, options={"redirect_to": redirect_url})
            return {"success": True, "message": "Password reset link sent to email.", "error": None}
        except AuthApiError as e:
            return {"success": False, "message": None, "error": e.message}

    def update_password(self, access_token: str, new_password: str) -> Dict[str, Any]:
        """
        Updates the authenticated user's password using the active session token
        extracted from the redirect callback fragment.
        """
        try:
            # Set the active user session context via the access token before updating
            self.supabase.auth.set_session(access_token, "") 
            response = self.supabase.auth.update_user({"password": new_password})
            return {"success": True, "user": response.user, "error": None}
        except AuthApiError as e:
            return {"success": False, "user": None, "error": e.message}

    def logout(self) -> None:
        """Signs out the current user session context."""
        try:
            self.supabase.auth.sign_out()
        except AuthApiError:
            pass
Use code with caution.📝 3. Executable Implementation Example (app.py)This snippet demonstrates how you can safely hook the reusable auth templates into your functional code:pythonimport os
from auth_manager import SupabaseAuthManager

# Ensure your credentials are loaded safely
os.environ["SUPABASE_URL"] = "https://supabase.co"
os.environ["SUPABASE_KEY"] = "your-anon-public-key"

# Instantiate your modular auth template
auth = SupabaseAuthManager()

# --- 1. USER REGISTRATION & LOGIN FLOW ---
print("--- Testing Registration ---")
reg_result = auth.register("nate@example.com", "SecurePassword123!")
print(f"Register status: {reg_result['success']} | Error: {reg_result['error']}")

print("\n--- Testing Login ---")
login_result = auth.login("nate@example.com", "SecurePassword123!")
if login_result["success"]:
    print(f"Logged in successfully! User ID: {login_result['user'].id}")
else:
    print(f"Login failed: {login_result['error']}")


# --- 2. PASSWORD RESET FLOW (2 STEPS) ---
print("\n--- Step 1: Initiating Forgot Password ---")
# The URL where your app listens for password modifications
callback_url = "https://your-frontend-app.com" 
reset_req = auth.request_password_reset("nate@example.com", redirect_url=callback_url)
print(f"Reset Link Sent: {reset_req['success']} | Error: {reset_req['error']}")

print("\n--- Step 2: Completing Password Reset Callback ---")
# When the user clicks the link, they arrive at your callback URL.
# Your frontend app needs to grab the `#access_token=...` parameter directly from the URL fragment.
extracted_token = "user-access-token-from-url-hash-fragment"

new_pass_result = auth.update_password(extracted_token, "BrandNewSecurePassword456!")
if new_pass_result["success"]:
    print("Password successfully updated! The user can now log in using their new credentials.")
else:
    print(f"Password update failed: {new_pass_result['error']}")
Use code with caution.⚠️ Crucial Supabase ConfigurationsFor the password reset template to function completely, make sure to adjust these settings inside your Supabase Dashboard:Whitelisting Redirects: Navigate to Authentication > URL Configuration and add your specific frontend reset path (e.g., https://your-frontend-app.com) into the Redirect URLs input field.Handling Hash Fragments: When Supabase routes a user back to your app after an email click, it attaches parameters as an anchor/hash fragment (#access_token=...&type=recovery) rather than standard URL search parameters. Ensure your client code pulls variables from the location hash context.Would you like me to tailor this python template for a specific framework context? I can:Wrap it in a FastAPI backend API blueprint with secure route dependency validation.Integrate it natively inside an interactive Streamlit frontend interface using standard session state tracking.Let me know the number or preference you'd like to dive into!Try without personalizationRedditFastAPI + Supabase Auth Template : r/Python - Redditcursor_rik FastAPI + Supabase Auth Template Showcase What My Project Does This is a FastAPI + Supabase authentication template tha...SupabasePython: Send a password reset request | Supabase DocsThe password reset flow consists of 2 broad steps: Update the user's password. You can configure the URL that the user is redirect...GitHubGitHub - hpohlmann/supabase-api-scaffolding-template: Production-ready FastAPI authentication API template with Supabase integration. Features email/password auth, Google OAuth (PKCE), JWT validation, and Google Secret Manager support. Perfect scaffolding for modern web applications requiring secure user authentication.Supabase integration. Features email/password auth, Google OAuth (PKCE), Perfect scaffolding for modern web applications requiring...Show allYou sent: mobile_app.py and said: i am wanting to use it on this and removeeverythingmobile_app.pyi am wanting to use it on this and removeeverythingHere is your cleaned-up Streamlit application template. All Stripe paywall components, billing pathways, and Gemini AI processing features have been completely removed.The application now functions strictly as a reusable Authentication & Password Management Gateway built directly on top of your existing Supabase configurations.python#!/usr/bin/env python3
import os
import streamlit as st
import urllib.parse
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables securely from .env file
load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

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
Use code with caution.Would you like me to add any specific dashboard logic next? I can:Initialize an authenticated user profile panel to store custom metadata in your database.Build a Streamlit form element to insert input metrics into a protected Supabase table.Let me know the option number or describe what you want to construct in the dashboard context!Try without personalizationYou sent: mobile_app.py and said: so the reset password will work now 000mobile_app.pyso the reset password will work now 000No, the password reset in your current script will not let users change their password.Your current script uses supabase.auth.sign_in_with_otp(), which simply emails a Magic Login Link to log the user right back into their old account session. If they forgot their password, they still won't know it next time they try to log in normally.To make an actual password reset work so users can type a brand new password, your script needs two things:Use supabase.auth.reset_password_for_email() to send a proper password recovery link.Intercept the inbound type=recovery URL parameters and show a password update input form.Here is your complete, updated code with the proper password reset workflows safely integrated alongside your camera, Stripe paywall, and Gemini AI pipeline:python#!/usr/bin/env python3
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
# 🔄 PRODUCTION MAGIC LINK & RECOVERY INTERCEPTOR
# ==========================================
# JavaScript Engine: Converts the native browser URL hash '#' into a backend-readable '?' query string
st.components.v1.html(
    """
    <script>
    const currentUrl = window.parent.location.href;
    if (currentUrl.includes('#access_token=') || currentUrl.includes('#type=recovery') || currentUrl.includes('#type=magiclink')) {
        const cleanUrl = currentUrl.replace('#', '?');
        window.parent.location.href = cleanUrl;
    }
    </script>
    """,
    height=0,
)

url_params = st.query_params

# Native Fallback: Directly extract tokens from raw HTTP referer headers if the JavaScript block is sandboxed
raw_referer_url = st.context.headers.get("referer", "")
inbound_access_token = url_params.get("access_token")
inbound_refresh_token = url_params.get("refresh_token")
is_magic_link = url_params.get("type") == "magiclink"
is_recovery_mode = url_params.get("type") == "recovery" or "type=recovery" in raw_referer_url

if not inbound_access_token and "#access_token=" in raw_referer_url:
    try:
        parsed_fragment = urllib.parse.urlparse(raw_referer_url).fragment
        fragment_params = urllib.parse.parse_qs(parsed_fragment)
        inbound_access_token = fragment_params.get("access_token", [None])[0]
        inbound_refresh_token = fragment_params.get("refresh_token", [None])[0]
        if "type=recovery" in parsed_fragment:
            is_recovery_mode = True
    except Exception:
        pass

# Handoff Session validation to Supabase if an inbound token is detected
if inbound_access_token:
    try:
        response = supabase.auth.set_session(inbound_access_token, inbound_refresh_token or "")
        st.session_state.user_session = response.session
        
        if is_recovery_mode:
            st.session_state.show_password_update = True
            st.success("Recovery token validated! Please set your new password below.")
        else:
            st.success("Successfully authenticated!")
        
        # Clean up browser tracking params and refresh the application state
        st.query_params.clear()
        if "reset_mode" in st.session_state:
            st.session_state.reset_mode = False
        st.rerun()
    except Exception as e:
        st.error(f"Authentication failed: {e}")
    st.stop()


# ==========================================
# 📱 STREAMLIT PAGE CONFIG & MOBILE STYLING
# ==========================================
st.set_page_config(page_title="AI Talk & Solve Scanner", page_icon="🔊", layout="centered")
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

st.title("🔊 Talk & Solve Scanner")

# Initialize password update system states
if "user_session" not in st.session_state:
    st.session_state.user_session = None
if "show_password_update" not in st.session_state:
    st.session_state.show_password_update = False


# ==========================================
# 🔑 FORCED PASSWORD UPDATE PANEL (POST-RESET CLICK)
# ==========================================
if st.session_state.show_password_update:
    st.subheader("🔑 Set New Password")
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
                # Modifies credentials using the active verified token session context
                supabase.auth.update_user({"password": new_password})
                st.success("Password updated successfully!")
                st.session_state.show_password_update = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update password: {e}")
    st.stop()


# ==========================================
# 🛡️ GATEWAY 1: SUPABASE AUTHENTICATION
# ==========================================
if st.session_state.user_session is None:
    st.write("Please sign in or create an account to unlock the Scanner.")
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
                        # Triggers an explicit recovery email path rather than just an OTP log-in link
                        supabase.auth.reset_password_for_email(reset_email)
                        st.success("Password reset email sent! Click the link in your email to change your password.")
                    except Exception as e:
                        st.error(f"Error: {e}")
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

# Track active user properties globally below this boundary
user_id = st.session_state.user_session.user.id
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
