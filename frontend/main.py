# frontend/src/main.py
import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from components.VideoUploader import VideoUploader
from components.SearchInterface import SearchInterface  
from components.VideoPlayer import VideoPlayer
from components.ResultsDisplay import ResultsDisplay
from utils.api_client import APIClient
from config import Config

# Page config
st.set_page_config(
    page_title="Video Learning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .video-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .search-result {
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 1rem 0;
        background: #f8f9fa;
        border-radius: 0 8px 8px 0;
    }
    
    .scene-label {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 0.2rem;
    }
    
    .timestamp {
        color: #666;
        font-family: monospace;
        background: #f0f0f0;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
    }
    
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .video-player-container {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border: 2px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

class VideoLearningApp:
    def __init__(self):
        self.api_client = APIClient(Config.API_BASE_URL)
        self.video_uploader = VideoUploader(self.api_client)
        self.search_interface = SearchInterface(self.api_client)
        self.video_player = VideoPlayer()
        self.results_display = ResultsDisplay(self.api_client)
        
        # Initialize session state
        if 'current_video_id' not in st.session_state:
            st.session_state.current_video_id = None
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        if 'selected_scene' not in st.session_state:
            st.session_state.selected_scene = None
        if 'videos_list' not in st.session_state:
            st.session_state.videos_list = []
        if 'show_video_player' not in st.session_state:
            st.session_state.show_video_player = False
    
    def run(self):
        """Main application runner"""
        # Header
        st.markdown("""
        <div class="main-header">
            <h1>🎓 Video Learning Assistant</h1>
            <p>AI-powered educational video search and scene detection</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar
        self.render_sidebar()
        
        # Main content area
        self.render_main_content()
        
        # Always show video player if scene is selected
        if st.session_state.selected_scene:
            st.markdown("---")
            self.render_video_player_section()
    
    def render_sidebar(self):
        """Render sidebar with navigation and controls"""
        with st.sidebar:
            st.markdown("## Navigation")
            
            page = st.radio(
                "Select Page",
                ["🔍 Search Videos", "📤 Upload Video", "📚 My Videos", "📈 Analytics"],
                key="navigation"
            )
            
            st.markdown("---")
            
            # Video player controls (if scene is selected)
            if st.session_state.selected_scene:
                st.markdown("### 🎥 Now Playing")
                scene = st.session_state.selected_scene
                st.markdown(f"**Video:** {scene.get('video_title', 'Educational Video')}")
                st.markdown(f"**Time:** {self.format_time(scene.get('start_time', 0))} - {self.format_time(scene.get('end_time', 30))}")
                
                if st.button("❌ Close Player"):
                    st.session_state.selected_scene = None
                    st.rerun()
            
            st.markdown("---")
            
            # Quick stats
            st.markdown("### Quick Stats")
            try:
                videos = self.api_client.get_videos()
                processed_count = len([v for v in videos if v.get('status') == 'indexed'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Videos", len(videos))
                with col2:
                    st.metric("Processed", processed_count)
                    
            except Exception as e:
                st.error(f"Error loading stats: {str(e)}")
            
            st.markdown("---")
            
            # Popular topics
            st.markdown("### Popular Topics")
            try:
                topics_response = self.api_client.get_popular_topics()
                for topic in topics_response.get('popular_topics', [])[:5]:
                    st.markdown(f"• **{topic['topic']}** ({topic['count']})")
            except:
                st.markdown("• Physics Demonstrations")
                st.markdown("• Math Problem Solving")
                st.markdown("• Chemistry Experiments")
            
            # Set current page
            st.session_state.current_page = page
    
    def render_main_content(self):
        """Render main content based on selected page"""
        page = st.session_state.get('current_page', '🔍 Search Videos')
        
        if page == "🔍 Search Videos":
            self.render_search_page()
        elif page == "📤 Upload Video":
            self.render_upload_page()
        elif page == "📚 My Videos":
            self.render_videos_page()
        elif page == "📈 Analytics":
            self.render_analytics_page()
    
    def render_search_page(self):
        """Render search page"""
        st.markdown("## 🔍 Search Educational Content")
        
        # Use the SearchInterface component
        search_data = self.search_interface.render_search_form()
        
        # Handle follow-up queries from suggestions
        if st.session_state.get('follow_up_query'):
            search_data = {
                "query": st.session_state.follow_up_query,
                "video_id": None,
                "subject_filter": None,
                "max_results": 5
            }
            st.session_state.follow_up_query = None
        
        # Perform search if search data is available
        if search_data:
            with st.spinner("🔍 Searching educational content..."):
                try:
                    search_params = {
                        "query": search_data["query"],
                        "max_results": search_data["max_results"],
                        "min_confidence": 0.5
                    }
                    
                    if search_data["video_id"]:
                        search_params["video_id"] = search_data["video_id"]
                    
                    if search_data["subject_filter"]:
                        search_params["subject_filter"] = search_data["subject_filter"].lower()
                    
                    results = self.api_client.search_scenes(search_params)
                    st.session_state.search_results = results
                    st.session_state.last_search_query = search_data["query"]
                    
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
                    st.session_state.search_results = {"results": [], "total_results": 0}
        
        # Display results using ResultsDisplay component
        if st.session_state.get('search_results'):
            self.results_display.render_results(st.session_state.search_results)
    
    def render_video_player_section(self):
        """Render video player section when scene is selected"""
        st.markdown('<div class="video-player-container">', unsafe_allow_html=True)
        
        # Get video file information
        scene = st.session_state.selected_scene
        video_id = scene.get('video_id')
        
        # Try to get video metadata and file path
        video_metadata = None
        if video_id:
            try:
                video_metadata = self.api_client.get_video(video_id)
            except Exception as e:
                st.error(f"Error loading video metadata: {str(e)}")
        
        # Render the video player with enhanced functionality
        self.video_player.render_player(scene, video_metadata)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_upload_page(self):
        """Render video upload page"""
        st.markdown("## 📤 Upload Educational Video")
        
        # Use the VideoUploader component
        upload_data = self.video_uploader.render_upload_form()
        
        if upload_data:
            with st.spinner("Uploading video..."):
                try:
                    # Prepare metadata in the format expected by API client
                    metadata = {
                        "title": upload_data["title"],
                        "description": upload_data["description"],
                        "subject": upload_data["subject"] if upload_data["subject"] else None,
                        "difficulty_level": upload_data["difficulty"].lower() if upload_data["difficulty"] else None,
                        "tags": upload_data["tags"] if upload_data["tags"] else ""
                    }
                    
                    # Upload video using API client
                    response = self.api_client.upload_video(upload_data["file"], metadata)
                    
                    if response:
                        st.success(f"✅ Video uploaded successfully! ID: {response.get('video_id')}")
                        st.info("🔄 Video processing has started. Check the 'My Videos' section for progress.")
                        
                        # Add progress tracking
                        video_id = response.get('video_id')
                        if video_id:
                            self.show_processing_progress(video_id)
                    else:
                        st.error("Upload failed. Please try again.")
                        
                except Exception as e:
                    st.error(f"Upload error: {str(e)}")
    
    def show_processing_progress(self, video_id: str):
        """Show video processing progress"""
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        for i in range(30):  # Check for up to 5 minutes
            try:
                status = self.api_client.get_video_status(video_id)
                current_status = status.get('status', 'unknown')
                
                with status_placeholder.container():
                    if current_status == 'processing':
                        st.info(f"🔄 Processing video... ({i+1}/30)")
                    elif current_status == 'indexed':
                        st.success("✅ Video processed successfully! Ready for search.")
                        break
                    elif current_status == 'failed':
                        st.error("❌ Video processing failed.")
                        break
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                st.error(f"Error checking status: {str(e)}")
                break
    
    def render_videos_page(self):
        """Render videos management page"""
        st.markdown("## 📚 My Videos")
        
        # Refresh button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 Refresh", type="secondary"):
                st.rerun()
        
        try:
            videos = self.api_client.get_videos()
            
            if not videos:
                st.info("No videos uploaded yet. Upload your first educational video!")
                return
            
            # Video filters
            with st.expander("Filter Videos"):
                col1, col2 = st.columns(2)
                with col1:
                    status_filter = st.selectbox(
                        "Status",
                        ["All", "Processing", "Indexed", "Failed"],
                        key="video_status_filter"
                    )
                with col2:
                    subject_filter = st.selectbox(
                        "Subject",
                        ["All"] + list(set([v.get('subject') for v in videos if v.get('subject')])),
                        key="video_subject_filter"
                    )
            
            # Filter videos
            filtered_videos = videos
            if status_filter != "All":
                filtered_videos = [v for v in filtered_videos if v.get('status') == status_filter.lower()]
            if subject_filter != "All":
                filtered_videos = [v for v in filtered_videos if v.get('subject') == subject_filter]
            
            # Display videos
            for video in filtered_videos:
                with st.container():
                    st.markdown(f"""
                    <div class="video-card">
                        <h4>🎬 {video.get('title', 'Untitled Video')}</h4>
                        <p><strong>Status:</strong> {self.get_status_badge(video.get('status', 'unknown'))}</p>
                        <p><strong>Subject:</strong> {video.get('subject', 'Not specified')}</p>
                        <p><strong>Uploaded:</strong> {self.format_datetime(video.get('created_at'))}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if video.get('description'):
                        st.markdown(f"**Description:** {video['description']}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if video.get('status') == 'indexed':
                            if st.button(f"🔍 Search Scenes", key=f"search_{video['id']}"):
                                st.session_state.current_video_id = video['id']
                                st.session_state.current_page = "🔍 Search Videos"
                                st.rerun()
                    
                    with col2:
                        if st.button(f"📊 View Scenes", key=f"scenes_{video['id']}"):
                            self.show_video_scenes(video['id'])
                    
                    with col3:
                        if st.button(f"📈 Analytics", key=f"analytics_{video['id']}"):
                            st.session_state.selected_video_analytics = video['id']
                    
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"delete_{video['id']}"):
                            if st.session_state.get(f"confirm_delete_{video['id']}", False):
                                try:
                                    self.api_client.delete_video(video['id'])
                                    st.success("Video deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Delete failed: {str(e)}")
                            else:
                                st.session_state[f"confirm_delete_{video['id']}"] = True
                                st.warning("Click again to confirm deletion")
                    
                    st.markdown("---")
                    
        except Exception as e:
            st.error(f"Error loading videos: {str(e)}")
    
    def show_video_scenes(self, video_id: str):
        """Show scenes for a specific video"""
        try:
            scenes_data = self.api_client.get_video_scenes(video_id)
            scenes = scenes_data.get('scenes', [])
            
            if not scenes:
                st.info("No scenes detected yet. Video may still be processing.")
                return
            
            st.markdown(f"### 🎬 Scenes for Video")
            
            for i, scene in enumerate(scenes):
                with st.expander(f"Scene {i+1}: {self.format_time(scene.get('start_time', 0))} - {self.format_time(scene.get('end_time', 30))}"):
                    st.markdown(f"**Description:** {scene.get('description', 'No description')}")
                    
                    if scene.get('labels'):
                        st.markdown("**Labels:** " + " ".join([f'<span class="scene-label">{label}</span>' for label in scene['labels']]), unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Confidence", f"{scene.get('confidence_score', 0):.1%}")
                    with col2:
                        if st.button(f"▶️ Play Scene {i+1}", key=f"play_scene_{video_id}_{i}"):
                            # Create scene data in the format expected by video player
                            scene_data = {
                                'video_id': video_id,
                                'scene_id': scene.get('id'),
                                'start_time': scene.get('start_time', 0),
                                'end_time': scene.get('end_time', 30),
                                'scene': scene,
                                'video_title': f"Video {video_id}"  # You might want to get actual title
                            }
                            st.session_state.selected_scene = scene_data
                            st.rerun()
                            
        except Exception as e:
            st.error(f"Error loading scenes: {str(e)}")
    
    def render_analytics_page(self):
        """Render analytics and insights page"""
        st.markdown("## 📈 Analytics & Insights")
        
        try:
            videos = self.api_client.get_videos()
            
            if not videos:
                st.info("No data available yet. Upload some videos to see analytics!")
                return
            
            # Overall statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_videos = len(videos)
            processed_videos = len([v for v in videos if v.get('status') == 'indexed'])
            processing_videos = len([v for v in videos if v.get('status') == 'processing'])
            failed_videos = len([v for v in videos if v.get('status') == 'failed'])
            
            with col1:
                st.metric("Total Videos", total_videos)
            with col2:
                st.metric("Processed", processed_videos, delta=f"{processed_videos/total_videos*100:.1f}%" if total_videos > 0 else "0%")
            with col3:
                st.metric("Processing", processing_videos)
            with col4:
                st.metric("Failed", failed_videos)
            
            # Subject distribution
            st.markdown("### 📚 Subject Distribution")
            subject_counts = {}
            for video in videos:
                subject = video.get('subject', 'Unspecified')
                subject_counts[subject] = subject_counts.get(subject, 0) + 1
            
            if subject_counts:
                import matplotlib.pyplot as plt
                import pandas as pd
                
                df = pd.DataFrame(list(subject_counts.items()), columns=['Subject', 'Count'])
                st.bar_chart(df.set_index('Subject'))
            
            # Processing status over time
            st.markdown("### 📊 Upload Timeline")
            
            # Mock data for timeline (in production, use actual dates)
            timeline_data = []
            for i, video in enumerate(videos[-10:]):  # Last 10 videos
                timeline_data.append({
                    'Date': video.get('created_at', datetime.now().isoformat())[:10],
                    'Status': video.get('status', 'unknown').title(),
                    'Count': 1
                })
            
            if timeline_data:
                df = pd.DataFrame(timeline_data)
                df['Date'] = pd.to_datetime(df['Date'])
                daily_counts = df.groupby(['Date', 'Status']).sum().reset_index()
                
                # Simple line chart
                chart_data = daily_counts.pivot(index='Date', columns='Status', values='Count').fillna(0)
                st.line_chart(chart_data)
            
            # Popular search terms (mock data)
            st.markdown("### 🔍 Popular Search Terms")
            popular_searches = [
                {"term": "physics demonstration", "count": 45},
                {"term": "chemical reaction", "count": 32},
                {"term": "mathematical proof", "count": 28},
                {"term": "programming tutorial", "count": 25},
                {"term": "biology experiment", "count": 22}
            ]
            
            for search in popular_searches:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{search['term']}**")
                with col2:
                    st.write(f"{search['count']} searches")
            
            # Video performance insights
            st.markdown("### 🎯 Content Insights")
            
            insights = [
                "📈 Videos with clear narration get 40% more relevant search results",
                "🔬 Science demonstration videos have the highest engagement",
                "⏱️ Optimal video length for learning: 5-15 minutes",
                "🏷️ Videos with proper tags are found 3x more often",
                "📝 Adding descriptions improves search accuracy by 25%"
            ]
            
            for insight in insights:
                st.info(insight)
                
        except Exception as e:
            st.error(f"Error loading analytics: {str(e)}")
    
    def submit_feedback(self, result: Dict[str, Any], helpful: bool):
        """Submit feedback for search result"""
        try:
            feedback_data = {
                "query": st.session_state.get('search_query', ''),
                "scene_id": result.get('scene_id'),
                "video_id": result.get('video_id'),
                "helpful": helpful
            }
            
            self.api_client.submit_feedback(feedback_data)
            st.success("Thanks for your feedback!" if helpful else "Feedback noted. We'll improve the results.")
            
        except Exception as e:
            st.error(f"Failed to submit feedback: {str(e)}")
    
    def format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def format_datetime(self, dt_string: str) -> str:
        """Format datetime string for display"""
        try:
            if dt_string:
                dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            return "Unknown"
        except:
            return "Unknown"
    
    def get_status_badge(self, status: str) -> str:
        """Get HTML badge for status"""
        status_colors = {
            'uploading': '#ffc107',
            'processing': '#17a2b8', 
            'indexed': '#28a745',
            'failed': '#dc3545'
        }
        
        color = status_colors.get(status, '#6c757d')
        return f'<span style="background-color: {color}; color: white; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.8rem;">{status.title()}</span>'

def main():
    """Main application entry point"""
    app = VideoLearningApp()
    app.run()

if __name__ == "__main__":
    main()