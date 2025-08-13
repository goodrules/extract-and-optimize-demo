import streamlit as st
from google import genai
from google.genai import types
from google.cloud import storage
import json
import subprocess
import tempfile
import os
from dotenv import load_dotenv
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import io
import base64
import time

import config.schema as schemas
from config.system_prompt import system_prompt as default_system_prompt, ifc_extraction_system_prompt

# Load environment variables
load_dotenv()

#def wide_space_default():
#    st.set_page_config(layout="wide")
#wide_space_default()

# Page header
st.header("🤖 IFC Drawing Analysis")

# Initialize session state (page-specific for Drawing Analysis)
if 'drawing_extracted_data' not in st.session_state:
    st.session_state.drawing_extracted_data = None
if 'drawing_original_extracted_data' not in st.session_state:
    st.session_state.drawing_original_extracted_data = None
if 'drawing_selected_filename' not in st.session_state:
    st.session_state.drawing_selected_filename = None
if 'drawing_pdf_preview_data' not in st.session_state:
    st.session_state.drawing_pdf_preview_data = None

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
    
    prompt = f"""Extract structured component data from the following IFC file.

IFC File Analysis Summary:
- Total components found: {structure_info['total_components']}
- Component types: {len(structure_info['component_types'])}
- File size: {content_length:,} characters{component_guidance}

IFC Data:
{truncated_content}

Extract ALL {structure_info['total_components']} components according to the provided schema. Return a complete JSON object with every component included in the components array."""
    
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
        system_instruction=ifc_extraction_system_prompt,
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
        
        # Check component types by counting actual components (more reliable than trusting summary)
        if 'components' in extracted_data:
            # Count component types from actual components array
            actual_type_counts = {}
            for component in extracted_data['components']:
                comp_type = component.get('type', 'Unknown')
                actual_type_counts[comp_type] = actual_type_counts.get(comp_type, 0) + 1
            
            for expected_type, expected_count in expected_structure['component_types'].items():
                actual_count = actual_type_counts.get(expected_type, 0)
                if actual_count < expected_count:
                    validation_results['is_complete'] = False
                    validation_results['messages'].append(f"⚠️ {expected_type}: {actual_count}/{expected_count} extracted")
                elif actual_count == expected_count:
                    validation_results['messages'].append(f"✅ {expected_type}: {actual_count}/{expected_count} extracted")
                elif actual_count > expected_count:
                    # This shouldn't happen but let's log it
                    validation_results['messages'].append(f"ℹ️ {expected_type}: {actual_count}/{expected_count} extracted (more than expected)")
            
            # Check for unexpected component types
            for actual_type, actual_count in actual_type_counts.items():
                if actual_type not in expected_structure['component_types']:
                    validation_results['messages'].append(f"ℹ️ {actual_type}: {actual_count} extracted (unexpected type)")
    else:
        validation_results['is_complete'] = False
        validation_results['messages'].append("❌ No components array found in extraction result")
    
    return validation_results

