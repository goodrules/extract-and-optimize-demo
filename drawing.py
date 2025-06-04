import streamlit as st
from google import genai
from google.genai import types
import json
import subprocess
import tempfile
import os

import config.schema as schemas
from config.system_prompt import system_prompt as default_system_prompt

# Page header
st.header("🎨 IFC Drawing Analysis")

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'original_extracted_data' not in st.session_state:
    st.session_state.original_extracted_data = None
if 'selected_filename' not in st.session_state:
    st.session_state.selected_filename = None

@st.cache_data
def get_project_id():
    """Get the current GCP project ID"""
    result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                          capture_output=True, text=True)
    return result.stdout.strip()

def initialize_client(project_id, region):
    """Initialize genai client with Vertex AI"""
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=region,
    )

def process_uploaded_ifc_file(uploaded_file):
    """Process uploaded IFC file and read as text string."""
    if uploaded_file is None:
        return None
        
    # Create a temporary file to store the uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    # Read the file content as text
    try:
        with open(tmp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(tmp_file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Clean up temporary file
    os.unlink(tmp_file_path)
    
    return content

def generate_ifc_extraction(client, ifc_content, model, schema):
    """Generate extraction from IFC content string"""
    
    # Create prompt for IFC analysis
    prompt = f"""Analyze the following IFC (3D CAD) data and extract structured information according to the provided schema.
    
Focus on identifying:
- Project metadata and basic information
- Spatial placement and coordinate systems  
- Component types, counts, and properties
- Individual component details including coordinates, materials, and dimensions

IFC Data:
{ifc_content[:50000]}...

Respond ONLY with a valid JSON object strictly conforming to the required schema."""
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt)
            ]
        )
    ]
    
    # Count tokens
    token_count = client.models.count_tokens(
        model=model,
        contents=contents,
    )
    
    # Configure generation
    generate_content_config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=65535,
        response_modalities=["TEXT"],
        response_mime_type="application/json",
        system_instruction=default_system_prompt,
        response_schema=schema,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
    )
    
    # Generate response
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config
    )
    
    return response, token_count.total_tokens

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection
    model_option = st.selectbox(
        "Select Model",
        ["gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-05-06"],
        index=1  # Default to Pro
    )
    
    # Schema is fixed to IFC schema
    st.info("ℹ️ Using IFC 3D CAD Analysis Schema")
    
    # Region
    region = st.text_input("Region", value="us-central1")
    
    # Get project ID
    project_id = get_project_id()
    st.info(f"Project ID: {project_id}")
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Page", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Rerun the app
        st.rerun()

# Main content area
st.header("IFC File Upload")

file_selected = False
ifc_content = None
selected_filename = None

uploaded_file = st.file_uploader(
    "Choose an IFC file",
    type=['ifc'],
    help="Upload an IFC file for 3D CAD analysis"
)

if uploaded_file is not None:
    ifc_content = process_uploaded_ifc_file(uploaded_file)
    selected_filename = uploaded_file.name
    file_selected = True
    st.success(f"Uploaded: {selected_filename}")
    st.info(f"File size: {len(ifc_content):,} characters")

# Show extract button only if a file is selected
if file_selected:
    # Extract button
    if st.button("🚀 Analyze IFC Data", type="primary"):
        with st.spinner("Processing IFC file..."):
            try:
                # Initialize client
                client = initialize_client(project_id, region)
                
                # Get IFC schema
                ifc_schema = schemas.ifc_schema
                
                # Generate extraction
                response, token_count = generate_ifc_extraction(
                    client, ifc_content, model_option, ifc_schema
                )
                
                # Parse and store result
                extracted_result = json.loads(response.text)
                st.session_state.extracted_data = extracted_result
                st.session_state.original_extracted_data = json.loads(json.dumps(extracted_result))  # Deep copy
                st.session_state.selected_filename = selected_filename
                st.success(f"✅ Analysis complete! ({token_count} input tokens)")
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")

st.header("Analysis Results")

