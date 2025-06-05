import streamlit as st
from google import genai
from google.genai import types
from google.cloud import storage
import json
import subprocess
import tempfile
import os
from dotenv import load_dotenv

import config.schema as schemas
from config.system_prompt import system_prompt as default_system_prompt, task_extraction_system_prompt

# Load environment variables
load_dotenv()

# Page header
st.header("📋 Work Package Extraction")

# Initialize session state (page-specific for Work Package)
if 'wp_extracted_data' not in st.session_state:
    st.session_state.wp_extracted_data = None
if 'wp_original_extracted_data' not in st.session_state:
    st.session_state.wp_original_extracted_data = None
if 'wp_selected_filename' not in st.session_state:
    st.session_state.wp_selected_filename = None
if 'custom_schema' not in st.session_state:
    st.session_state.custom_schema = None
if 'custom_system_prompt' not in st.session_state:
    st.session_state.custom_system_prompt = None

@st.cache_data
def get_project_id():
    """Get the current GCP project ID from environment variables or gcloud config"""
    project_id = os.getenv('GCP_PROJECT_ID')
    if project_id:
        return project_id
    
    # Fallback to gcloud config if env var not set
    try:
        result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        st.error("Could not determine GCP project ID. Please set GCP_PROJECT_ID environment variable.")
        return None

@st.cache_data
def list_files_in_bucket(bucket_name=None, prefix=None):
    """List files in a GCS bucket with given prefix"""
    # Use environment variables with fallback defaults
    if bucket_name is None:
        bucket_name = os.getenv('GCS_BUCKET_NAME', 'wec_demo_files')
    if prefix is None:
        prefix = os.getenv('GCS_PREFIX', 'examples/')
    
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

def get_available_schemas():
    """Get all available schemas from the config.schema module"""
    available_schemas = {}
    schema_display_names = {
        'schema_work_package_basic': 'Work Package - Basic',
        'schema_work_package_advanced': 'Work Package - Advanced',
        'schema_cwp_v1': 'Construction Work Package (CWP) - Piping',
        'schema_task_based_work_package': 'Task-Based Work Package'
    }
    
    for attr_name in dir(schemas):
        if attr_name.startswith('schema_'):
            schema_obj = getattr(schemas, attr_name)
            if isinstance(schema_obj, dict):
                # Use friendly display name if available, otherwise format the attribute name
                display_name = schema_display_names.get(attr_name, 
                    attr_name.replace('schema_', '').replace('_', ' ').title())
                
                # Handle nested schema structure (like schema_cwp_v1)
                if 'schema_construction_work_package_piping' in schema_obj:
                    schema_obj = schema_obj['schema_construction_work_package_piping']
                
                available_schemas[display_name] = schema_obj
    
    return available_schemas

def initialize_client(project_id, region):
    """Initialize genai client with Vertex AI"""
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=region,
    )

def process_uploaded_file(uploaded_file):
    """Process uploaded file and convert to genai Part object."""
    if uploaded_file is None:
        return None
        
    # Create a temporary file to store the uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    # Read the file content
    with open(tmp_file_path, "rb") as f:
        file_content = f.read()
    
    # Clean up temporary file
    os.unlink(tmp_file_path)
    
    # Create Part object from file data
    return types.Part.from_bytes(data=file_content, mime_type="application/pdf")

