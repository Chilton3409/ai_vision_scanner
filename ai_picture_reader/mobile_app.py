#!/usr/bin/env python3
import hashlib
import io
import streamlit as st
from google import genai
from dotenv import load_dotenv
from gtts import gTTS

# 1. Page Configuration for Clean Mobile Display
st.set_page_config(
    page_title="AI Talk & Solve Scanner", 
    page_icon="🔊", 
    layout="centered"
)

st.title("🔊 Talk & Solve Scanner")
st.write("Snap a photo to instantly see and hear the technical solution.")

# Load your environment variables securely from the .env file
load_dotenv()
# Initialize the client (automatically inherits GEMINI_API_KEY from .env)
client = genai.Client()
# 2. Optimized Pipeline with Smart Image Caching
@st.cache_data(show_spinner=False)
def generate_solution_and_audio(image_bytes_hash, image_bytes):
    """
    Processes image via Gemini Flash, then runs local text-to-speech conversion.
    Returns both clean markdown text and raw audio bytes.
    """
    
    
    # Stable multimodal cloud call
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            genai.types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
            """
            You are a premium, direct technical problem solver. 
            Analyze the question, formula, or code bug visible in this image.
            Provide a clear, brief, incremental step-by-step solution path. 
            Keep it highly concise so it reads beautifully when spoken aloud.
            """
        ]
    )
    
    text_content = response.text
    
    # Clean up formatting symbols so the audio reader doesn't say "hash hash" out loud
    spoken_text = text_content.replace("#", "").replace("*", "").replace("`", "")
    
    # Convert text to audio bytes entirely in-memory using an IO buffer stream
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
    
    # Unique signature prevents duplicate billing costs on accidental page re-runs
    bytes_hash = hashlib.md5(raw_bytes).hexdigest()
    
    with st.spinner("Analyzing problem parameters and rendering vocal tracks..."):
        try:
            solution_text, solution_audio = generate_solution_and_audio(bytes_hash, raw_bytes)
            
            st.markdown("---")
            
            # 5. Render Native Audio Widget at the top for immediate access
            if solution_audio:
                st.subheader("🔊 Listen to Solution:")
                st.audio(solution_audio, format="audio/mp3")
            
            # 6. Render Structured Text Sheet below it
            st.subheader("📝 Visual Text Breakdown:")
            st.markdown(solution_text)
            
        except Exception as e:
            st.error(f"Processing Engine Error: {e}")
