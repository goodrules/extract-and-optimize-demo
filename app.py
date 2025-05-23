import streamlit as st
from google import genai
from google.genai import types
from google.cloud import storage
import json
import subprocess

from config.schema import schema_work_package_basic, schema_work_package_advanced
from config.system_prompt import system_prompt as default_system_prompt

# Page configuration
st.set_page_config(
    page_title="Document Extraction & Optimization",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'custom_schema' not in st.session_state:
    st.session_state.custom_schema = None
if 'custom_system_prompt' not in st.session_state:
    st.session_state.custom_system_prompt = None

@st.cache_data
def get_project_id():
    """Get the current GCP project ID"""
    result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                          capture_output=True, text=True)
    return result.stdout.strip()

@st.cache_data
def list_files_in_bucket(bucket_name="wec_demo_files", prefix="examples/"):
    """List files in a GCS bucket with given prefix"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        file_list = []
        for blob in blobs:
            # Only include actual files, not directories
            if not blob.name.endswith('/'):
                file_list.append(blob.name)
        
        return file_list
    except Exception as e:
        st.error(f"Error accessing bucket: {str(e)}")
        return []

def initialize_client(project_id, region):
    """Initialize genai client with Vertex AI"""
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=region,
    )

def generate_extraction(client, prompt, file_path, model, schema_type):
    """Generate extraction from document"""
    # Select schema based on user choice
    if st.session_state.custom_schema and schema_type == "Custom":
        schema = st.session_state.custom_schema
    else:
        schema = schema_work_package_advanced if schema_type == "Advanced" else schema_work_package_basic
    
    # Use custom system prompt if available
    system_prompt = st.session_state.custom_system_prompt if st.session_state.custom_system_prompt else default_system_prompt
    
    # Prepare content with PDF file
    pdf_file = types.Part.from_uri(
        file_uri=file_path,
        mime_type="application/pdf",
    )
    
    contents = [
        types.Content(
            role="user",
            parts=[
                pdf_file,
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
        temperature=0.2,
        top_p=1,
        seed=0,
        max_output_tokens=65535,
        response_modalities=["TEXT"],
        response_mime_type="application/json",
        system_instruction=system_prompt,
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

# Main app
st.title("📄 Document Extraction & Optimization")
st.markdown("Extract structured information from technical documents using Gemini models")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection
    model_option = st.selectbox(
        "Select Model",
        ["gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-05-06"],
        index=0  # Default to Flash
    )
    
    # Schema selection
    schema_options = ["Advanced", "Basic"]
    if st.session_state.custom_schema:
        schema_options.append("Custom")
    
    schema_type = st.selectbox(
        "Select Schema",
        schema_options,
        index=0
    )
    
    # Region
    region = st.text_input("Region", value="us-central1")
    
    # Get project ID
    project_id = get_project_id()
    st.info(f"Project ID: {project_id}")
    
    # Custom uploads section
    st.divider()
    st.subheader("Custom Configuration")
    
    # Custom schema upload
    uploaded_schema = st.file_uploader(
        "Upload Custom Schema (JSON)",
        type=['json'],
        help="Upload a JSON file with your custom extraction schema"
    )
    
    if uploaded_schema is not None:
        try:
            schema_content = json.loads(uploaded_schema.read())
            st.session_state.custom_schema = schema_content
            st.success("✅ Custom schema loaded successfully!")
            uploaded_schema.seek(0)  # Reset file pointer
        except Exception as e:
            st.error(f"Error loading schema: {str(e)}")
    
    # Custom system prompt upload
    uploaded_prompt = st.file_uploader(
        "Upload Custom System Prompt (TXT)",
        type=['txt'],
        help="Upload a text file with your custom system prompt"
    )
    
    if uploaded_prompt is not None:
        try:
            prompt_content = uploaded_prompt.read().decode('utf-8')
            st.session_state.custom_system_prompt = prompt_content
            st.success("✅ Custom system prompt loaded successfully!")
            uploaded_prompt.seek(0)  # Reset file pointer
        except Exception as e:
            st.error(f"Error loading system prompt: {str(e)}")
    
    # Show current configuration status
    if st.session_state.custom_schema or st.session_state.custom_system_prompt:
        st.divider()
        st.caption("**Active Custom Configuration:**")
        if st.session_state.custom_schema:
            st.caption("• Custom schema loaded")
        if st.session_state.custom_system_prompt:
            st.caption("• Custom system prompt loaded")
    
    # Refresh button
    st.divider()
    if st.button("🔄 Refresh Page", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Rerun the app
        st.rerun()

# Main content area
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Document Selection")
    
    # List files from bucket
    files = list_files_in_bucket()
    
    if files:
        selected_file = st.selectbox(
            "Select a document from GCS",
            files,
            format_func=lambda x: x.split('/')[-1]  # Show only filename
        )
        
        # Construct full GCS path
        if selected_file:
            file_path = f"gs://wec_demo_files/{selected_file}"
            st.success(f"Selected: {selected_file.split('/')[-1]}")
            
            # Custom prompt
            prompt = st.text_area(
                "Extraction Prompt",
                value="Review this document, and extract key elements and information. Respond ONLY with a valid JSON object strictly conforming to the required schema.",
                height=100
            )
            
            # Extract button
            if st.button("🚀 Extract Information", type="primary"):
                with st.spinner("Processing document..."):
                    try:
                        # Initialize client
                        client = initialize_client(project_id, region)
                        
                        # Generate extraction
                        response, token_count = generate_extraction(
                            client, prompt, file_path, model_option, schema_type
                        )
                        
                        # Parse and store result
                        st.session_state.extracted_data = json.loads(response.text)
                        st.success(f"✅ Extraction complete! ({token_count} input tokens)")
                        
                    except Exception as e:
                        st.error(f"Error during extraction: {str(e)}")
    else:
        st.error("No files found in the bucket")

with col2:
    st.header("Extraction Results")
    
    if st.session_state.extracted_data:
        # Display options
        view_option = st.radio(
            "View format",
            ["Formatted JSON", "Raw JSON", "Expandable Sections"],
            horizontal=True
        )
        
        if view_option == "Formatted JSON":
            # Pretty-printed JSON in a code block
            st.code(json.dumps(st.session_state.extracted_data, indent=2), language="json")
            
        elif view_option == "Raw JSON":
            # Raw JSON in a text area (editable)
            edited_json = st.text_area(
                "JSON Data (editable)",
                value=json.dumps(st.session_state.extracted_data, indent=2),
                height=500
            )
            
        else:  # Expandable Sections
            # Dynamic display for any schema structure
            data = st.session_state.extracted_data
            
            def display_value(value, indent_level=0):
                """Recursively display values with proper formatting"""
                indent = "&nbsp;" * (indent_level * 4)
                
                if isinstance(value, dict):
                    for k, v in value.items():
                        if isinstance(v, (dict, list)):
                            st.markdown(f"{indent}**{k.replace('_', ' ').title()}:**")
                            display_value(v, indent_level + 1)
                        else:
                            st.markdown(f"{indent}**{k.replace('_', ' ').title()}:** {v}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            st.markdown(f"{indent}• Item {i + 1}:")
                            display_value(item, indent_level + 1)
                        else:
                            st.markdown(f"{indent}• {item}")
                else:
                    st.markdown(f"{indent}{value}")
            
            # Define icons for common section names
            section_icons = {
                "metadata": "📋",
                "project": "🏗️",
                "technical": "⚙️",
                "timeline": "📅",
                "milestone": "🎯",
                "financial": "💰",
                "stakeholder": "👥",
                "permit": "📄",
                "document": "📑",
                "location": "📍",
                "specs": "📊",
                "approval": "✅"
            }
            
            def get_section_icon(section_name):
                """Get appropriate icon for section based on keywords"""
                section_lower = section_name.lower()
                for keyword, icon in section_icons.items():
                    if keyword in section_lower:
                        return icon
                return "📁"  # Default icon
            
            # Display each top-level key as an expandable section
            for key, value in data.items():
                # Format the section title
                title = key.replace('_', ' ').title()
                icon = get_section_icon(key)
                
                # Determine if section should be expanded by default
                expanded = key in ["project_metadata", "project_name", "metadata"]
                
                # Count items if it's a list
                if isinstance(value, list):
                    title += f" ({len(value)} items)"
                
                with st.expander(f"{icon} {title}", expanded=expanded):
                    if isinstance(value, dict):
                        # For dictionaries, display key-value pairs
                        for k, v in value.items():
                            if isinstance(v, (dict, list)):
                                st.write(f"**{k.replace('_', ' ').title()}:**")
                                display_value(v, 1)
                            else:
                                st.write(f"**{k.replace('_', ' ').title()}:** {v}")
                    elif isinstance(value, list):
                        # For lists, display each item
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                # Find a good identifier for the item
                                identifier = None
                                for id_key in ['name', 'title', 'type', 'role', 'milestone_name', 'permit_type', 'document_type']:
                                    if id_key in item:
                                        identifier = item[id_key]
                                        break
                                
                                if identifier:
                                    st.write(f"### {identifier}")
                                else:
                                    st.write(f"### Item {i + 1}")
                                
                                display_value(item, 0)
                                if i < len(value) - 1:
                                    st.divider()
                            else:
                                st.write(f"• {item}")
                    else:
                        # For simple values
                        st.write(value)
        
        # Download section
        st.divider()
        col1_dl, col2_dl = st.columns(2)
        
        with col1_dl:
            # Download JSON button
            json_str = json.dumps(st.session_state.extracted_data, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"extraction_{selected_file.split('/')[-1].replace('.pdf', '')}.json",
                mime="application/json"
            )
        
        with col2_dl:
            # Copy to clipboard button (using st.code for easy copying)
            if st.button("📋 Copy to Clipboard"):
                st.code(json_str, language="json")
                st.info("Select all text above and copy (Ctrl+C or Cmd+C)")
    
    else:
        st.info("👈 Select a document and click 'Extract Information' to see results")

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