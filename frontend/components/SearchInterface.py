import streamlit as st
from typing import Dict, Any, List, Optional

class SearchInterface:
    def __init__(self, api_client):
        self.api_client = api_client
    
    def render_search_form(self) -> Optional[Dict[str, Any]]:
        """Render search interface"""
        # Main search bar
        col1, col2 = st.columns([4, 1])
        
        with col1:
            query = st.text_input(
                "Search educational content:",
                placeholder="e.g., 'Show me the part about photosynthesis'",
                key="main_search"
            )
        
        with col2:
            search_clicked = st.button("🔍 Search", type="primary")
        
        # Advanced options
        with st.expander("🔧 Advanced Search"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                video_filter = st.selectbox("Specific Video", ["All Videos"] + self._get_video_list())
            
            with col2:
                subject_filter = st.selectbox("Subject", 
                    ["All", "Physics", "Math", "Chemistry", "Biology", "Programming"])
            
            with col3:
                max_results = st.slider("Max Results", 1, 20, 5)
        
        # Search suggestions
        if query and len(query) > 2:
            self._show_search_suggestions(query)
        
        if search_clicked and query:
            return {
                "query": query,
                "video_id": None if video_filter == "All Videos" else video_filter,
                "subject_filter": None if subject_filter == "All" else subject_filter,
                "max_results": max_results
            }
        
        return None
    
    def _get_video_list(self) -> List[str]:
        """Get list of available videos"""
        try:
            videos = self.api_client.get_videos()
            return [f"{v.get('title', 'Untitled')} ({v.get('id', '')})" for v in videos if v.get('status') == 'indexed']
        except:
            return []
    
    def _show_search_suggestions(self, query: str):
        """Show search suggestions"""
        try:
            suggestions = self.api_client.get_search_suggestions(query)
            if suggestions.get('suggestions'):
                st.write("💡 **Suggestions:**")
                for suggestion in suggestions['suggestions'][:3]:
                    if st.button(suggestion, key=f"sugg_{hash(suggestion)}"):
                        st.session_state.main_search = suggestion
                        st.rerun()
        except:
            pass