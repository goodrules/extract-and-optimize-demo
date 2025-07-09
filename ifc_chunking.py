"""
IFC Chunking Strategy Implementation
Provides hierarchical chunking for efficient IFC file processing with async support.
"""

import re
import asyncio
import time
import json
from typing import Dict, List, Tuple, Set, Any, Optional
from google import genai
from google.genai import types
from config.system_prompt import ifc_extraction_system_prompt


def create_ifc_entity_index(ifc_content: str) -> Dict[str, str]:
    """
    Pre-parse IFC file to create entity ID -> full line mapping.
    
    Args:
        ifc_content: Raw IFC file content
        
    Returns:
        Dictionary mapping entity IDs to full lines
    """
    entity_index = {}
    
    # Find DATA section
    data_start = ifc_content.find('DATA;')
    data_end = ifc_content.find('ENDSEC;', data_start)
    
    if data_start == -1 or data_end == -1:
        return entity_index
    
    # Extract DATA section
    data_section = ifc_content[data_start + 5:data_end].strip()
    
    # Parse entities - handle multi-line entities
    current_entity = []
    for line in data_section.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        current_entity.append(line)
        
        # Check if entity is complete (ends with ;)
        if line.endswith(';'):
            full_entity = ' '.join(current_entity)
            # Extract entity ID
            match = re.match(r'(#\d+)\s*=', full_entity)
            if match:
                entity_id = match.group(1)
                entity_index[entity_id] = full_entity
            current_entity = []
    
    return entity_index


def build_relationship_maps(entity_index: Dict[str, str]) -> Dict[str, Dict[str, List[str]]]:
    """
    Build maps of relationships between entities.
    
    Returns:
        Dictionary with 'properties', 'aggregations', and 'property_sets' mappings
    """
    rel_maps = {
        'properties': {},  # Object ID -> [Property Set IDs]
        'aggregations': {},  # Parent ID -> [Child IDs]
        'property_sets': {}  # Property Set ID -> [Property IDs]
    }
    
    for entity_id, line in entity_index.items():
        # Parse IFCRELDEFINESBYPROPERTIES
        if 'IFCRELDEFINESBYPROPERTIES' in line:
            # Extract related objects and property set
            # Pattern can be:
            # IFCRELDEFINESBYPROPERTIES('id',#6,$,$,(#obj1,#obj2),#propset);
            # or IFCRELDEFINESBYPROPERTIES('id',#6,$,$,(#obj),#propset);
            # Look for pattern with parentheses around object IDs
            match = re.search(r',\s*\(([^)]+)\),\s*(#\d+)', line)
            if match:
                related_objects_str = match.group(1)
                property_set = match.group(2)
                related_objects = re.findall(r'#\d+', related_objects_str)
                
                for obj_id in related_objects:
                    if obj_id not in rel_maps['properties']:
                        rel_maps['properties'][obj_id] = []
                    rel_maps['properties'][obj_id].append(property_set)
        
        # Parse IFCRELAGGREGATES
        elif 'IFCRELAGGREGATES' in line:
            # Pattern: IFCRELAGGREGATES('id',#6,$,$,#parent,(#child1,#child2));
            match = re.search(r',\s*(#\d+),\s*\(([^)]+)\)', line)
            if match:
                parent_id = match.group(1)
                children_str = match.group(2)
                children = re.findall(r'#\d+', children_str)
                rel_maps['aggregations'][parent_id] = children
        
        # Parse IFCPROPERTYSET
        elif 'IFCPROPERTYSET' in line:
            # Extract property IDs from the property set
            # Pattern: IFCPROPERTYSET('id',#6,'name','desc',(#prop1,#prop2));
            # Look for the last occurrence of parentheses with # references
            match = re.search(r',\s*\(([^)]*#\d+[^)]*)\)[^,)]*\)', line)
            if match:
                property_ids_str = match.group(1)
                property_ids = re.findall(r'#\d+', property_ids_str)
                rel_maps['property_sets'][entity_id] = property_ids
    
    return rel_maps


