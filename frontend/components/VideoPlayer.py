import streamlit as st
from typing import Dict, Any, Optional

class VideoPlayer:
    def render_player(self, scene_data: Dict[str, Any]):
        """Render video player for selected scene"""
        if not scene_data:
            return
        
        st.markdown("### 🎥 Video Player")
        
        # Scene info
        video_title = scene_data.get('video_title', 'Educational Video')
        start_time = scene_data.get('start_time', 0)
        end_time = scene_data.get('end_time', 30)
        
        st.markdown(f"""
        **Video:** {video_title}  
        **Scene Time:** {self._format_time(start_time)} - {self._format_time(end_time)}  
        **Duration:** {self._format_time(end_time - start_time)}
        """)
        
        # Video player placeholder (in production, integrate with actual video player)
        st.markdown("""
        <div style="background: #f0f0f0; padding: 3rem; text-align: center; border-radius: 8px; margin: 1rem 0;">
            <h3>🎬 Video Player</h3>
            <p>Video would play here from {start_time}s to {end_time}s</p>
            <p><em>In production: Integrate with VideoDB player or HTML5 video with time controls</em></p>
        </div>
        """.format(start_time=start_time, end_time=end_time), unsafe_allow_html=True)
        
        # Player controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("⏮️ Previous Scene"):
                self._navigate_scene("previous", scene_data)
        
        with col2:
            if st.button("⏸️ Pause"):
                st.info("Video paused")
        
        with col3:
            if st.button("▶️ Play"):
                st.info("Video playing")
        
        with col4:
            if st.button("⏭️ Next Scene"):
                self._navigate_scene("next", scene_data)
        
        # Scene details
        scene = scene_data.get('scene', {})
        if scene:
            with st.expander("📝 Scene Details"):
                st.markdown(f"**Description:** {scene.get('description', 'No description')}")
                
                if scene.get('audio_transcript'):
                    st.markdown(f"**Transcript:** {scene['audio_transcript']}")
                
                if scene.get('labels'):
                    st.markdown("**Labels:** " + ", ".join(scene['labels']))
                
                st.metric("Confidence Score", f"{scene.get('confidence_score', 0):.1%}")
        
        # Related scenes
        self._show_related_scenes(scene_data)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _navigate_scene(self, direction: str, current_scene: Dict[str, Any]):
        """Navigate to previous/next scene"""
        # In production, implement actual scene navigation
        st.info(f"Would navigate to {direction} scene")
    
    def _show_related_scenes(self, scene_data: Dict[str, Any]):
        """Show related scenes"""
        with st.expander("🔗 Related Scenes"):
            st.info("Related scenes would be shown here based on semantic similarity")
