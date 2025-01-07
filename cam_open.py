import streamlit as st

# Title for the app
st.title("Camera Access Example")

# Access camera input
camera_image = st.camera_input("Take a picture")

# If a picture is taken, display it
if camera_image:
    st.image(camera_image, caption="Captured Image", use_column_width=True)
