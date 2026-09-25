import os
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse, RedirectResponse
from supabase import create_client, Client
import config
from fastapi import Request
import stripe
import hashlib
import io
from fastapi import UploadFile, File, Depends
from fastapi.responses import Response
from google import genai
from google.genai import types
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load variables out of the local .env workspace file
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL", "http://localhost:8000")
# Setup your stripe keys directly from our verified config loader
stripe.api_key = os.environ.get("STRIPE_SANDBOX_API_KEY")
stripe_price_id = os.environ.get("STRIPE_PRICE_ID")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing critical Supabase environment configurations.")

app = FastAPI(title="AI Scanner Backend API Engine")
# Allow your local html mock file pages to communicate securely with your API routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows testing entries from any local path structure
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize the Gemini Client (automatically pulls GEMINI_API_KEY from your .env)
client = genai.Client()

# A simple in-memory dictionary cache to mimic Streamlit's @st.cache_data asset scaling
SOLUTION_CACHE = {}
# Initialize the Supabase client safely outside the routing pathways
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

@app.get("/")
def root():
    """Health check endpoint to ensure server is live on Render."""
    return {"status": "online", "application": "AI Scanner API"}


# ==========================================
# 🔑 AUTHENTICATION ENDPOINTS
# ==========================================

