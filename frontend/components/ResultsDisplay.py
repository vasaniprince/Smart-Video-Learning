import streamlit as st
from typing import Dict, Any, List

class ResultsDisplay:
    def __init__(self, api_client):
        self.api_client = api_client
    
    def render_results(self, results: Dict[str, Any]):
        """Render search results"""
        if not results or not results.get('results'):
            st.info("No results found. Try different keywords.")
            return
        
        total_results = results.get('total_results', 0)
        processing_time = results.get('processing_time', 0)
        
        st.markdown(f"### 📋 Found {total_results} relevant scenes ({processing_time:.2f}s)")
        
        for i, result in enumerate(results['results']):
            self._render_single_result(result, i)
        
        # Show suggestions if available
        if results.get('suggestions'):
            st.markdown("### 💡 Related Questions")
            for suggestion in results['suggestions']:
                if st.button(f"🔍 {suggestion}", key=f"suggestion_{hash(suggestion)}"):
                    # Update search query and trigger new search
                    st.session_state.follow_up_query = suggestion
                    st.rerun()
    
    def _render_single_result(self, result: Dict[str, Any], index: int):
        """Render a single search result"""
        with st.container():
            # Result header
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"#### 🎬 {result.get('video_title', 'Educational Video')}")
            
            with col2:
                relevance = result.get('relevance_score', 0)
                st.metric("Relevance", f"{relevance:.1%}")
            
            # Time info
            start_time = result.get('start_time', 0)
            end_time = result.get('end_time', 30)
            st.markdown(f"⏱️ **Time:** {self._format_time(start_time)} - {self._format_time(end_time)}")
            
            # Scene description
            scene = result.get('scene', {})
            if scene.get('description'):
                st.markdown(f"**Content:** {scene['description']}")
            
            # AI explanation
            if result.get('explanation'):
                st.markdown(f"**Why this helps:** {result['explanation']}")
            
            # Labels/tags
            if scene.get('labels'):
                labels_html = " ".join([
                    f'<span style="background: #667eea; color: white; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.8rem; margin: 0.2rem;">{label}</span>'
                    for label in scene['labels']
                ])
                st.markdown(f"**Topics:** {labels_html}", unsafe_allow_html=True)
            
            # Action buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button(f"▶️ Play", key=f"play_result_{index}"):
                    st.session_state.selected_scene = result
                    st.success("Scene selected for playback!")
            
            with col2:
                if st.button(f"🔗 Related", key=f"related_{index}"):
                    self._show_related_scenes(result)
            
            with col3:
                if st.button(f"👍", key=f"like_{index}"):
                    self._submit_feedback(result, True)
            
            with col4:
                if st.button(f"👎", key=f"dislike_{index}"):
                    self._submit_feedback(result, False)
            
            st.markdown("---")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _show_related_scenes(self, result: Dict[str, Any]):
        """Show related scenes"""
        try:
            video_id = result.get('video_id')
            scene_id = result.get('scene_id')
            
            if video_id and scene_id:
                related = self.api_client.get_related_scenes(video_id, scene_id)
                
                if related and related.get('related_scenes'):
                    st.markdown("#### 🔗 Related Scenes")
                    for scene in related['related_scenes'][:3]:  # Show top 3
                        st.markdown(f"• **{scene.get('video_title', 'Video')}** ({self._format_time(scene.get('start_time', 0))})")
                else:
                    st.info("No related scenes found")
        except Exception as e:
            st.error(f"Error loading related scenes: {str(e)}")
    
    def _submit_feedback(self, result: Dict[str, Any], helpful: bool):
        """Submit user feedback"""
        try:
            feedback_data = {
                "query": st.session_state.get('last_search_query', ''),
                "scene_id": result.get('scene_id'),
                "video_id": result.get('video_id'),
                "helpful": helpful
            }
            
            self.api_client.submit_feedback(feedback_data)
            
            if helpful:
                st.success("👍 Thanks for the positive feedback!")
            else:
                st.info("👎 Feedback noted. We'll work on better results.")
                
        except Exception as e:
            st.error(f"Failed to submit feedback: {str(e)}")
