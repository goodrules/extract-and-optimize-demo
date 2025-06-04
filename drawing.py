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
from config.system_prompt import system_prompt as default_system_prompt

# Load environment variables
load_dotenv()

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

@st.cache_data
def list_ifc_files_in_bucket(bucket_name=None, prefix=None):
    """List IFC files in a GCS bucket with given prefix"""
    # Use environment variables with fallback defaults for IFC drawings
    if bucket_name is None:
        bucket_name = os.getenv('GCS_BUCKET_NAME', 'wec_demo_files')
    if prefix is None:
        prefix = os.getenv('GCS_IFC_PREFIX', 'wec_examples/drawings/')
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        file_list = []
        for blob in blobs:
            # Only include actual IFC files, not directories
            if not blob.name.endswith('/') and blob.name.lower().endswith('.ifc'):
                file_list.append(blob.name)
        
        return file_list
    except Exception as e:
        st.error(f"Error accessing bucket: {str(e)}")
        return []

def process_gcs_ifc_file(file_uri):
    """Download and process IFC file from Google Cloud Storage"""
    try:
        # Parse the GCS URI
        if file_uri.startswith('gs://'):
            uri_parts = file_uri[5:].split('/', 1)
            bucket_name = uri_parts[0]
            file_path = uri_parts[1] if len(uri_parts) > 1 else ''
        else:
            raise ValueError("Invalid GCS URI format")
        
        # Download file from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        # Download as text
        content = blob.download_as_text(encoding='utf-8')
        return content
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            content = blob.download_as_text(encoding='latin-1')
            return content
        except Exception as e:
            st.error(f"Error reading file with alternative encoding: {str(e)}")
            return None
    except Exception as e:
        st.error(f"Error downloading file from GCS: {str(e)}")
        return None

def analyze_ifc_structure(ifc_content):
    """Analyze IFC content to provide structure information for better extraction"""
    import re
    
    # Find all IFC entities
    entity_pattern = r'#\d+\s*=\s*([A-Z][A-Z0-9_]*)\s*\('
    entities = re.findall(entity_pattern, ifc_content.upper())
    
    # Count component types
    component_types = {}
    spatial_entities = []
    total_entities = len(entities)
    
    for entity in entities:
        if entity.startswith(('IFCFLOW', 'IFCWALL', 'IFCSLAB', 'IFCBEAM', 'IFCCOLUMN', 
                            'IFCDOOR', 'IFCWINDOW', 'IFCROOF', 'IFCSTAIR', 'IFCRAILING',
                            'IFCFURNISHING', 'IFCMECHANICAL')):
            component_types[entity] = component_types.get(entity, 0) + 1
        elif entity in ('IFCPROJECT', 'IFCSITE', 'IFCBUILDING', 'IFCBUILDINGSTOREY'):
            spatial_entities.append(entity)
    
    return {
        'total_entities': total_entities,
        'component_types': component_types,
        'total_components': sum(component_types.values()),
        'spatial_entities': spatial_entities,
        'has_coordinate_data': 'IFCCARTESIANPOINT' in entities,
        'has_placement_data': 'IFCLOCALPLACEMENT' in entities
    }

