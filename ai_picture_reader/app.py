#!/usr/bin/env python3
import cv2
from google import genai
import os
from dotenv import load_dotenv
import threading

# Global flag to prevent sending multiple overlapping requests if space is spammed
is_analyzing = False

def send_to_gemini(client, image_bytes):
    """This function runs entirely in the background so the UI doesn't freeze."""
    global is_analyzing
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                genai.types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg',
                ),
                "Describe what you see in this photo clearly and concisely."
            ]
        )
        print("\n=== Gemini AI Analysis ===")
        print(response.text)
        print("==========================\n")
        print("-> Press [SPACEBAR] to take another photo, or [ESC] to quit.")
    except Exception as e:
        print(f"\nAn error occurred during AI analysis: {e}")
    finally:
        # Re-enable the button once the background job finishes
        is_analyzing = False

def main():
    global is_analyzing
    load_dotenv()
    
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Error initializing Gemini Client. Check .env file. \nDetails: {e}")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open the webcam.")
        return

    print("\n=== Multi-Threaded Webcam App Started ===")
    print("-> Press [SPACEBAR] to Take Photo (Feed will stay smooth!).")
    print("-> Press [ESC] or 'q' to Quit.")

    # Forces macOS to cycle UI events properly on startup
    cv2.startWindowThread()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        display_frame = frame.copy()
        
        # Change overlay text based on background system state
        if is_analyzing:
            cv2.putText(display_frame, "AI is thinking... Feed is live!", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(display_frame, "Space: Take Photo | ESC: Quit", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Live Webcam Feed', display_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord('q'):
            print("Closing application...")
            break

        elif key == 32:
            if is_analyzing:
                print("[!] Still waiting for the last response. Hold on!")
                continue

            print("\n[!] Photo captured! Processing in background...")
            is_analyzing = True
            
            # Encode image to bytes
            success, encoded_image = cv2.imencode('.jpg', frame)
            if not success:
                print("Failed to process image matrix.")
                is_analyzing = False
                continue
            image_bytes = encoded_image.tobytes()

            # Launch the network call on a separate background thread
            threading.Thread(target=send_to_gemini, args=(client, image_bytes), daemon=True).start()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
