import streamlit as st
from typing import Dict, Any, Optional
import requests

class VideoUploader:
    def __init__(self, api_client):
        self.api_client = api_client
    
    def render_upload_form(self) -> Optional[Dict[str, Any]]:
        """Render video upload form"""
        uploaded_file = st.file_uploader(
            "Choose a video file",
            type=['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'],
            help="Upload educational videos for AI-powered indexing"
        )
        
        if uploaded_file:
            # Show file info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("File Size", f"{uploaded_file.size / (1024*1024):.1f} MB")
            with col2:
                st.metric("File Type", uploaded_file.type)
            
            # Metadata form
            with st.form("upload_form"):
                title = st.text_input("Video Title", value=uploaded_file.name)
                description = st.text_area("Description")
                
                col1, col2 = st.columns(2)
                with col1:
                    subject = st.selectbox("Subject", 
                        ["", "Physics", "Mathematics", "Chemistry", "Biology", "Programming", "Other"])
                with col2:
                    difficulty = st.selectbox("Difficulty", 
                        ["", "Beginner", "Intermediate", "Advanced"])
                
                tags = st.text_input("Tags (comma-separated)")
                
                submit = st.form_submit_button("Upload Video", type="primary")
                
                if submit:
                    return {
                        "file": uploaded_file,
                        "title": title,
                        "description": description,
                        "subject": subject,
                        "difficulty": difficulty,
                        "tags": tags
                    }
        
        return None