def generate_ifc_extraction(client, ifc_content, model, schema):
    """Generate extraction from IFC content string"""
    
    # Analyze IFC structure first to provide guidance to the model
    structure_info = analyze_ifc_structure(ifc_content)
    
    # Store structure info in session state for validation
    st.session_state.ifc_structure_info = structure_info
    
    # Display analysis to user
    st.info(f"📊 IFC Analysis: Found {structure_info['total_components']} components across {len(structure_info['component_types'])} types")
    if structure_info['component_types']:
        with st.expander("View Component Breakdown"):
            for comp_type, count in structure_info['component_types'].items():
                st.write(f"- {comp_type}: {count}")
    
    # Calculate content length and determine if we need to truncate intelligently
    content_length = len(ifc_content)
    max_content_length = 1200000  # 1.2M characters - Leave room for prompt and response
    
    if content_length > max_content_length:
        # Try to include header and as many entity definitions as possible
        header_end = ifc_content.find("DATA;")
        if header_end != -1:
            header_section = ifc_content[:header_end + 5]  # Include "DATA;"
            data_section = ifc_content[header_end + 5:]
            
            # Calculate remaining space for data
            remaining_space = max_content_length - len(header_section) - 2000  # Buffer for prompt
            if remaining_space > 0:
                truncated_content = header_section + data_section[:remaining_space]
                st.warning(f"⚠️ IFC file is large ({content_length:,} chars). Using first {len(truncated_content):,} characters for analysis.")
            else:
                truncated_content = ifc_content[:max_content_length]
                st.warning(f"⚠️ IFC file is very large. Truncated to {max_content_length:,} characters.")
        else:
            truncated_content = ifc_content[:max_content_length]
            st.warning(f"⚠️ IFC file is large. Truncated to {max_content_length:,} characters.")
    else:
        truncated_content = ifc_content
    
    # Create comprehensive prompt for IFC analysis
    component_guidance = ""
    if structure_info['component_types']:
        component_guidance = f"\n\nEXPECTED COMPONENTS TO EXTRACT:\nBased on analysis, this IFC file contains {structure_info['total_components']} total components:\n"
        for comp_type, count in structure_info['component_types'].items():
            component_guidance += f"- {comp_type}: {count} instances\n"
        component_guidance += f"\nYour output MUST include ALL {structure_info['total_components']} components in the components array."
    
    prompt = f"""You are an expert IFC (Industry Foundation Classes) file analyzer. Your task is to extract ALL components and comprehensive information from the provided IFC 3D CAD data.

CRITICAL REQUIREMENTS:
1. Extract ALL {structure_info['total_components']} individual components - do not limit or sample
2. Parse the entire IFC structure systematically 
3. Include every IFCFLOWFITTING, IFCFLOWSEGMENT, IFCWALL, IFCSLAB, IFCBEAM, IFCCOLUMN, IFCDOOR, IFCWINDOW, and other building elements
4. Calculate accurate statistics (totalComponents={structure_info['total_components']}, componentTypes counts, boundingVolume)
5. Extract precise coordinates, materials, and dimensions for each component{component_guidance}

IFC STRUCTURE PARSING INSTRUCTIONS:
- HEADER section: Extract project metadata, creation info, schema version
- IFCPROJECT: Project name, description, global ID
- IFCSITE/IFCBUILDING: Spatial hierarchy and placement
- IFCLOCALPLACEMENT + IFCCARTESIANPOINT: Component coordinates (x,y,z)
- IFCAXIS2PLACEMENT3D: Orientation and rotation data
- Component entities (IFCFLOWFITTING, IFCFLOWSEGMENT, etc.): Names, types, materials
- IFCPROPERTYSET: Additional component properties
- IFCMATERIAL: Material assignments

COMPONENT EXTRACTION STRATEGY:
1. Scan ALL entity definitions starting with # (e.g., #123= IFCFLOWFITTING(...))
2. For each component entity:
   - Extract globalId (unique identifier)
   - Extract name/description
   - Extract type (entity class name)
   - Find referenced IFCLOCALPLACEMENT for coordinates
   - Find referenced IFCMATERIAL for material info
   - Calculate dimensions from geometry references
3. Cross-reference placement and material data by ID numbers

COORDINATE EXTRACTION:
- Find IFCLOCALPLACEMENT entities and their referenced IFCAXIS2PLACEMENT3D
- Extract IFCCARTESIANPOINT coordinates (x, y, z values)
- Handle coordinate transformations and relative placements
- Convert all coordinates to absolute world coordinates where possible

STATISTICS CALCULATION:
- Count every component entity accurately
- Group by IFC entity type (IFCFLOWFITTING, IFCFLOWSEGMENT, etc.)
- Calculate overall bounding box from all component coordinates
- Provide example GlobalId for each component type

IMPORTANT: The components array in your response must include EVERY individual component found in the IFC file. Do not summarize, sample, or limit the number of components.

IFC Data (Length: {content_length:,} characters):
{truncated_content}

Respond ONLY with a valid JSON object strictly conforming to the provided schema. Ensure the components array contains ALL individual components found in the data."""
    
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
    
    # Configure generation with settings optimized for comprehensive extraction
    generate_content_config = types.GenerateContentConfig(
        temperature=0.05,  # Lower temperature for more consistent, complete extraction
        max_output_tokens=65535,  # Maximum tokens for large component lists
        response_modalities=["TEXT"],
        response_mime_type="application/json",
        system_instruction="You are an expert IFC file parser specializing in comprehensive component extraction. Always extract ALL components found in the data without sampling or limiting.",
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

def validate_extraction_completeness(extracted_data, expected_structure):
    """Validate that the extraction captured all expected components"""
    validation_results = {
        'is_complete': True,
        'messages': [],
        'extracted_count': 0,
        'expected_count': expected_structure['total_components']
    }
    
    if 'components' in extracted_data:
        validation_results['extracted_count'] = len(extracted_data['components'])
        
        # Check if we got all expected components
        if validation_results['extracted_count'] < expected_structure['total_components']:
            validation_results['is_complete'] = False
            missing_count = expected_structure['total_components'] - validation_results['extracted_count']
            validation_results['messages'].append(f"⚠️ Missing {missing_count} components ({validation_results['extracted_count']}/{expected_structure['total_components']} extracted)")
        
        # Check component types
        if 'componentSummary' in extracted_data and 'componentTypes' in extracted_data['componentSummary']:
            extracted_types = {item['type']: item['count'] for item in extracted_data['componentSummary']['componentTypes']}
            
            for expected_type, expected_count in expected_structure['component_types'].items():
                extracted_count = extracted_types.get(expected_type, 0)
                if extracted_count < expected_count:
                    validation_results['is_complete'] = False
                    validation_results['messages'].append(f"⚠️ {expected_type}: {extracted_count}/{expected_count} extracted")
                elif extracted_count == expected_count:
                    validation_results['messages'].append(f"✅ {expected_type}: {extracted_count}/{expected_count} extracted")
    else:
        validation_results['is_complete'] = False
        validation_results['messages'].append("❌ No components array found in extraction result")
    
    return validation_results

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection with environment variable defaults
    default_model = os.getenv('DEFAULT_MODEL', 'gemini-2.5-pro-preview-05-06')
    flash_model = os.getenv('FLASH_MODEL', 'gemini-2.5-flash-preview-05-20')
    
    model_options = [flash_model, default_model]
    default_index = 1 if default_model in model_options else 0
    
    model_option = st.selectbox(
        "Select Model",
        model_options,
        index=default_index
    )
    
    # Schema is fixed to IFC schema
    st.info("ℹ️ Using IFC 3D CAD Analysis Schema")
    
    # Region with environment variable default
    default_region = os.getenv('GCP_REGION', 'us-central1')
    region = st.text_input("Region", value=default_region)
    
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
col1, col2 = st.columns([1, 2])

with col1:
    st.header("IFC File Selection")
    
    # Add tabs for file source selection
    file_source = st.radio(
        "Select file source:",
        ["Google Cloud Storage", "Upload Local File"],
        horizontal=True
    )
    
    file_selected = False
    ifc_content = None
    is_uploaded_file = False
    selected_filename = None
    
    if file_source == "Google Cloud Storage":
        # List IFC files from bucket
        files = list_ifc_files_in_bucket()
        
        if files:
            selected_file = st.selectbox(
                "Select an IFC file from GCS",
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
                
                # Download and process the file
                with st.spinner("Downloading IFC file from GCS..."):
                    ifc_content = process_gcs_ifc_file(file_input)
                    if ifc_content:
                        st.info(f"File size: {len(ifc_content):,} characters")
                    else:
                        file_selected = False
                        st.error("Failed to download or process the selected file")
        else:
            st.error("No IFC files found in the bucket")
    
    else:  # Upload Local File
        uploaded_file = st.file_uploader(
            "Choose an IFC file",
            type=['ifc'],
            help="Upload an IFC file for 3D CAD analysis"
        )
        
        if uploaded_file is not None:
            ifc_content = process_uploaded_ifc_file(uploaded_file)
            selected_filename = uploaded_file.name
            file_selected = True
            is_uploaded_file = True
            st.success(f"Uploaded: {selected_filename}")
            st.info(f"File size: {len(ifc_content):,} characters")
    
    # Store structure info in session state for validation
    if 'ifc_structure_info' not in st.session_state:
        st.session_state.ifc_structure_info = None

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
                    
                    # Generate extraction (this also analyzes structure and stores it)
                    response, token_count = generate_ifc_extraction(
                        client, ifc_content, model_option, ifc_schema
                    )
                    
                    # Parse and store result
                    extracted_result = json.loads(response.text)
                    st.session_state.extracted_data = extracted_result
                    st.session_state.original_extracted_data = json.loads(json.dumps(extracted_result))  # Deep copy
                    st.session_state.selected_filename = selected_filename
                    
                    # Validate extraction completeness if we have structure info
                    if hasattr(st.session_state, 'ifc_structure_info') and st.session_state.ifc_structure_info:
                        validation = validate_extraction_completeness(extracted_result, st.session_state.ifc_structure_info)
                        
                        if validation['is_complete']:
                            st.success(f"✅ Analysis complete! All {validation['extracted_count']} components extracted successfully. ({token_count} input tokens)")
                        else:
                            st.warning(f"⚠️ Analysis complete but incomplete extraction: {validation['extracted_count']}/{validation['expected_count']} components. ({token_count} input tokens)")
                        
                        # Show detailed validation results
                        if validation['messages']:
                            with st.expander("📊 Extraction Validation Details"):
                                for message in validation['messages']:
                                    st.write(message)
                    else:
                        st.success(f"✅ Analysis complete! ({token_count} input tokens)")
                    
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")

with col2:
    st.header("Analysis Results")
    
    if st.session_state.extracted_data:
        # Check for incomplete extraction and show helpful guidance
        if hasattr(st.session_state, 'ifc_structure_info') and st.session_state.ifc_structure_info:
            validation = validate_extraction_completeness(st.session_state.extracted_data, st.session_state.ifc_structure_info)
            if not validation['is_complete']:
                st.error(f"""
                🚨 **Incomplete Component Extraction Detected**
                
                Only {validation['extracted_count']}/{validation['expected_count']} components were extracted.
                
                **Troubleshooting suggestions:**
                - Try using the Pro model (it has better accuracy for complex extractions)
                - For very large IFC files, consider pre-processing to split into smaller sections
                - Check the 'Component Summary' tab for detailed extraction status
                """)
        
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
                    st.text(f"Coordinates - E: {site.get('easting', 0):.1f} mm, N: {site.get('northing', 0):.1f} mm, Elev: {site.get('elevation', 0):.1f} mm")
                
                if 'building' in spatial:
                    building = spatial['building']
                    st.markdown(f"**Building:** {building.get('name', 'N/A')}")
                    st.text(f"Position - X: {building.get('x', 0):.1f} mm, Y: {building.get('y', 0):.1f} mm, Z: {building.get('z', 0):.1f} mm")
        
        elif view_option == "Component Summary":
            # Show validation results if available
            if hasattr(st.session_state, 'ifc_structure_info') and st.session_state.ifc_structure_info:
                validation = validate_extraction_completeness(data, st.session_state.ifc_structure_info)
                
                if validation['is_complete']:
                    st.success(f"✅ Complete Extraction: {validation['extracted_count']}/{validation['expected_count']} components")
                else:
                    st.warning(f"⚠️ Incomplete Extraction: {validation['extracted_count']}/{validation['expected_count']} components")
                    
                if validation['messages']:
                    with st.expander("📋 Detailed Extraction Status"):
                        for message in validation['messages']:
                            st.write(message)
            
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
                        volume_mm3 = (bv.get('maxX', 0) - bv.get('minX', 0)) * (bv.get('maxY', 0) - bv.get('minY', 0)) * (bv.get('maxZ', 0) - bv.get('minZ', 0))
                        volume_m3 = volume_mm3 / (1000 * 1000 * 1000)  # Convert mm³ to m³
                        st.metric("Bounding Volume", f"{volume_m3:,.2f} m³")
                
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
                        st.write(f"**Min Coordinates:** X: {bv.get('minX', 0):.1f} mm, Y: {bv.get('minY', 0):.1f} mm, Z: {bv.get('minZ', 0):.1f} mm")
                    with col_bv2:
                        st.write(f"**Max Coordinates:** X: {bv.get('maxX', 0):.1f} mm, Y: {bv.get('maxY', 0):.1f} mm, Z: {bv.get('maxZ', 0):.1f} mm")
        
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
                            st.write(f"**Position:** X: {component.get('x', 0):.1f} mm, Y: {component.get('y', 0):.1f} mm, Z: {component.get('z', 0):.1f} mm")
                            if 'rotationDegrees' in component:
                                rot = component['rotationDegrees']
                                st.write(f"**Rotation:** X: {rot.get('x', 0):.1f}°, Y: {rot.get('y', 0):.1f}°, Z: {rot.get('z', 0):.1f}°")
                            if 'dimensions' in component:
                                dim = component['dimensions']
                                st.write(f"**Dimensions:** L: {dim.get('length', 0):.1f} mm, W: {dim.get('width', 0):.1f} mm, H: {dim.get('height', 0):.1f} mm")
        
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