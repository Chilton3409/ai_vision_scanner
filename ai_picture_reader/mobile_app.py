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
    Processes image via Gemini Flash, splits the output into visual and spoken payloads,
    and converts the filtered text to audio.
    """
    # Stable multimodal cloud call using global client
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
    
    # 1. Parse and extract the two distinct payloads
    if "---VISUAL_START---" in raw_response and "---VISUAL_END---" in raw_response:
        text_content = raw_response.split("---VISUAL_START---")[1].split("---VISUAL_END---")[0].strip()
    else:
        text_content = raw_response  # Fallback if parsing fails
        
    if "---SPOKEN_START---" in raw_response and "---SPOKEN_END---" in raw_response:
        spoken_text = raw_response.split("---SPOKEN_START---")[1].split("---SPOKEN_END---")[0].strip()
    else:
        spoken_text = text_content  # Fallback if parsing fails

    # 2. Heavy-Duty Character Filter for the TTS Audio Engine
    # Force replace common culprits that break gTTS
    spoken_text = spoken_text.replace("#", "").replace("*", "").replace("`", "")
    spoken_text = spoken_text.replace("→", " leads to ").replace("=>", " implies ")
    spoken_text = spoken_text.replace("=", " equals ").replace("+", " plus ")
    spoken_text = spoken_text.replace("-", " minus ").replace("/", " divided by ")
    
    # Strip any remaining non-ASCII characters or strange math symbols entirely
    spoken_text = "".join(c for c in spoken_text if ord(c) < 128)
    
    # Flatten spaces and line breaks for natural speech delivery
    spoken_text = " ".join(spoken_text.split())
    
    if not spoken_text.strip():
        spoken_text = "Analysis complete. Please see the screen for details."

    # 3. Convert clean text to audio bytes in-memory
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
