import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Document Extraction & Optimization",
    page_icon="📄",
    layout="wide"
)

# App title and logo (will appear on all pages)
st.title("📄 Document Extraction & Optimization")
st.markdown("Extract structured information from technical documents using AI")

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