def render_editable_json(data, path="", form_data=None):
    """
    Recursively render JSON data as editable form widgets
    Returns a dictionary of all form values with their paths as keys
    """
    if form_data is None:
        form_data = {}
    
    if isinstance(data, dict):
        # For top-level objects, add section headers
        if not path:
            st.markdown("### 📋 Main Sections")
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Create section headers for top-level keys
            if not path and isinstance(value, (dict, list)):
                st.markdown(f"#### {key.replace('_', ' ').title()}")
                if isinstance(value, dict):
                    with st.container():
                        render_editable_json(value, current_path, form_data)
                elif isinstance(value, list):
                    with st.container():
                        render_editable_json(value, current_path, form_data)
            else:
                render_editable_json(value, current_path, form_data)
            
    elif isinstance(data, list):
        st.markdown(f"**{path.split('.')[-1].replace('_', ' ').title()}** ({len(data)} items)")
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                # Try to find a meaningful identifier for the item
                identifier = f"Item {i + 1}"
                if isinstance(item, dict):
                    for id_key in ['task_id', 'id', 'name', 'title', 'type']:
                        if id_key in item:
                            identifier = f"{identifier}: {item[id_key]}"
                            break
                
                st.markdown(f"*{identifier}*")
                with st.expander(f"Edit {identifier}", expanded=(i < 3)):  # Only expand first 3 items by default
                    render_editable_json(item, current_path, form_data)
            else:
                # For primitive values in arrays
                is_id_field = "id" in current_path.lower()
                widget_key = f"edit_{current_path}"
                
                if isinstance(item, str):
                    # Special handling for enum fields in arrays
                    if "execution_type" in current_path.lower():
                        execution_options = ["series", "parallel"]
                        current_index = execution_options.index(item) if item in execution_options else 0
                        form_data[current_path] = st.selectbox(
                            f"Item {i + 1}",
                            options=execution_options,
                            index=current_index,
                            key=widget_key,
                            disabled=is_id_field,
                            help="ID fields cannot be edited" if is_id_field else "Choose whether task runs in series or parallel"
                        )
                    elif "specialist_required" in current_path.lower():
                        specialist_options = ["pipefitter", "welder", "inspector"]
                        current_index = specialist_options.index(item) if item in specialist_options else 0
                        form_data[current_path] = st.selectbox(
                            f"Item {i + 1}",
                            options=specialist_options,
                            index=current_index,
                            key=widget_key,
                            disabled=is_id_field,
                            help="ID fields cannot be edited" if is_id_field else "Choose the specialist type required for this task"
                        )
                    else:
                        form_data[current_path] = st.text_input(
                            f"Item {i + 1}",
                            value=item,
                            key=widget_key,
                            disabled=is_id_field,
                            help="ID fields cannot be edited" if is_id_field else None
                        )
                elif isinstance(item, int):
                    form_data[current_path] = st.number_input(
                        f"Item {i + 1}",
                        value=item,
                        step=1,
                        key=widget_key,
                        disabled=is_id_field,
                        help="ID fields cannot be edited" if is_id_field else None
                    )
                elif isinstance(item, float):
                    form_data[current_path] = st.number_input(
                        f"Item {i + 1}",
                        value=item,
                        step=0.1,
                        key=widget_key,
                        disabled=is_id_field,
                        help="ID fields cannot be edited" if is_id_field else None
                    )
                elif isinstance(item, bool):
                    form_data[current_path] = st.checkbox(
                        f"Item {i + 1}",
                        value=item,
                        key=widget_key,
                        disabled=is_id_field,
                        help="ID fields cannot be edited" if is_id_field else None
                    )
                    
    else:
        # Handle primitive values
        field_name = path.split('.')[-1].replace('_', ' ').title()
        is_id_field = "id" in path.lower()
        widget_key = f"edit_{path}"
        
        if isinstance(data, str):
            # Special handling for specific enum fields
            if "execution_type" in path.lower():
                execution_options = ["series", "parallel"]
                current_index = execution_options.index(data) if data in execution_options else 0
                form_data[path] = st.selectbox(
                    field_name,
                    options=execution_options,
                    index=current_index,
                    key=widget_key,
                    disabled=is_id_field,
                    help="ID fields cannot be edited" if is_id_field else "Choose whether task runs in series or parallel"
                )
            elif "specialist_required" in path.lower():
                specialist_options = ["pipefitter", "welder", "inspector"]
                current_index = specialist_options.index(data) if data in specialist_options else 0
                form_data[path] = st.selectbox(
                    field_name,
                    options=specialist_options,
                    index=current_index,
                    key=widget_key,
                    disabled=is_id_field,
                    help="ID fields cannot be edited" if is_id_field else "Choose the specialist type required for this task"
                )
            else:
                # Use text_area for longer strings, text_input for shorter ones
                if len(data) > 100:
                    form_data[path] = st.text_area(
                        field_name,
                        value=data,
                        height=100,
                        key=widget_key,
                        disabled=is_id_field,
                        help="ID fields cannot be edited" if is_id_field else None
                    )
                else:
                    form_data[path] = st.text_input(
                        field_name,
                        value=data,
                        key=widget_key,
                        disabled=is_id_field,
                        help="ID fields cannot be edited" if is_id_field else None
                    )
        elif isinstance(data, int):
            form_data[path] = st.number_input(
                field_name,
                value=data,
                step=1,
                key=widget_key,
                disabled=is_id_field,
                help="ID fields cannot be edited" if is_id_field else None
            )
        elif isinstance(data, float):
            form_data[path] = st.number_input(
                field_name,
                value=data,
                step=0.1,
                key=widget_key,
                disabled=is_id_field,
                help="ID fields cannot be edited" if is_id_field else None
            )
        elif isinstance(data, bool):
            form_data[path] = st.checkbox(
                field_name,
                value=data,
                key=widget_key,
                disabled=is_id_field,
                help="ID fields cannot be edited" if is_id_field else None
            )
    
    return form_data