def deduplicate_components(extracted_data, details_container=None):
    """Remove duplicate components from extracted IFC data
    
    Args:
        extracted_data: The extracted JSON data containing components
        details_container: Optional container to log deduplication messages
        
    Returns:
        dict: Updated data with duplicates removed
    """
    if 'components' not in extracted_data or not extracted_data['components']:
        return extracted_data
    
    components = extracted_data['components']
    original_count = len(components)
    
    # Track deduplication process
    log_container = details_container if details_container else st
    log_container.info(f"🔍 Starting deduplication process for {original_count} components...")
    
    # Step 1: Remove exact GlobalId duplicates
    unique_components = {}
    globalid_duplicates = 0
    
    for component in components:
        global_id = component.get('globalId', '')
        if global_id and global_id in unique_components:
            globalid_duplicates += 1
            # Merge information from duplicate, keeping most complete data
            existing = unique_components[global_id]
            merged = merge_component_data(existing, component)
            unique_components[global_id] = merged
        else:
            unique_components[global_id] = component
    
    if globalid_duplicates > 0:
        log_container.warning(f"⚠️ Found {globalid_duplicates} GlobalId duplicates, merged with existing components")
    
    # Skip spatial/geometric deduplication - only remove true GlobalId duplicates
    # Components with same dimensions are legitimate (e.g., identical windows, pipes, etc.)
    final_components = list(unique_components.values())
    final_count = len(final_components)
    
    # Update the extracted data
    extracted_data['components'] = final_components
    
    # Recalculate component summary statistics
    if 'componentSummary' in extracted_data:
        extracted_data['componentSummary'] = recalculate_component_summary(final_components)
        
        # Debug: Check if coordinates are present
        coord_count = sum(1 for c in final_components if 'x' in c and 'y' in c and 'z' in c)
        if coord_count == 0:
            log_container.warning(f"⚠️ No components have coordinate data (x, y, z) - bounding volume will be zero")
        elif coord_count < len(final_components):
            log_container.info(f"ℹ️ {coord_count}/{len(final_components)} components have coordinate data")
    
    # Log results with component type breakdown
    duplicates_removed = original_count - final_count
    if duplicates_removed > 0:
        log_container.success(f"✅ Deduplication complete: removed {duplicates_removed} GlobalId duplicates ({original_count} → {final_count} components)")
        
        # Show type breakdown after deduplication
        if 'componentSummary' in extracted_data and 'componentTypes' in extracted_data['componentSummary']:
            log_container.info("📊 Final component counts by type:")
            for comp_type in extracted_data['componentSummary']['componentTypes']:
                log_container.info(f"  • {comp_type['type']}: {comp_type['count']}")
    else:
        log_container.info(f"ℹ️ No GlobalId duplicates found - all {final_count} components are unique")
    
    return extracted_data

def merge_component_data(component1, component2):
    """Merge data from two similar components, keeping most complete information"""
    merged = component1.copy()
    
    # Merge fields, preferring non-empty values
    for key, value in component2.items():
        if key not in merged or not merged[key]:
            merged[key] = value
        elif value and key in ['name', 'material', 'storey']:
            # For text fields, prefer longer/more descriptive values
            if len(str(value)) > len(str(merged[key])):
                merged[key] = value
    
    return merged

def find_similar_components(target_component, components_list, target_index, tolerance):
    """Find components with similar coordinates and type"""
    similar_indices = []
    
    target_x = target_component.get('x', 0)
    target_y = target_component.get('y', 0) 
    target_z = target_component.get('z', 0)
    target_type = target_component.get('type', '')
    target_name = target_component.get('name', '')
    
    for i, component in enumerate(components_list):
        if i == target_index:
            continue
            
        # Check if same type
        if component.get('type', '') != target_type:
            continue
            
        # Check coordinate proximity
        comp_x = component.get('x', 0)
        comp_y = component.get('y', 0)
        comp_z = component.get('z', 0)
        
        distance = ((target_x - comp_x)**2 + (target_y - comp_y)**2 + (target_z - comp_z)**2)**0.5
        
        if distance <= tolerance:
            # Also check if names are similar (for additional confidence)
            name_similarity = calculate_name_similarity(target_name, component.get('name', ''))
            if name_similarity > 0.7 or distance < tolerance / 2:  # Very close or similar names
                similar_indices.append(i)
    
    return similar_indices

def calculate_name_similarity(name1, name2):
    """Calculate similarity between two component names (simple approach)"""
    if not name1 or not name2:
        return 0.0
    
    name1_clean = name1.lower().strip()
    name2_clean = name2.lower().strip()
    
    if name1_clean == name2_clean:
        return 1.0
    
    # Simple token-based similarity
    tokens1 = set(name1_clean.split())
    tokens2 = set(name2_clean.split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union) if union else 0.0

def recalculate_component_summary(components):
    """Recalculate component summary statistics after deduplication"""
    if not components:
        return {
            'totalComponents': 0,
            'componentTypes': [],
            'boundingVolume': {
                'minX': 0, 'minY': 0, 'minZ': 0,
                'maxX': 0, 'maxY': 0, 'maxZ': 0
            }
        }
    
    # Count by type
    type_counts = {}
    type_examples = {}
    
    # Calculate bounding volume - collect all valid coordinates
    xs = []
    ys = []
    zs = []
    
    for component in components:
        # Check if component has valid coordinate data
        x = component.get('x')
        y = component.get('y')
        z = component.get('z')
        
        # Only include coordinates that are present and numeric
        if x is not None and isinstance(x, (int, float)):
            xs.append(x)
        if y is not None and isinstance(y, (int, float)):
            ys.append(y)
        if z is not None and isinstance(z, (int, float)):
            zs.append(z)
    
    for component in components:
        comp_type = component.get('type', 'Unknown')
        type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        
        if comp_type not in type_examples and component.get('globalId'):
            type_examples[comp_type] = component['globalId']
    
    # Build component types array
    component_types = []
    for comp_type, count in type_counts.items():
        type_entry = {
            'type': comp_type,
            'count': count
        }
        if comp_type in type_examples:
            type_entry['exampleGlobalId'] = type_examples[comp_type]
        component_types.append(type_entry)
    
    # Sort by count (descending)
    component_types.sort(key=lambda x: x['count'], reverse=True)
    
    return {
        'totalComponents': len(components),
        'componentTypes': component_types,
        'boundingVolume': calculate_bounding_volume(xs, ys, zs)
    }