@app.post("/auth/register")
def register_user(email: str, password: str):
    """Registers a new account. Handles onboarding validation rules natively."""
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        return {"success": True, "message": "Verification link sent to email inbox."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login_user(email: str, password: str):
    """Verifies user credentials and generates a stable session token."""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return {
            "success": True,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user_id": response.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login invalid: {str(e)}")


# ==========================================
# 🔄 PASSWORD RESET FLOW (NO MORE CHECKING BLOCKS!)
# ==========================================

@app.post("/auth/forgot-password")
def trigger_password_reset(email: str):
    """
    Sends a true recovery link containing routing parameters 
    directed straight to our callback handler.
    """
    try:
        redirect_target = f"{config.RENDER_BASE_URL}/auth/callback"
        supabase.auth.reset_password_for_email(email, options={"redirect_to": redirect_target})
        return {"success": True, "message": "Password recovery email dispatched."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/callback")
def authentication_callback(
    access_token: str = Query(None), 
    refresh_token: str = Query(None),
    type: str = Query(None)
):
    """
    Supabase sends users here. Because FastAPI uses dedicated routes, 
    we instantly know if they clicked a password reset link without checking state variables!
    """
    if type == "recovery" or access_token:
        # Redirect the user smoothly to a clean, isolated input form endpoint
        # Passing the token as query variables so the next screen can read it
        update_url = f"/update-password?access_token={access_token}"
        return RedirectResponse(url=update_url)
    
    return RedirectResponse(url="/")


@app.post("/auth/update-password")
def complete_password_reset(access_token: str, new_password: str):
    """Updates the user's password securely using their verified recovery context token."""
    try:
        # Pass the access token into Supabase to authorize this specific request context
        supabase.auth.set_session(access_token, "")
        supabase.auth.update_user({"password": new_password})
        return {"success": True, "message": "Password updated securely. You can now login normally."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update password: {str(e)}")
# Helper tool to protect your core scanner routes
async def is_premium_user(user_id: str) -> bool:
    """Queries the profiles table manually to see if user has access"""
    try:
        res = supabase.table("profiles").select("is_subscribed").eq("id", user_id).maybe_single().execute()
        if res.data and res.data.get("is_subscribed") == True:
            return True
    except Exception:
        pass
    return False


# ==========================================
# 💳 DIRECT PAYMENT MANAGEMENT ROUTES
# ==========================================

@app.get("/billing/checkout")
def generate_stripe_checkout(user_id: str):
    """Generates a secure checkout link custom mapped to the active user ID"""
    try:
        # Build the return route pointing back to your direct verification route below
        success_target = f"{config.RENDER_BASE_URL}/billing/verify?stripe_session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}"
        cancel_target = f"{config.RENDER_BASE_URL}/"

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url=success_target,
            cancel_url=cancel_target,
            client_reference_id=user_id
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/billing/verify")
def verify_stripe_payment(stripe_session_id: str, user_id: str):
    """
    Your manual verification loop. Intercepts incoming session tokens,
    validates payment with Stripe, and upserts your database row.
    """
    try:
        # Retrieve the transaction details straight from the Stripe API
        stripe_session = stripe.checkout.Session.retrieve(stripe_session_id)
        
        if stripe_session.payment_status == "paid":
            cust_id = stripe_session.customer
            
            # Record both active premium clearance and the Customer ID in your profile row
            supabase.table("profiles").upsert({
                "id": user_id, 
                "is_subscribed": True,
                "stripe_customer_id": cust_id
            }).execute()
            
            # Smoothly redirect the user back to the application homepage after saving
            return RedirectResponse(url="/?payment=confirmed")
            
        raise HTTPException(status_code=400, detail="Transaction not completed successfully.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transaction fault: {str(e)}")


@app.get("/billing/portal")
def get_user_billing_portal(user_id: str):
    """Fetches customer ID from Supabase and requests a short-lived Stripe portal session link"""
    try:
        res = supabase.table("profiles").select("stripe_customer_id").eq("id", user_id).maybe_single().execute()
        if res.data and res.data.get("stripe_customer_id"):
            cust_id = res.data["stripe_customer_id"]
            
            portal_session = stripe.billing_portal.Session.create(
                customer=cust_id,
                return_url=f"{config.RENDER_BASE_URL}/"
            )
            return {"portal_url": portal_session.url}
            
        raise HTTPException(status_code=404, detail="No active billing profiles found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/scanner/solve")
async def process_image_problem(
    user_id: str, 
    file: UploadFile = File(...)
):
    """
    Accepts image file uploads, verifies the user's premium row context status,
    processes via Gemini, and compiles accompanying vocal tracks.
    """
    # 1. Enforce premium lock boundary using our direct verification helper tool
    premium_clearance = await is_premium_user(user_id)
    if not premium_clearance:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access Restricted: Premium subscription required."
        )

    # 2. Read file contents and create a hash string to handle smart query caching
    image_bytes = await file.read()
    bytes_hash = hashlib.md5(image_bytes).hexdigest()

    # 3. Memory cache bypass check to prevent repeating costly AI engine cycles
    if bytes_hash in SOLUTION_CACHE:
        return SOLUTION_CACHE[bytes_hash]

    try:
        # 4. Fire the image content directly to the Gemini 2.5 Flash model API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
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

        # 5. Safe, production-grade split extraction logic isolates your text strings cleanly
        if "---VISUAL_START---" in raw_response and "---VISUAL_END---" in raw_response:
            text_content = raw_response.split("---VISUAL_START---")[1].split("---VISUAL_END---")[0].strip()
        else:
            text_content = raw_response
            
        if "---SPOKEN_START---" in raw_response and "---SPOKEN_END---" in raw_response:
            spoken_text = raw_response.split("---SPOKEN_START---")[1].split("---SPOKEN_END---")[0].strip()
        else:
            spoken_text = text_content

        # Clean vocal metrics so the text reader sounds completely natural
        spoken_text = spoken_text.replace("#", "").replace("*", "").replace("`", "")
        spoken_text = spoken_text.replace("→", " leads to ").replace("=>", " implies ")
        spoken_text = spoken_text.replace("=", " equals ").replace("+", " plus ")
        spoken_text = spoken_text.replace("-", " minus ").replace("/", " divided by ")
        spoken_text = "".join(c for c in spoken_text if ord(c) < 128)
        spoken_text = " ".join(spoken_text.split())

        if not spoken_text.strip():
            spoken_text = "Analysis complete. Please view the dashboard screen details."

        # 6. Render the audio stream using Google Text-to-Speech
        tts = gTTS(text=spoken_text, lang='en', tld='com')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        
        # In a real API deployment framework, you can save this file path or return data strings.
        # For simplicity, we convert to a basic text response format, but you can build audio outputs here.
        payload_result = {
            "solution_text": text_content,
            "spoken_transcript": spoken_text,
            "cache_id": bytes_hash
        }

        # Save to local application cache layer memory array bucket
        SOLUTION_CACHE[bytes_hash] = payload_result
        return payload_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing engine error: {str(e)}")
    
# ==========================================
# 🔊 AUDIO DELIVERY ROUTE
# ==========================================
@app.get("/scanner/audio/{cache_id}")
async def get_solution_audio(cache_id: str):
    """
    Retrieves the generated vocal binary tracks from the solution cache
    and streams them down to the browser player.
    """
    if cache_id not in SOLUTION_CACHE:
        raise HTTPException(status_code=404, detail="Audio track signature expired or not found.")
        
    try:
        # Re-run the solution audio generation based on the cached spoken text transcript
        spoken_text = SOLUTION_CACHE[cache_id]["spoken_transcript"]
        
        tts = gTTS(text=spoken_text, lang='en', tld='com')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_bytes = audio_buffer.getvalue()
        
        # Return a native streaming binary response configured for audio media players
        return Response(content=audio_bytes, media_type="audio/mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio rendering engine fault: {str(e)}")