def reconstruct_json_from_form(form_data, original_data):
    """
    Reconstruct JSON structure from form data while preserving the original structure
    """
    import copy
    result = copy.deepcopy(original_data)
    
    for path, value in form_data.items():
        try:
            # Parse the path and set the value in the result
            keys = []
            current_path = path
            
            # Split by dots first, then handle arrays within each segment
            path_segments = current_path.split('.')
            
            for segment in path_segments:
                if '[' in segment and ']' in segment:
                    # Handle array notation like "tasks[0]" or "items[5]"
                    bracket_start = segment.find('[')
                    bracket_end = segment.find(']')
                    
                    # Add the key before the bracket
                    if bracket_start > 0:
                        keys.append(segment[:bracket_start])
                    
                    # Add the array index
                    index = int(segment[bracket_start+1:bracket_end])
                    keys.append(index)
                    
                    # Handle anything after the closing bracket
                    remaining = segment[bracket_end+1:]
                    if remaining:
                        keys.append(remaining)
                else:
                    # Regular key
                    keys.append(segment)
            
            # Navigate through the structure and set the value
            current = result
            for i, key in enumerate(keys[:-1]):
                if isinstance(key, int):
                    current = current[key]
                else:
                    if key not in current:
                        # This shouldn't happen with our form structure, but just in case
                        current[key] = {}
                    current = current[key]
            
            # Set the final value
            final_key = keys[-1]
            if isinstance(final_key, int):
                current[final_key] = value
            else:
                current[final_key] = value
                
        except Exception as e:
            # Log the specific path that caused the error for debugging
            st.error(f"Error processing path '{path}': {str(e)}")
            raise Exception(f"Error processing path '{path}': {str(e)}")
    
    return result

def calculate_project_statistics(tasks_data):
    """Calculate project statistics from task data"""
    if not tasks_data or 'tasks' not in tasks_data:
        return None
    
    tasks = tasks_data['tasks']
    
    # 1. Calculate total level of effort hours
    total_effort_hours = sum(task.get('level_of_effort_hours', 0) for task in tasks)
    
    # 2. Calculate hours per specialist
    specialist_hours = {'pipefitter': 0, 'welder': 0, 'inspector': 0}
    for task in tasks:
        specialist = task.get('dependencies', {}).get('specialist_required', 'pipefitter')
        hours = task.get('level_of_effort_hours', 0)
        if specialist in specialist_hours:
            specialist_hours[specialist] += hours
    
    # 3. Calculate critical path (total calendar days)
    # Build task lookup and dependency graph
    task_dict = {task['task_id']: task for task in tasks}
    
    # Calculate earliest start time for each task using topological sort
    earliest_start = {}
    in_degree = {}
    
    # Initialize
    for task in tasks:
        task_id = task['task_id']
        prerequisites = task.get('dependencies', {}).get('prerequisite_tasks', [])
        in_degree[task_id] = len(prerequisites)
        earliest_start[task_id] = 0
    
    # Find tasks with no prerequisites
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    
    # Process tasks in dependency order
    while queue:
        current_task_id = queue.pop(0)
        current_task = task_dict[current_task_id]
        current_duration = current_task.get('duration_days', 0)
        current_end_time = earliest_start[current_task_id] + current_duration
        
        # Update dependent tasks
        for task in tasks:
            task_id = task['task_id']
            prerequisites = task.get('dependencies', {}).get('prerequisite_tasks', [])
            
            if current_task_id in prerequisites:
                # Update earliest start time for this dependent task
                earliest_start[task_id] = max(earliest_start[task_id], current_end_time)
                in_degree[task_id] -= 1
                
                # If all prerequisites are processed, add to queue
                if in_degree[task_id] == 0:
                    queue.append(task_id)
    
    # Calculate total project duration (critical path)
    max_end_time = 0
    for task in tasks:
        task_id = task['task_id']
        duration = task.get('duration_days', 0)
        end_time = earliest_start[task_id] + duration
        max_end_time = max(max_end_time, end_time)
    
    return {
        'total_calendar_days': max_end_time,
        'total_effort_hours': total_effort_hours,
        'specialist_hours': specialist_hours,
        'total_tasks': len(tasks)
    }