def calculate_bounding_volume(xs, ys, zs):
    """Calculate bounding volume from coordinate arrays - simplified approach"""
    
    # If no coordinates at all, return zero bounding volume
    if not xs or not ys or not zs:
        return {
            'minX': 0, 'minY': 0, 'minZ': 0,
            'maxX': 0, 'maxY': 0, 'maxZ': 0
        }
    
    # Simple min/max calculation
    return {
        'minX': min(xs),
        'minY': min(ys), 
        'minZ': min(zs),
        'maxX': max(xs),
        'maxY': max(ys),
        'maxZ': max(zs)
    }

def check_pdf_exists_in_gcs(ifc_file_path):
    """Check if corresponding PDF file exists in GCS for the given IFC file"""
    try:
        # Convert IFC path to PDF path (same name, different extension)
        pdf_file_path = ifc_file_path.replace('.ifc', '.pdf').replace('.IFC', '.pdf')
        
        # Parse the GCS URI to get bucket and blob path
        if pdf_file_path.startswith('gs://'):
            uri_parts = pdf_file_path[5:].split('/', 1)
            bucket_name = uri_parts[0]
            blob_path = uri_parts[1] if len(uri_parts) > 1 else ''
        else:
            return False
        
        # Check if PDF blob exists
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        return blob.exists()
    except Exception as e:
        st.warning(f"Error checking for PDF: {str(e)}")
        return False

def download_pdf_from_gcs(pdf_file_path):
    """Download PDF file from GCS and return bytes"""
    try:
        # Parse the GCS URI
        if pdf_file_path.startswith('gs://'):
            uri_parts = pdf_file_path[5:].split('/', 1)
            bucket_name = uri_parts[0]
            blob_path = uri_parts[1] if len(uri_parts) > 1 else ''
        else:
            raise ValueError("Invalid GCS URI format")
        
        # Download PDF as bytes
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        return blob.download_as_bytes()
    except Exception as e:
        st.error(f"Error downloading PDF: {str(e)}")
        return None

@st.cache_data
def convert_pdf_to_images(pdf_bytes, max_pages=3):
    """Convert PDF bytes to images for display. Cache the result for performance."""
    try:
        # Validate input
        if not pdf_bytes:
            st.error("PDF bytes are empty")
            return [], 0
        
        st.info(f"Processing PDF ({len(pdf_bytes):,} bytes)...")
        
        # Open PDF from bytes with error handling
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as open_error:
            st.error(f"Failed to open PDF: {str(open_error)}")
            return [], 0
        
        # Check if PDF has pages
        if pdf_doc.page_count == 0:
            st.error("PDF has no pages")
            pdf_doc.close()
            return [], 0
        
        # Store page count before we start processing (and potentially close the document)
        total_page_count = pdf_doc.page_count
        st.info(f"PDF has {total_page_count} pages, converting first {min(max_pages, total_page_count)}...")
        
        images = []
        pages_to_convert = min(max_pages, total_page_count)
        
        for page_num in range(pages_to_convert):
            try:
                page = pdf_doc[page_num]
                
                # Use a more conservative zoom level first
                mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom instead of 2x
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes first, then to PIL Image
                png_bytes = pix.tobytes("png")
                
                # Create PIL Image from PNG bytes
                img = Image.open(io.BytesIO(png_bytes))
                images.append(img)
                
                st.success(f"✅ Converted page {page_num + 1}")
                
            except Exception as page_error:
                st.warning(f"Failed to convert page {page_num + 1}: {str(page_error)}")
                continue
        
        # Close the document after processing
        pdf_doc.close()
        
        if not images:
            st.error("No pages could be converted to images")
            return [], total_page_count
        
        st.success(f"Successfully converted {len(images)} pages")
        return images, total_page_count
        
    except Exception as e:
        st.error(f"Error in PDF conversion workflow: {str(e)}")
        import traceback
        st.error(f"Detailed error: {traceback.format_exc()}")
        return [], 0