if st.session_state.extracted_data:
    # Display options
    view_option = st.radio(
        "View format",
        ["Project Overview", "Component Summary", "Detailed Components", "Raw JSON"],
        horizontal=True
    )
    
    data = st.session_state.extracted_data
    
    if view_option == "Project Overview":
        # Display project metadata and spatial placement
        if 'projectMetadata' in data:
            st.subheader("📋 Project Information")
            metadata = data['projectMetadata']
            
            col_meta1, col_meta2 = st.columns(2)
            with col_meta1:
                st.metric("Project Name", metadata.get('projectName', 'N/A'))
                st.metric("Schema Version", metadata.get('schemaVersion', 'N/A'))
                st.text(f"Global ID: {metadata.get('globalId', 'N/A')}")
            
            with col_meta2:
                st.metric("Creation Date", metadata.get('creationDate', 'N/A'))
                st.text(f"Authoring Tool: {metadata.get('authoringTool', 'N/A')}")
                st.text(f"Organization: {metadata.get('organization', 'N/A')}")
        
        if 'overallSpatialPlacement' in data:
            st.subheader("🗺️ Spatial Placement")
            spatial = data['overallSpatialPlacement']
            
            if 'site' in spatial:
                site = spatial['site']
                st.markdown(f"**Site:** {site.get('name', 'N/A')}")
                st.text(f"Coordinates - E: {site.get('easting', 0)}, N: {site.get('northing', 0)}, Elev: {site.get('elevation', 0)}")
            
            if 'building' in spatial:
                building = spatial['building']
                st.markdown(f"**Building:** {building.get('name', 'N/A')}")
                st.text(f"Position - X: {building.get('x', 0)}, Y: {building.get('y', 0)}, Z: {building.get('z', 0)}")
        
    elif view_option == "Component Summary":
        if 'componentSummary' in data:
            summary = data['componentSummary']
            
            # Overview metrics
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.metric("Total Components", summary.get('totalComponents', 0))
            with col_sum2:
                st.metric("Component Types", len(summary.get('componentTypes', [])))
            with col_sum3:
                # Calculate bounding volume if available
                if 'boundingVolume' in summary:
                    bv = summary['boundingVolume']
                    volume = (bv.get('maxX', 0) - bv.get('minX', 0)) * (bv.get('maxY', 0) - bv.get('minY', 0)) * (bv.get('maxZ', 0) - bv.get('minZ', 0))
                    st.metric("Bounding Volume", f"{volume:,.0f} m³")
            
            # Component types breakdown
            st.subheader("📊 Component Types")
            if 'componentTypes' in summary:
                for comp_type in summary['componentTypes']:
                    col_type1, col_type2, col_type3 = st.columns([2, 1, 2])
                    with col_type1:
                        st.write(f"**{comp_type.get('type', 'Unknown')}**")
                    with col_type2:
                        st.write(f"{comp_type.get('count', 0)} items")
                    with col_type3:
                        st.code(comp_type.get('exampleGlobalId', 'N/A'), language=None)
            
            # Bounding volume details
            if 'boundingVolume' in summary:
                st.subheader("📐 Bounding Volume")
                bv = summary['boundingVolume']
                col_bv1, col_bv2 = st.columns(2)
                with col_bv1:
                    st.write(f"**Min Coordinates:** X: {bv.get('minX', 0):.2f}, Y: {bv.get('minY', 0):.2f}, Z: {bv.get('minZ', 0):.2f}")
                with col_bv2:
                    st.write(f"**Max Coordinates:** X: {bv.get('maxX', 0):.2f}, Y: {bv.get('maxY', 0):.2f}, Z: {bv.get('maxZ', 0):.2f}")
        
    elif view_option == "Detailed Components":
        if 'components' in data and data['components']:
            st.subheader(f"🔧 Individual Components ({len(data['components'])} total)")
            
            # Add search/filter
            search_term = st.text_input("Search components by name or type:")
            
            components = data['components']
            if search_term:
                components = [c for c in components if 
                            search_term.lower() in c.get('name', '').lower() or 
                            search_term.lower() in c.get('type', '').lower()]
                st.info(f"Found {len(components)} components matching '{search_term}'")
            
            # Display components in batches to avoid performance issues
            batch_size = 10
            total_components = len(components)
            
            if total_components > batch_size:
                page = st.selectbox("Page", 
                                  options=list(range(1, (total_components // batch_size) + 2)),
                                  format_func=lambda x: f"Page {x} ({(x-1)*batch_size + 1}-{min(x*batch_size, total_components)})")
                start_idx = (page - 1) * batch_size
                end_idx = min(start_idx + batch_size, total_components)
                display_components = components[start_idx:end_idx]
            else:
                display_components = components
            
            for i, component in enumerate(display_components):
                with st.expander(f"{component.get('name', f'Component {i+1}')}", expanded=False):
                    col_comp1, col_comp2 = st.columns(2)
                    
                    with col_comp1:
                        st.write(f"**Type:** {component.get('type', 'N/A')}")
                        st.write(f"**Global ID:** {component.get('globalId', 'N/A')}")
                        st.write(f"**Storey:** {component.get('storey', 'N/A')}")
                        st.write(f"**Material:** {component.get('material', 'N/A')}")
                    
                    with col_comp2:
                        st.write(f"**Position:** X: {component.get('x', 0):.2f}, Y: {component.get('y', 0):.2f}, Z: {component.get('z', 0):.2f}")
                        if 'rotationDegrees' in component:
                            rot = component['rotationDegrees']
                            st.write(f"**Rotation:** X: {rot.get('x', 0):.1f}°, Y: {rot.get('y', 0):.1f}°, Z: {rot.get('z', 0):.1f}°")
                        if 'dimensions' in component:
                            dim = component['dimensions']
                            st.write(f"**Dimensions:** L: {dim.get('length', 0):.2f}, W: {dim.get('width', 0):.2f}, H: {dim.get('height', 0):.2f}")
        
    else:  # Raw JSON
        # Raw JSON display
        st.subheader("Raw JSON Data")
        st.code(json.dumps(data, indent=2), language="json")
    
    # Download section
    st.divider()
    col1_dl, col2_dl = st.columns(2)
    
    with col1_dl:
        # Download JSON button
        json_str = json.dumps(st.session_state.extracted_data, indent=2)
        download_filename = st.session_state.selected_filename.replace('.ifc', '') if st.session_state.selected_filename else "ifc_analysis"
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"ifc_analysis_{download_filename}.json",
            mime="application/json"
        )
    
    with col2_dl:
        # Copy to clipboard button
        if st.button("📋 Copy to Clipboard"):
            st.code(json_str, language="json")
            st.info("Select all text above and copy (Ctrl+C or Cmd+C)")
    
else:
    st.info("👈 Upload an IFC file and click 'Analyze IFC Data' to see results")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Built with Streamlit and Google Vertex AI Gemini models
    </div>
    """,
    unsafe_allow_html=True
)