def extract_properties_for_entity(
    entity_id: str, 
    entity_index: Dict[str, str], 
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> Dict[str, str]:
    """
    Extract all properties for a given entity.
    
    Returns:
        Dictionary of property name -> value
    """
    properties = {}
    
    # Get property sets for this entity
    property_sets = rel_maps['properties'].get(entity_id, [])
    
    for pset_id in property_sets:
        # Get properties in this set
        property_ids = rel_maps['property_sets'].get(pset_id, [])
        
        for prop_id in property_ids:
            prop_line = entity_index.get(prop_id, '')
            
            # Extract property name and value
            # Multiple patterns for IFCPROPERTYSINGLEVALUE:
            # Pattern 1: IFCPROPERTYSINGLEVALUE('PropName',$,IFCLABEL('Value'),$);
            # Pattern 2: IFCPROPERTYSINGLEVALUE('PropName',$,IFCTEXT('Value'),$);
            # Pattern 3: IFCPROPERTYSINGLEVALUE('PropName','desc',IFCTEXT('Value'),$);
            
            # Try IFCLABEL pattern
            match = re.search(r"IFCPROPERTYSINGLEVALUE\('([^']+)'[^,]*,[^,]*,\s*IFCLABEL\('([^']+)'\)", prop_line)
            if not match:
                # Try IFCTEXT pattern
                match = re.search(r"IFCPROPERTYSINGLEVALUE\('([^']+)'[^,]*,[^,]*,\s*IFCTEXT\('([^']+)'\)", prop_line)
            
            if match:
                prop_name = match.group(1)
                prop_value = match.group(2)
                properties[prop_name] = prop_value
    
    return properties


def identify_core_assemblies(
    entity_index: Dict[str, str], 
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> List[Dict[str, str]]:
    """
    Identify IFCELEMENTASSEMBLY objects with E3DType of PIPE or BRANCH.
    
    Returns:
        List of assemblies with id, type, and name
    """
    core_assemblies = []
    
    # Debug: Track all assemblies found
    all_assemblies_debug = []
    
    for entity_id, line in entity_index.items():
        if 'IFCELEMENTASSEMBLY' in line:
            # Get properties for this assembly
            properties = extract_properties_for_entity(entity_id, entity_index, rel_maps)
            
            # Debug: Track all assemblies and their E3DType
            e3d_type = properties.get('E3DType', 'NOT_FOUND')
            all_assemblies_debug.append(f"{entity_id}: E3DType={e3d_type}")
            
            # Check if it has PIPE or BRANCH type
            if e3d_type in ['PIPE', 'BRANCH']:
                core_assemblies.append({
                    'id': entity_id,
                    'type': e3d_type,
                    'name': properties.get('NAME', properties.get('Name', 'Unknown'))
                })
    
    # Debug logging (will be captured by the caller)
    if all_assemblies_debug:
        import streamlit as st
        with st.expander("🔍 Debug: All IFCELEMENTASSEMBLY entities found"):
            for debug_info in all_assemblies_debug:
                st.write(debug_info)
    
    return core_assemblies


def assemble_hierarchical_chunk(
    parent_id: str,
    entity_index: Dict[str, str],
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> str:
    """
    Assemble a complete chunk for a parent object and all its children.
    
    Returns:
        Concatenated text of all related entities
    """
    chunk_lines = []
    processed_ids = set()  # Track processed entities to avoid duplicates
    
    def add_placement_entities(entity_line: str, depth=0):
        """Extract and add placement/coordinate entities referenced in the entity."""
        # Avoid infinite recursion
        if depth > 10:
            return
            
        # For components, focus on the placement reference (usually 5th parameter)
        # Pattern: IFCCOMPONENT('guid',#owner,'name','desc',#placement,#representation,...);
        placement_refs = []
        
        # First, try to extract the placement reference specifically
        if any(comp_type in entity_line for comp_type in ['IFCFLOW', 'IFCWALL', 'IFCSLAB', 'IFCBEAM', 'IFCCOLUMN', 'IFCELEMENTASSEMBLY']):
            # Extract placement reference (typically 5th parameter after 4 strings/nulls)
            match = re.search(r"[^,]+,[^,]+,[^,]+,[^,]+,\s*(#\d+)", entity_line)
            if match:
                placement_refs.append(match.group(1))
        
        # For placement entities, get all references
        if any(placement_type in entity_line for placement_type in ['IFCLOCALPLACEMENT', 'IFCAXIS2PLACEMENT3D']):
            placement_refs.extend(re.findall(r'#\d+', entity_line))
        
        for ref_id in placement_refs:
            if ref_id in processed_ids or ref_id not in entity_index:
                continue
                
            ref_line = entity_index[ref_id]
            
            # Check if this is a placement-related entity
            if any(placement_type in ref_line for placement_type in [
                'IFCLOCALPLACEMENT', 'IFCAXIS2PLACEMENT3D', 'IFCCARTESIANPOINT',
                'IFCDIRECTION'
            ]):
                processed_ids.add(ref_id)
                chunk_lines.append(ref_line)
                
                # Recursively add placement entities referenced by this placement
                add_placement_entities(ref_line, depth + 1)
    
    def add_entity_with_properties(entity_id: str):
        """Recursively add an entity and all its properties."""
        if entity_id in processed_ids or entity_id not in entity_index:
            return
        
        processed_ids.add(entity_id)
        
        # Add the entity itself
        entity_line = entity_index[entity_id]
        chunk_lines.append(entity_line)
        
        # Add placement and coordinate entities
        add_placement_entities(entity_line)
        
        # Find and add property relationships
        for rel_id, rel_line in entity_index.items():
            if rel_id not in processed_ids and 'IFCRELDEFINESBYPROPERTIES' in rel_line:
                # Check if this relation references our entity
                if entity_id in rel_line:
                    processed_ids.add(rel_id)
                    chunk_lines.append(rel_line)
                    
                    # Extract property set from relation
                    match = re.search(r',\s*(#\d+)\s*\)', rel_line)
                    if match:
                        pset_id = match.group(1)
                        add_property_set(pset_id)
        
        # Add direct property sets if any
        property_sets = rel_maps['properties'].get(entity_id, [])
        for pset_id in property_sets:
            add_property_set(pset_id)
    
    def add_property_set(pset_id: str):
        """Add a property set and all its properties."""
        if pset_id in processed_ids or pset_id not in entity_index:
            return
            
        processed_ids.add(pset_id)
        chunk_lines.append(entity_index[pset_id])
        
        # Add individual properties
        properties = rel_maps['property_sets'].get(pset_id, [])
        for prop_id in properties:
            if prop_id in entity_index and prop_id not in processed_ids:
                processed_ids.add(prop_id)
                chunk_lines.append(entity_index[prop_id])
    
    # Start with parent entity
    add_entity_with_properties(parent_id)
    
    # Add aggregation relationships
    for rel_id, rel_line in entity_index.items():
        if 'IFCRELAGGREGATES' in rel_line and parent_id in rel_line:
            if rel_id not in processed_ids:
                processed_ids.add(rel_id)
                chunk_lines.append(rel_line)
    
    # Add all children and their properties
    children = rel_maps['aggregations'].get(parent_id, [])
    for child_id in children:
        add_entity_with_properties(child_id)
    
    return '\n'.join(chunk_lines)


def create_chunk_prompt(assembly: Dict[str, str], chunk: str) -> str:
    """
    Create a focused prompt for chunk extraction.
    
    Args:
        assembly: Assembly information (id, type, name)
        chunk: The assembled chunk content
        
    Returns:
        Formatted prompt for the LLM
    """
    # Count entities in chunk for better guidance
    chunk_lines = chunk.strip().split('\n')
    entity_count = len([line for line in chunk_lines if line.strip()])
    
    # Count coordinate entities for debugging
    placement_count = len([line for line in chunk_lines if 'IFCLOCALPLACEMENT' in line])
    axis_count = len([line for line in chunk_lines if 'IFCAXIS2PLACEMENT3D' in line])
    point_count = len([line for line in chunk_lines if 'IFCCARTESIANPOINT' in line])
    coord_count = placement_count + axis_count + point_count
    
    # Warn if chunk is very large or has no coordinates
    if len(chunk) > 100000:
        import streamlit as st
        st.warning(f"⚠️ Large chunk for {assembly['name']}: {len(chunk):,} characters, {entity_count} entities")
    
    if coord_count == 0:
        import streamlit as st
        st.error(f"❌ No coordinate entities found in chunk for {assembly['name']}. Components will lack position data.")
        st.info("This chunk is missing: IFCLOCALPLACEMENT, IFCAXIS2PLACEMENT3D, and IFCCARTESIANPOINT entities")
    else:
        import streamlit as st
        st.info(f"✅ {assembly['name']} chunk includes: {placement_count} placements, {axis_count} axis placements, {point_count} points")
    
    return f"""Extract all components from this IFC assembly chunk.
        
Assembly: {assembly['type']} - {assembly['name']} (ID: {assembly['id']})
This chunk contains {entity_count} IFC entities for a complete {assembly['type']} assembly.
Coordinate entities included: {coord_count} (placement/position data)

IMPORTANT: Return ONLY a valid JSON object. Do not include any explanation or text outside the JSON.

IFC Data Chunk:
{chunk}

Extract ALL components found in this chunk including:
- The parent assembly itself  
- All child components (welds, tubes, fittings, attachments, etc.)
- Complete properties for each component
- Accurate coordinates (x, y, z) from IFCLOCALPLACEMENT/IFCAXIS2PLACEMENT3D/IFCCARTESIANPOINT entities
- Material assignments

CRITICAL: For coordinates, you MUST:
1. Follow IFCLOCALPLACEMENT references to find IFCAXIS2PLACEMENT3D
2. Extract IFCCARTESIANPOINT values for actual x,y,z coordinates
3. Include the exact numeric values (do not default to 0,0,0)
4. If coordinates are missing, set x,y,z to null (not 0)

Return a JSON object with this exact structure:
{{
  "components": [
    {{
      "globalId": "unique_id",
      "type": "IFCFLOWFITTING",
      "name": "component name",
      "x": 0.0,
      "y": 0.0,
      "z": 0.0,
      "material": "material name",
      "properties": {{}}
    }}
  ]
}}"""


async def process_chunk_async(
    client: genai.Client,
    model: str,
    chunk_data: Dict[str, Any],
    schema: dict,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Process a single chunk asynchronously with rate limiting.
    
    Args:
        client: Genai client (must support async operations)
        model: Model name
        chunk_data: Chunk information including assembly and prompt
        schema: JSON schema for extraction
        semaphore: Semaphore for rate limiting
        
    Returns:
        Processing result with components, tokens, and timing
    """
    async with semaphore:  # Limit concurrent requests
        try:
            start_time = time.time()
            
            # Create content
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=chunk_data['prompt'])]
                )
            ]
            
            # Adjust output tokens based on chunk size
            # Larger chunks need more output tokens
            chunk_size = len(chunk_data['chunk'])
            if chunk_size > 50000:
                max_tokens = 65535  # Maximum allowed by Gemini
            elif chunk_size > 20000:
                max_tokens = 32768
            else:
                max_tokens = 16384
            
            # Generation config
            config = types.GenerateContentConfig(
                temperature=0.05,
                max_output_tokens=max_tokens,
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
            
            # Async API call using client.aio
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Async token counting
            token_count = await client.aio.models.count_tokens(
                model=model,
                contents=contents
            )
            
            api_time = time.time() - start_time
            
            # Parse result with better error handling
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError as json_error:
                # Log the raw response for debugging
                import streamlit as st
                with st.expander(f"❌ JSON Error for {chunk_data['assembly']['name']}"):
                    st.error(f"JSON Parse Error: {str(json_error)}")
                    st.text("Raw response (first 1000 chars):")
                    st.code(response.text[:1000])
                    if len(response.text) > 1000:
                        st.warning(f"Response truncated. Total length: {len(response.text)} characters")
                
                # Try to extract components array if possible
                components = []
                try:
                    # Try to find components array in the response
                    import re
                    components_match = re.search(r'"components"\s*:\s*\[(.*?)\]', response.text, re.DOTALL)
                    if components_match:
                        components_str = '[' + components_match.group(1) + ']'
                        components = json.loads(components_str)
                except:
                    pass
                
                return {
                    'success': False,
                    'assembly': chunk_data['assembly'],
                    'error': f"JSON parsing failed: {str(json_error)}",
                    'components': components,  # May have partial results
                    'tokens': token_count.total_tokens,
                    'api_time': api_time,
                    'partial': True
                }
            
            return {
                'success': True,
                'assembly': chunk_data['assembly'],
                'components': result.get('components', []),
                'tokens': token_count.total_tokens,
                'api_time': api_time
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'assembly': chunk_data['assembly'],
                'error': f"{type(e).__name__}: {str(e)}",
                'components': [],
                'tokens': 0,
                'api_time': time.time() - start_time,
                'traceback': traceback.format_exc()
            }


def calculate_optimal_concurrency(num_chunks: int) -> int:
    """
    Calculate optimal concurrency based on workload.
    
    Args:
        num_chunks: Number of chunks to process
        
    Returns:
        Optimal number of concurrent workers
    """
    if num_chunks <= 5:
        return num_chunks
    elif num_chunks <= 20:
        return 5
    elif num_chunks <= 100:
        return 10
    else:
        return min(20, num_chunks // 10)


def extract_ungrouped_components(
    entity_index: Dict[str, str],
    core_assemblies: List[Dict[str, str]],
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> List[str]:
    """
    Find components that aren't part of any core assembly.
    
    Args:
        entity_index: Complete entity index
        core_assemblies: List of identified core assemblies
        rel_maps: Relationship mappings
        
    Returns:
        List of entity IDs for ungrouped components
    """
    # Get all components that are part of assemblies
    grouped_components = set()
    
    for assembly in core_assemblies:
        children = rel_maps['aggregations'].get(assembly['id'], [])
        grouped_components.update(children)
    
    # Find all component entities
    ungrouped = []
    component_patterns = [
        'IFCFLOWFITTING', 'IFCFLOWSEGMENT', 'IFCWALL', 'IFCSLAB',
        'IFCBEAM', 'IFCCOLUMN', 'IFCDOOR', 'IFCWINDOW'
    ]
    
    for entity_id, line in entity_index.items():
        # Check if it's a component type
        is_component = any(pattern in line for pattern in component_patterns)
        
        # Check if it's not part of any assembly
        if is_component and entity_id not in grouped_components:
            ungrouped.append(entity_id)
    
    return ungrouped