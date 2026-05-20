import cv2
import mediapipe as mp
import requests
import mysql.connector
from datetime import datetime
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode

# Streamlit App UI Configuration
st.set_page_config(page_title="Motion & Pose Detector", layout="centered")
st.title("🏃‍♂️ Real-Time Motion & Pose Tracking")
st.text("This app detects body poses, draws landmarks, and syncs status data with your database.")

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Configuration Constants
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


# --- Video Processing Class ---
class PoseTransformer(VideoTransformerBase):
    def __init__(self):
        # We use instance variables to track states across continuous video frames
        self.motion_active = False
        self.current_session_id = None

    def transform(self, frame):
        # Convert streamlit-webrtc frame format to a usable OpenCV BGR image
        img = frame.to_ndarray(format="bgr24")

        # MediaPipe processing
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = pose.process(image_rgb)
        image_rgb.flags.writeable = True

        # Handle landmarks and state state toggles
        if results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )
            cv2.putText(img, "Motion Detected (State: 1)", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Transition: Changed from NO motion to MOTION detected
            if not self.motion_active:
                self.motion_active = True
                update_mobile_state('1')
                self.current_session_id = insert_motion_start()
                
        else:
            cv2.putText(img, "No Motion (State: 0)", (10, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            
            # Transition: Changed from MOTION to NO motion detected
            if self.motion_active:
                self.motion_active = False
                update_mobile_state('0')
                update_motion_end(self.current_session_id)
                self.current_session_id = None

        return img

    def on_ended(self):
        """ Cleans up and clears database flags when user stops the stream """
        if self.motion_active:
            update_mobile_state('0')
            update_motion_end(self.current_session_id)


# --- Streamlit WebRTC Interface ---
ctx = webrtc_streamer(
    key="pose-detection",
    mode=WebRtcMode.SENDRECV,
    video_transformer_factory=PoseTransformer,
    rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
    media_stream_constraints={"video": True, "audio": False},
)

# Optional UI status indicators below the feed
if ctx.state.playing:
    st.success("Webcam stream is active. Monitoring for human poses...")
else:
    st.info("Click 'Start' above to open your webcam and start tracking.")
