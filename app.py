import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Document Extraction & Optimization",
    page_icon="📄",
    layout="wide"
)

def login_screen():
    """Display the login screen for unauthenticated users"""
    st.title("📄 Document Extraction & Optimization")
    st.markdown("Extract structured information from technical documents using AI")
    
    st.divider()
    
    st.header("🔒 This app is private.")
    st.subheader("Please log in to continue.")
    
    # Center the login button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("🚀 Log in with Google", on_click=st.login, type="primary", use_container_width=True)
    
    st.divider()
    
    # Add some information about the app
    st.markdown("""
    ### About This Application
    
    This application provides AI-powered document analysis capabilities:
    
    - **📋 Work Package Extraction**: Extract structured information from technical documents
    - **🎨 IFC Drawing Analysis**: Analyze 3D CAD files and extract component data
    
    Powered by Google Vertex AI Gemini models.
    """)

def main_app():
    """Display the main application for authenticated users"""
    # App title and user greeting
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("📄 Document Extraction & Optimization")
        st.markdown("Extract structured information from technical documents using AI")
    
    with col2:
        st.markdown(f"### Welcome! 👋")
        if st.button("🚪 Log out", type="secondary"):
            st.logout()
    
    st.divider()
    
    # Define pages using st.Page
    wp_page = st.Page(
        "wp.py", 
        title="Work Package Extraction", 
        icon="📋",
        default=True
    )
    
    drawing_page = st.Page(
        "drawing.py", 
        title="Drawing Analysis", 
        icon="🎨"
    )
    
    # Create navigation with grouped pages
    page_dict = {
        "Analysis Tools": [wp_page, drawing_page]
    }
    
    # Create navigation
    pg = st.navigation(page_dict)
    
    # Run the selected page
    pg.run()

# Check authentication status and display appropriate screen
main_app()