def generate_extraction(client, prompt, file_input, model, selected_schema, selected_schema_name, is_uploaded_file=False):
    """Generate extraction from document
    
    Args:
        client: The genai client
        prompt: The extraction prompt
        file_input: Either a GCS path (str) or a Part object (for uploaded files)
        model: The model to use
        selected_schema: The selected schema object
        selected_schema_name: The name of the selected schema
        is_uploaded_file: Boolean indicating if file_input is an uploaded file Part
    """
    # Use custom schema if available, otherwise use the selected schema
    if st.session_state.custom_schema:
        schema = st.session_state.custom_schema
    else:
        schema = selected_schema
    
    # Use custom system prompt if available, otherwise select based on schema
    if st.session_state.custom_system_prompt:
        system_prompt = st.session_state.custom_system_prompt
    elif selected_schema_name == 'Task-Based Work Package':
        system_prompt = task_extraction_system_prompt
    else:
        system_prompt = default_system_prompt
    
    # Prepare content with PDF file
    if is_uploaded_file:
        # file_input is already a Part object
        pdf_file = file_input
    else:
        # file_input is a GCS path
        pdf_file = types.Part.from_uri(
            file_uri=file_input,
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
        temperature=0.1,
        #top_p=1,
        #seed=0,
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

# Main content

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection with environment variable defaults
    default_model = os.getenv('DEFAULT_MODEL', 'gemini-2.5-pro-preview-06-05')
    flash_model = os.getenv('FLASH_MODEL', 'gemini-2.5-flash-preview-05-20')
    
    model_options = [flash_model, default_model]
    default_index = 1 if default_model in model_options else 0
    
    model_option = st.selectbox(
        "Select Model",
        model_options,
        index=default_index
    )
    
    # Get available schemas
    available_schemas = get_available_schemas()
    schema_names = list(available_schemas.keys())
    
    # Add custom option if custom schema is loaded
    if st.session_state.custom_schema:
        schema_names.append("Custom (Uploaded)")
    
    # Schema selection
    selected_schema_name = st.selectbox(
        "Select Schema",
        schema_names,
        index=schema_names.index('Task-Based Work Package') if 'Task-Based Work Package' in schema_names else 0
    )
    
    # Get the actual schema object
    if selected_schema_name == "Custom (Uploaded)":
        selected_schema = st.session_state.custom_schema
    else:
        selected_schema = available_schemas[selected_schema_name]
    
    # Show schema details in an expander
    with st.expander("View Schema Details"):
        st.json(selected_schema)
    
    # Show note about system prompt selection
    if selected_schema_name == 'Task-Based Work Package' and not st.session_state.custom_system_prompt:
        st.info("ℹ️ Using specialized task extraction system prompt for Task-Based Work Package schema")
    
    # Region with environment variable default
    default_region = os.getenv('GCP_REGION', 'us-central1')
    region = st.text_input("Region", value=default_region)
    
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
    
    # Cross-page status indicators
    st.divider()
    st.subheader("📊 Page Status")
    
    # Current page status
    if st.session_state.wp_extracted_data:
        st.success("✅ Work Package data available")
        if st.button("🗑️ Clear WP Data", use_container_width=True):
            st.session_state.wp_extracted_data = None
            st.session_state.wp_original_extracted_data = None
            st.session_state.wp_selected_filename = None
            st.success("Work Package data cleared!")
            st.rerun()
    else:
        st.info("ℹ️ No Work Package data")
    
    # Other page status
    if hasattr(st.session_state, 'drawing_extracted_data') and st.session_state.drawing_extracted_data:
        st.success("✅ Drawing Analysis data available")
    else:
        st.info("ℹ️ No Drawing Analysis data")
    
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
    
    # Add tabs for file source selection
    file_source = st.radio(
        "Select file source:",
        ["Google Cloud Storage", "Upload Local File"],
        horizontal=True
    )
    
    file_selected = False
    file_input = None
    is_uploaded_file = False
    selected_filename = None
    
    if file_source == "Google Cloud Storage":
        # List files from bucket
        files = list_files_in_bucket()
        
        if files:
            selected_file = st.selectbox(
                "Select a document from GCS",
                files,
                format_func=lambda x: x.split('/')[-1]  # Show only filename
            )
            
            # Construct full GCS path using environment variable
            if selected_file:
                bucket_name = os.getenv('GCS_BUCKET_NAME', 'wec_demo_files')
                file_input = f"gs://{bucket_name}/{selected_file}"
                selected_filename = selected_file.split('/')[-1]
                file_selected = True
                is_uploaded_file = False
                st.success(f"Selected: {selected_filename}")
        else:
            st.error("No files found in the bucket")
    
    else:  # Upload Local File
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF document for extraction"
        )
        
        if uploaded_file is not None:
            file_input = process_uploaded_file(uploaded_file)
            selected_filename = uploaded_file.name
            file_selected = True
            is_uploaded_file = True
            st.success(f"Uploaded: {selected_filename}")
    
    # Show prompt and extract button only if a file is selected
    if file_selected:
        # Custom prompt - use task-specific prompt for Task-Based Work Package
        default_prompt = (
            "Extract all individual tasks from this Statement of Work document. "
            "For each task, identify the task description, duration in days, level of effort in hours, "
            "dependencies (prerequisite tasks, execution type, and required specialist), and z-location if mentioned. "
            "Respond ONLY with a valid JSON object strictly conforming to the required schema."
            if selected_schema_name == 'Task-Based Work Package'
            else "Review this document, and extract key elements and information. Respond ONLY with a valid JSON object strictly conforming to the required schema."
        )
        
        prompt = st.text_area(
            "Extraction Prompt",
            value=default_prompt,
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
                        client, prompt, file_input, model_option, selected_schema, selected_schema_name, is_uploaded_file
                    )
                    
                    # Parse and store result
                    extracted_result = json.loads(response.text)
                    st.session_state.wp_extracted_data = extracted_result
                    st.session_state.wp_original_extracted_data = json.loads(json.dumps(extracted_result))  # Deep copy
                    st.session_state.wp_selected_filename = selected_filename
                    st.success(f"✅ Extraction complete! ({token_count} input tokens)")
                    
                except Exception as e:
                    st.error(f"Error during extraction: {str(e)}")

