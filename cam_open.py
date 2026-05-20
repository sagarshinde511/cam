import cv2
import mediapipe as mp
import requests
import mysql.connector
from datetime import datetime
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode

# --- Streamlit App UI Configuration ---
st.set_page_config(page_title="Motion & Pose Detector", layout="centered")
st.title("🏃‍♂️ Real-Time Motion & Pose Tracking")
st.text("This app detects body poses and syncs status data with your database.")

# --- Configuration Constants ---
API_URL = "https://aeprojecthub.in/Dairy/SwitchUpdateState.php"
DB_CONFIG = {
    'host': "82.180.143.66",
    'user': "u263681140_AttendanceInt",
    'password': "SagarAtten@12345",
    'database': "u263681140_Attendance"
}

# --- Database & API Functions ---
def update_mobile_state(state_value):
    try:
        params = {'state': state_value}
        response = requests.get(API_URL, params=params, timeout=5)
        if response.status_code == 200:
            print(f"Server response: {response.text.strip()}")
        else:
            print(f"HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"Error calling API: {e}")

def insert_motion_start():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = "INSERT INTO MotionDetected (start) VALUES (%s)"
        
        cursor.execute(query, (current_time,))
        conn.commit()
        inserted_id = cursor.lastrowid
        print(f"Database: Inserted start session at {current_time} (ID: {inserted_id})")
        
        cursor.close()
        conn.close()
        return inserted_id
    except Exception as e:
        print(f"Database Error on Insert: {e}")
        return None

def update_motion_end(row_id):
    if row_id is None:
        return
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = "UPDATE MotionDetected SET end = %s WHERE id = %s"
        
        cursor.execute(query, (current_time, row_id))
        conn.commit()
        print(f"Database: Updated end session at {current_time} for ID: {row_id}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database Error on Update: {e}")


# --- Video Processing Callback Class ---
class PoseTransformer(VideoTransformerBase):
    def __init__(self):
        self.motion_active = False
        self.current_session_id = None
        
        # Initialize the Modern MediaPipe Image Landmarker Engine
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        # Pull down the model framework binary directly from Google Storage CDN
        model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
        model_bytes = requests.get(model_url, timeout=10).content
        
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=model_bytes),
            running_mode=VisionRunningMode.IMAGE
        )
        self.landmarker = PoseLandmarker.create_from_options(options)

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Wrap the frame payload into standard MediaPipe Image format
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img)
        detection_result = self.landmarker.detect(mp_image)

        # Process landmarks detection logic
        if detection_result.pose_landmarks:
            cv2.putText(img, "Motion Detected (State: 1)", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Extract tracking points and map them overlaying the frame
            for landmark in detection_result.pose_landmarks[0]:
                x = int(landmark.x * img.shape[1])
                y = int(landmark.y * img.shape[0])
                cv2.circle(img, (x, y), 3, (0, 255, 0), -1)

            # State Logic Transition: Active State Triggered
            if not self.motion_active:
                self.motion_active = True
                update_mobile_state('1')
                self.current_session_id = insert_motion_start()
                
        else:
            cv2.putText(img, "No Motion (State: 0)", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            
            # State Logic Transition: Inactive State Triggered
            if self.motion_active:
                self.motion_active = False
                update_mobile_state('0')
                update_motion_end(self.current_session_id)
                self.current_session_id = None

        return img

    def on_ended(self):
        # Trigger explicit shutdown cleanups when a user terminates the video thread
        if self.motion_active:
            update_mobile_state('0')
            update_motion_end(self.current_session_id)


# --- Streamlit WebRTC Interface Component ---
ctx = webrtc_streamer(
    key="pose-detection",
    mode=WebRtcMode.SENDRECV,
    video_transformer_factory=PoseTransformer,
    
    # Custom Network Routing settings to bypass rigid firewalls or NAT environments
    rtc_configuration={
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302"]},
            # Free, universal public fallback TURN relay server
            {
                "urls": ["turn:openrelay.metered.ca:443"],
                "username": "openrelayproject",
                "credential": "openrelayproject"
            }
        ]
    },
    media_stream_constraints={"video": True, "audio": False},
)

# Render informative interface feedback blocks
if ctx.state.playing:
    st.success("Webcam stream is active. Monitoring for human poses...")
else:
    st.info("Click 'Start' above to open your webcam and start tracking.")