def simple_pdf_display(pdf_bytes, filename):
    """Fallback method to display PDF using browser's built-in PDF viewer"""
    try:
        # Encode PDF as base64 for embedding
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create a download link and iframe for PDF viewing
        st.subheader("📋 PDF Drawing")
        
        # Provide download option
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf"
        )
        
        # Try to embed PDF (may not work in all browsers)
        st.markdown("**PDF Preview:**")
        pdf_display = f"""
        <iframe src="data:application/pdf;base64,{b64_pdf}" 
                width="100%" height="600" type="application/pdf">
        <p>Your browser does not support PDFs. 
        <a href="data:application/pdf;base64,{b64_pdf}">Download the PDF</a>.</p>
        </iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        return True
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")
        return False

def convert_pdf_to_images_with_container(pdf_bytes, max_pages=3, container=None):
    """Convert PDF bytes to images with messages routed to a specific container"""
    if container is None:
        container = st  # Default to main streamlit if no container provided
    
    try:
        # Validate input
        if not pdf_bytes:
            container.error("PDF bytes are empty")
            return [], 0
        
        container.info(f"📄 Processing PDF ({len(pdf_bytes):,} bytes)...")
        
        # Open PDF from bytes with error handling
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as open_error:
            container.error(f"❌ Failed to open PDF: {str(open_error)}")
            return [], 0
        
        # Check if PDF has pages
        if pdf_doc.page_count == 0:
            container.error("❌ PDF has no pages")
            pdf_doc.close()
            return [], 0
        
        # Store page count before we start processing
        total_page_count = pdf_doc.page_count
        container.info(f"📊 PDF has {total_page_count} pages, converting first {min(max_pages, total_page_count)}...")
        
        images = []
        pages_to_convert = min(max_pages, total_page_count)
        
        for page_num in range(pages_to_convert):
            try:
                page = pdf_doc[page_num]
                
                # Use a more conservative zoom level first
                mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom instead of 2x
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes first, then to PIL Image
                png_bytes = pix.tobytes("png")
                
                # Create PIL Image from PNG bytes
                img = Image.open(io.BytesIO(png_bytes))
                images.append(img)
                
                container.success(f"✅ Converted page {page_num + 1}")
                
            except Exception as page_error:
                container.warning(f"⚠️ Failed to convert page {page_num + 1}: {str(page_error)}")
                continue
        
        # Close the document after processing
        pdf_doc.close()
        
        if not images:
            container.error("❌ No pages could be converted to images")
            return [], total_page_count
        
        container.success(f"🎉 Successfully converted {len(images)} pages")
        return images, total_page_count
        
    except Exception as e:
        container.error(f"❌ Error in PDF conversion workflow: {str(e)}")
        import traceback
        container.error(f"📋 Detailed error: {traceback.format_exc()}")
        return [], 0

def process_pdf_preview(ifc_filename, file_source, gcs_file_path=None, details_container=None):
    """Process PDF and return preview components instead of displaying directly
    
    Args:
        ifc_filename: Name of the IFC file
        file_source: Source type ("Google Cloud Storage" or "Upload Local File")
        gcs_file_path: Path to GCS file (if applicable)
        details_container: Streamlit container to place processing messages in
        
    Returns:
        dict: Contains 'has_preview', 'images', 'total_pages', 'pdf_filename', 'fallback_data'
    """
    
    if file_source == "Google Cloud Storage" and gcs_file_path:
        # For GCS files, check if corresponding PDF exists
        pdf_gcs_path = gcs_file_path.replace('.ifc', '.pdf').replace('.IFC', '.pdf')
        
        if check_pdf_exists_in_gcs(pdf_gcs_path):
            # Log PDF discovery in details container
            if details_container:
                details_container.success("📄 Found corresponding PDF drawing!")
            
            # Download and process PDF (messages go to details container)
            pdf_bytes = download_pdf_from_gcs(pdf_gcs_path)
            
            if pdf_bytes:
                # Route processing messages to details container
                container_for_messages = details_container if details_container else st
                images, total_pages = convert_pdf_to_images_with_container(pdf_bytes, container=container_for_messages)
                
                pdf_filename = ifc_filename.replace('.ifc', '.pdf').replace('.IFC', '.pdf')
                
                if images:
                    return {
                        'has_preview': True,
                        'images': images,
                        'total_pages': total_pages,
                        'pdf_filename': pdf_filename,
                        'fallback_data': None
                    }
                else:
                    # Fallback data for simple PDF display
                    if details_container:
                        details_container.warning("Could not convert PDF to images, trying alternative display method...")
                    return {
                        'has_preview': True,
                        'images': [],
                        'total_pages': total_pages,
                        'pdf_filename': pdf_filename,
                        'fallback_data': {'pdf_bytes': pdf_bytes, 'filename': pdf_filename}
                    }
        else:
            if details_container:
                details_container.info("ℹ️ No corresponding PDF drawing found")
            return {'has_preview': False}
    
    elif file_source == "Upload Local File":
        # For local uploads, offer to upload corresponding PDF
        st.info("💡 **Optional**: Upload the corresponding PDF drawing for preview")
        
        uploaded_pdf = st.file_uploader(
            "Upload corresponding PDF (optional)",
            type=['pdf'],
            help=f"Upload the PDF drawing that corresponds to {ifc_filename}",
            key="pdf_uploader"
        )
        
        if uploaded_pdf is not None:
            # Log upload success in details container
            if details_container:
                details_container.success("📄 PDF drawing uploaded!")
            
            # Read PDF bytes with error handling (messages go to details container)
            try:
                pdf_bytes = uploaded_pdf.read()
                uploaded_pdf.seek(0)  # Reset file pointer
                
                if len(pdf_bytes) == 0:
                    if details_container:
                        details_container.error("❌ Uploaded PDF file is empty")
                    return {'has_preview': False}
                else:
                    # Route processing messages to details container
                    container_for_messages = details_container if details_container else st
                    images, total_pages = convert_pdf_to_images_with_container(pdf_bytes, container=container_for_messages)
                    
                    if images:
                        return {
                            'has_preview': True,
                            'images': images,
                            'total_pages': total_pages,
                            'pdf_filename': uploaded_pdf.name,
                            'fallback_data': None
                        }
                    else:
                        # Fallback data for simple PDF display
                        if details_container:
                            details_container.warning("⚠️ Could not convert PDF to images, trying alternative display method...")
                        return {
                            'has_preview': True,
                            'images': [],
                            'total_pages': total_pages,
                            'pdf_filename': uploaded_pdf.name,
                            'fallback_data': {'pdf_bytes': pdf_bytes, 'filename': uploaded_pdf.name}
                        }
                        
            except Exception as read_error:
                if details_container:
                    details_container.error(f"❌ Error reading uploaded PDF: {str(read_error)}")
                return {'has_preview': False}
    
    # Default return if no PDF processing occurred
    return {'has_preview': False}

def display_pdf_preview_components(preview_data):
    """Display PDF preview components from processed data in an expander"""
    if not preview_data.get('has_preview', False):
        return
    
    images = preview_data.get('images', [])
    total_pages = preview_data.get('total_pages', 0)
    pdf_filename = preview_data.get('pdf_filename', 'PDF')
    fallback_data = preview_data.get('fallback_data')
    
    # Create expander for drawing preview with page count in title
    if images:
        if len(images) > 1:
            expander_title = f"📋 Drawing Preview ({len(images)} of {total_pages} pages)"
        else:
            expander_title = f"📋 Drawing Preview ({total_pages} page{'s' if total_pages != 1 else ''})"
    else:
        expander_title = "📋 Drawing Preview"
    
    with st.expander(expander_title, expanded=True):
        if images:
            # Show page navigation if multiple pages
            if len(images) > 1:
                page_num = st.selectbox(
                    f"Select page to view:",
                    range(len(images)),
                    format_func=lambda x: f"Page {x + 1}",
                    key="pdf_page_preview"
                )
                st.image(images[page_num], caption=f"Page {page_num + 1} of {pdf_filename}")
            else:
                st.image(images[0], caption=f"{pdf_filename}")
            
            if total_pages > len(images):
                st.info(f"ℹ️ Showing first {len(images)} pages of {total_pages} total pages")
        
        elif fallback_data:
            # Use fallback display method
            simple_pdf_display(fallback_data['pdf_bytes'], fallback_data['filename'])

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # Model selection with environment variable defaults
    default_model = os.getenv('DEFAULT_MODEL', 'gemini-2.5-pro')
    flash_model = os.getenv('FLASH_MODEL', 'gemini-2.5-flash')
    
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
    default_region = os.getenv('GCP_REGION', 'global')
    region = st.text_input("Region", value=default_region)
    
    # Get project ID
    project_id = get_project_id()
    st.info(f"Project ID: {project_id}")
    
    # Cross-page status indicators
    st.divider()
    st.subheader("📊 Page Status")
    
    # Current page status
    if st.session_state.drawing_extracted_data:
        st.success("✅ Drawing Analysis data available")
        if st.button("🗑️ Clear Drawing Data", use_container_width=True):
            st.session_state.drawing_extracted_data = None
            st.session_state.drawing_original_extracted_data = None
            st.session_state.drawing_selected_filename = None
            st.session_state.drawing_pdf_preview_data = None
            st.success("Drawing Analysis data cleared!")
            st.rerun()
    else:
        st.info("ℹ️ No Drawing Analysis data")
    
    # Other page status
    if hasattr(st.session_state, 'wp_extracted_data') and st.session_state.wp_extracted_data:
        st.success("✅ Work Package data available")
    else:
        st.info("ℹ️ No Work Package data")
    
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
    
    # Initialize PDF preview data
    # Will be set later if a file is selected and processed
    
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
                
                # Download and process the file
                with st.spinner("Downloading IFC file from GCS..."):
                    ifc_content = process_gcs_ifc_file(file_input)
                    if ifc_content:
                        # Create expander for file details and processing messages
                        details_expander = st.expander("📁 File Details", expanded=False)
                        
                        with details_expander:
                            st.success(f"✅ Selected: {selected_filename}")
                            st.info(f"📊 File size: {len(ifc_content):,} characters")
                            st.caption(f"📍 Source: Google Cloud Storage")
                            st.caption(f"🔗 Path: {file_input}")
                        
                        # Process PDF and store preview data for right column
                        st.session_state.drawing_pdf_preview_data = process_pdf_preview(
                            selected_filename, file_source, file_input, details_container=details_expander
                        )
                    else:
                        file_selected = False
                        st.session_state.drawing_pdf_preview_data = None
                        st.error("Failed to download or process the selected file")
        else:
            st.error("No IFC files found in the bucket")
            st.session_state.drawing_pdf_preview_data = None
    
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
            
            # Create expander for file details and processing messages
            details_expander = st.expander("📁 File Details", expanded=False)
            
            with details_expander:
                st.success(f"✅ Uploaded: {selected_filename}")
                st.info(f"📊 File size: {len(ifc_content):,} characters")
                st.caption(f"📍 Source: Local Upload")
                st.caption(f"📝 File type: {uploaded_file.type if uploaded_file.type else 'IFC'}")
            
            # Process PDF and store preview data for right column
            st.session_state.drawing_pdf_preview_data = process_pdf_preview(
                selected_filename, file_source, details_container=details_expander
            )
        else:
            # Clear PDF preview if no file uploaded
            st.session_state.drawing_pdf_preview_data = None
    
    # Store structure info in session state for validation
    if 'ifc_structure_info' not in st.session_state:
        st.session_state.ifc_structure_info = None

    # Show extract button only if a file is selected
    if file_selected:
        # Add visual separator before analysis section
        st.divider()
        st.subheader("🔍 Analysis")
        
        # Extract button
        if st.button("🚀 Analyze IFC Data", type="primary", use_container_width=True):
            # Start timing
            start_time = time.time()
            
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
                    
                    # Apply deduplication to remove duplicate components
                    try:
                        deduplicated_result = deduplicate_components(extracted_result)
                    except Exception as dedup_error:
                        st.warning(f"⚠️ Deduplication failed: {str(dedup_error)}. Using original data.")
                        deduplicated_result = extracted_result
                    
                    st.session_state.drawing_extracted_data = deduplicated_result
                    st.session_state.drawing_original_extracted_data = json.loads(json.dumps(extracted_result))  # Deep copy of original (pre-deduplication)
                    st.session_state.drawing_selected_filename = selected_filename
                    
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    
                    # Validate extraction completeness if we have structure info
                    if hasattr(st.session_state, 'ifc_structure_info') and st.session_state.ifc_structure_info:
                        validation = validate_extraction_completeness(deduplicated_result, st.session_state.ifc_structure_info)
                        
                        if validation['is_complete']:
                            st.success(f"✅ Analysis complete! All {validation['extracted_count']} components extracted successfully. ({token_count} input tokens) • ⏱️ {execution_time:.1f}s")
                        else:
                            st.warning(f"⚠️ Analysis complete but incomplete extraction: {validation['extracted_count']}/{validation['expected_count']} components. ({token_count} input tokens) • ⏱️ {execution_time:.1f}s")
                        
                        # Show detailed validation results
                        if validation['messages']:
                            with st.expander("📊 Extraction Validation Details"):
                                for message in validation['messages']:
                                    st.write(message)
                    else:
                        st.success(f"✅ Analysis complete! ({token_count} input tokens) • ⏱️ {execution_time:.1f}s")
                    
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")

with col2:
    st.header("Analysis Results")
    
    # Display PDF preview above analysis results
    if st.session_state.drawing_pdf_preview_data:
        display_pdf_preview_components(st.session_state.drawing_pdf_preview_data)
        st.divider()  # Add separator between preview and analysis results
    
    if st.session_state.drawing_extracted_data:
        # Check for incomplete extraction and show helpful guidance
        if hasattr(st.session_state, 'ifc_structure_info') and st.session_state.ifc_structure_info:
            validation = validate_extraction_completeness(st.session_state.drawing_extracted_data, st.session_state.ifc_structure_info)
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
        
        data = st.session_state.drawing_extracted_data
        
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
                        width = bv.get('maxX', 0) - bv.get('minX', 0)
                        height = bv.get('maxY', 0) - bv.get('minY', 0)
                        depth = bv.get('maxZ', 0) - bv.get('minZ', 0)
                        
                        # Calculate volume
                        volume_raw = width * height * depth
                        
                        # Smart unit detection and conversion
                        if volume_raw > 1000000:  # Likely in mm³, convert to m³
                            volume_display = volume_raw / (1000 * 1000 * 1000)
                            unit = "m³"
                        elif volume_raw > 1:  # Likely in m³ already
                            volume_display = volume_raw
                            unit = "m³"
                        else:  # Very small or zero
                            volume_display = volume_raw
                            unit = "units³"
                        
                        if volume_display > 0:
                            st.metric("Bounding Volume", f"{volume_display:,.2f} {unit}")
                        else:
                            st.metric("Bounding Volume", "0.00 m³")
                            st.caption("⚠️ No valid coordinates found")
                
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
                    st.subheader("📐 Bounding Volume Details")
                    bv = summary['boundingVolume']
                    
                    # Show coordinate ranges
                    col_bv1, col_bv2 = st.columns(2)
                    with col_bv1:
                        st.write(f"**Min Coordinates:**")
                        st.write(f"• X: {bv.get('minX', 0):,.1f} mm")
                        st.write(f"• Y: {bv.get('minY', 0):,.1f} mm")
                        st.write(f"• Z: {bv.get('minZ', 0):,.1f} mm")
                    with col_bv2:
                        st.write(f"**Max Coordinates:**")
                        st.write(f"• X: {bv.get('maxX', 0):,.1f} mm")
                        st.write(f"• Y: {bv.get('maxY', 0):,.1f} mm")
                        st.write(f"• Z: {bv.get('maxZ', 0):,.1f} mm")
                    
                    # Show dimensions
                    width = bv.get('maxX', 0) - bv.get('minX', 0)
                    height = bv.get('maxY', 0) - bv.get('minY', 0)
                    depth = bv.get('maxZ', 0) - bv.get('minZ', 0)
                    
                    st.write(f"**Dimensions:**")
                    st.write(f"• Width (X): {width:,.1f} mm")
                    st.write(f"• Height (Y): {height:,.1f} mm") 
                    st.write(f"• Depth (Z): {depth:,.1f} mm")
        
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
            json_str = json.dumps(st.session_state.drawing_extracted_data, indent=2)
            download_filename = st.session_state.drawing_selected_filename.replace('.ifc', '') if st.session_state.drawing_selected_filename else "ifc_analysis"
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