with col2:
    st.header("Extraction Results")
    
    if st.session_state.wp_extracted_data:
        # Display options
        view_option = st.radio(
            "View format",
            ["Formatted JSON", "Raw JSON", "Expandable Sections", "Statistics Summary"],
            horizontal=True
        )
        
        if view_option == "Formatted JSON":
            # Editable JSON form
            st.subheader("📝 Edit Extracted Data")
            st.info("💡 You can edit the values below. ID fields are protected and cannot be changed.")
            
            # Create form for editing
            with st.form("edit_json_form"):
                form_data = render_editable_json(st.session_state.wp_extracted_data)
                
                # Save button
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    save_changes = st.form_submit_button("💾 Save Changes", type="primary")
                with col2:
                    reset_clicked = st.form_submit_button("🔄 Reset")
                    if reset_clicked:
                        if st.session_state.wp_original_extracted_data:
                            st.session_state.wp_extracted_data = json.loads(json.dumps(st.session_state.wp_original_extracted_data))  # Deep copy
                            st.success("✅ Data reset to original values!")
                            st.rerun()
                        else:
                            st.warning("⚠️ No original data to reset to")
                with col3:
                    st.caption("Changes are saved to the current session only")
                
                if save_changes:
                    try:
                        # Reconstruct JSON from form data
                        updated_data = reconstruct_json_from_form(form_data, st.session_state.wp_extracted_data)
                        st.session_state.wp_extracted_data = updated_data
                        st.success("✅ Changes saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error saving changes: {str(e)}")
            
            # Show current JSON structure (read-only) for reference
            with st.expander("📋 View Current JSON Structure", expanded=False):
                st.code(json.dumps(st.session_state.wp_extracted_data, indent=2), language="json")
            
        elif view_option == "Raw JSON":
            # Raw JSON in a text area (editable)
            edited_json = st.text_area(
                "JSON Data (editable)",
                value=json.dumps(st.session_state.wp_extracted_data, indent=2),
                height=500
            )
            
        elif view_option == "Statistics Summary":
            # Calculate and display project statistics (only for task-based schemas)
            data = st.session_state.wp_extracted_data
            
            if 'tasks' in data and isinstance(data['tasks'], list):
                stats = calculate_project_statistics(data)
                
                if stats:
                    st.subheader("📊 Project Statistics")
                    
                    # Display in columns for better layout
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            label="Total Calendar Days (Critical Path)",
                            value=f"{stats['total_calendar_days']} days",
                            help="Minimum project duration considering task dependencies"
                        )
                        
                    with col2:
                        st.metric(
                            label="Total Level of Effort",
                            value=f"{stats['total_effort_hours']:,.0f} hours",
                            help="Sum of all task man-hours"
                        )
                        
                    with col3:
                        st.metric(
                            label="Total Tasks",
                            value=stats['total_tasks'],
                            help="Number of individual tasks"
                        )
                    
                    st.divider()
                    
                    # Specialist breakdown
                    st.subheader("👷 Effort by Specialist Type")
                    
                    spec_col1, spec_col2, spec_col3 = st.columns(3)
                    
                    with spec_col1:
                        st.metric(
                            label="🔧 Pipefitter Hours",
                            value=f"{stats['specialist_hours']['pipefitter']:,.0f}",
                            delta=f"{stats['specialist_hours']['pipefitter']/stats['total_effort_hours']*100:.1f}%" if stats['total_effort_hours'] > 0 else "0%"
                        )
                        
                    with spec_col2:
                        st.metric(
                            label="🔥 Welder Hours",
                            value=f"{stats['specialist_hours']['welder']:,.0f}",
                            delta=f"{stats['specialist_hours']['welder']/stats['total_effort_hours']*100:.1f}%" if stats['total_effort_hours'] > 0 else "0%"
                        )
                        
                    with spec_col3:
                        st.metric(
                            label="🔍 Inspector Hours",
                            value=f"{stats['specialist_hours']['inspector']:,.0f}",
                            delta=f"{stats['specialist_hours']['inspector']/stats['total_effort_hours']*100:.1f}%" if stats['total_effort_hours'] > 0 else "0%"
                        )
                    
                    # Additional insights
                    st.divider()
                    st.subheader("📈 Project Insights")
                    
                    insight_col1, insight_col2 = st.columns(2)
                    
                    with insight_col1:
                        # Calculate efficiency metric
                        if stats['total_calendar_days'] > 0:
                            efficiency = stats['total_effort_hours'] / (stats['total_calendar_days'] * 8)  # Assuming 8-hour workdays
                            st.metric(
                                label="Average Daily Resource Usage",
                                value=f"{efficiency:.1f} workers",
                                help="Average number of workers needed per day (assuming 8-hour workdays)"
                            )
                    
                    with insight_col2:
                        # Most used specialist
                        max_specialist = max(stats['specialist_hours'], key=stats['specialist_hours'].get)
                        st.metric(
                            label="Primary Specialist Type",
                            value=max_specialist.title(),
                            help="Specialist type with the most hours"
                        )
                else:
                    st.warning("Unable to calculate statistics from the extracted data.")
            else:
                st.info("📋 Statistics Summary is only available for Task-Based Work Package extractions.")
                st.write("Current schema type does not contain task-level data.")
        
        else:  # Expandable Sections
            # Dynamic display for any schema structure
            data = st.session_state.wp_extracted_data
            
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
            json_str = json.dumps(st.session_state.wp_extracted_data, indent=2)
            # Use the filename from session state
            download_filename = st.session_state.wp_selected_filename.replace('.pdf', '') if st.session_state.wp_selected_filename else "extraction"
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"extraction_{download_filename}.json",
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

