# IFC Chunking Implementation Guide

## Quick Start Implementation

This guide provides concrete implementation steps for adding hierarchical chunking to `drawing.py` while maintaining the current output format.

## Step 1: Create Tests First (TDD Red Phase)

Create `test_ifc_chunking.py`:

```python
import pytest
from drawing import (
    create_ifc_entity_index,
    identify_core_assemblies,
    build_relationship_maps,
    assemble_hierarchical_chunk
)

class TestIFCChunking:
    
    @pytest.fixture
    def sample_ifc_content(self):
        """Sample IFC content for testing."""
        return """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('test.ifc','2024-01-01T00:00:00',(),(),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1= IFCPROJECT('project_id',$,'Test Project',$,$,$,$,$,$);
#155= IFCPROPERTYSET('pset1',$,'Properties',$,(#159,#163));
#159= IFCPROPERTYSINGLEVALUE('E3DType',$,IFCLABEL('BRANCH'),$);
#163= IFCPROPERTYSINGLEVALUE('NAME',$,IFCLABEL('B1'),$);
#278= IFCFLOWFITTING('fitting1',$,'WELD 1',$,$,$,$,$);
#316= IFCFLOWSEGMENT('segment1',$,'TUBE 1',$,$,$,$,$);
#4530= IFCELEMENTASSEMBLY('assembly1',$,'BRANCH B1',$,$,$,$,$,$);
#4532= IFCRELDEFINESBYPROPERTIES('rel1',$,$,$,(#4530),#155);
#4541= IFCRELAGGREGATES('agg1',$,$,$,#4530,(#278,#316));
ENDSEC;
END-ISO-10303-21;"""
    
    def test_create_entity_index(self, sample_ifc_content):
        """Test entity indexing creates correct ID to line mapping."""
        index = create_ifc_entity_index(sample_ifc_content)
        
        assert '#278' in index
        assert 'IFCFLOWFITTING' in index['#278']
        assert index['#278'].startswith('#278=')
        
    def test_identify_core_assemblies(self, sample_ifc_content):
        """Test identification of PIPE/BRANCH assemblies."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_map = build_relationship_maps(index)
        
        assemblies = identify_core_assemblies(index, rel_map)
        
        assert len(assemblies) == 1
        assert assemblies[0]['id'] == '#4530'
        assert assemblies[0]['type'] == 'BRANCH'
        assert assemblies[0]['name'] == 'B1'
        
    def test_build_relationship_maps(self, sample_ifc_content):
        """Test relationship mapping between entities."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        # Check property relationships
        assert '#4530' in rel_maps['properties']
        assert '#155' in rel_maps['properties']['#4530']
        
        # Check aggregation relationships
        assert '#4530' in rel_maps['aggregations']
        assert '#278' in rel_maps['aggregations']['#4530']
        assert '#316' in rel_maps['aggregations']['#4530']
        
    def test_assemble_hierarchical_chunk(self, sample_ifc_content):
        """Test chunk assembly includes all related entities."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        chunk = assemble_hierarchical_chunk('#4530', index, rel_maps)
        
        # Verify chunk contains all expected entities
        assert '#4530=' in chunk  # Parent
        assert '#4532=' in chunk  # Property relation
        assert '#155=' in chunk   # Property set
        assert '#159=' in chunk   # E3DType property
        assert '#163=' in chunk   # NAME property
        assert '#4541=' in chunk  # Aggregation
        assert '#278=' in chunk   # Child weld
        assert '#316=' in chunk   # Child tube
```

## Step 2: Implement Core Functions

Add these functions to `drawing.py` or create a new module `ifc_chunking.py`:

```python
import re
from typing import Dict, List, Tuple, Set

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
        Dictionary with 'properties' and 'aggregations' mappings
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
            match = re.search(r'\((.*?)\),\s*(#\d+)', line)
            if match:
                related_objects = re.findall(r'#\d+', match.group(1))
                property_set = match.group(2)
                
                for obj_id in related_objects:
                    if obj_id not in rel_maps['properties']:
                        rel_maps['properties'][obj_id] = []
                    rel_maps['properties'][obj_id].append(property_set)
        
        # Parse IFCRELAGGREGATES
        elif 'IFCRELAGGREGATES' in line:
            # Extract parent and children
            match = re.search(r',(#\d+),\s*\((.*?)\)', line)
            if match:
                parent_id = match.group(1)
                children = re.findall(r'#\d+', match.group(2))
                rel_maps['aggregations'][parent_id] = children
        
        # Parse IFCPROPERTYSET
        elif 'IFCPROPERTYSET' in line:
            # Extract property IDs
            match = re.search(r'\((#\d+(?:,\s*#\d+)*)\)', line)
            if match:
                property_ids = re.findall(r'#\d+', match.group(1))
                rel_maps['property_sets'][entity_id] = property_ids
    
    return rel_maps

def identify_core_assemblies(
    entity_index: Dict[str, str], 
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> List[Dict[str, str]]:
    """
    Identify IFCELEMENTASSEMBLY objects with E3DType of PIPE or BRANCH.
    """
    core_assemblies = []
    
    for entity_id, line in entity_index.items():
        if 'IFCELEMENTASSEMBLY' in line:
            # Check if this assembly has PIPE or BRANCH type
            e3d_type = None
            name = None
            
            # Get property sets for this assembly
            property_sets = rel_maps['properties'].get(entity_id, [])
            
            for pset_id in property_sets:
                # Get properties in this set
                properties = rel_maps['property_sets'].get(pset_id, [])
                
                for prop_id in properties:
                    prop_line = entity_index.get(prop_id, '')
                    
                    # Check for E3DType
                    if 'E3DType' in prop_line:
                        match = re.search(r"IFCLABEL\('(.*?)'\)", prop_line)
                        if match:
                            e3d_type = match.group(1)
                    
                    # Check for NAME
                    elif "'NAME'" in prop_line or '"NAME"' in prop_line:
                        match = re.search(r"IFCLABEL\('(.*?)'\)", prop_line)
                        if match:
                            name = match.group(1)
            
            # Add if it's a PIPE or BRANCH
            if e3d_type in ['PIPE', 'BRANCH']:
                core_assemblies.append({
                    'id': entity_id,
                    'type': e3d_type,
                    'name': name or 'Unknown'
                })
    
    return core_assemblies

def assemble_hierarchical_chunk(
    parent_id: str,
    entity_index: Dict[str, str],
    rel_maps: Dict[str, Dict[str, List[str]]]
) -> str:
    """
    Assemble a complete chunk for a parent object and all its children.
    """
    chunk_lines = []
    processed_ids = set()  # Track processed entities to avoid duplicates
    
    def add_entity_with_properties(entity_id: str):
        """Recursively add an entity and all its properties."""
        if entity_id in processed_ids:
            return
        
        processed_ids.add(entity_id)
        
        # Add the entity itself
        if entity_id in entity_index:
            chunk_lines.append(entity_index[entity_id])
        
        # Add property relationships and sets
        property_sets = rel_maps['properties'].get(entity_id, [])
        for pset_id in property_sets:
            # Add property set
            if pset_id in entity_index and pset_id not in processed_ids:
                processed_ids.add(pset_id)
                chunk_lines.append(entity_index[pset_id])
                
                # Add individual properties
                properties = rel_maps['property_sets'].get(pset_id, [])
                for prop_id in properties:
                    if prop_id in entity_index and prop_id not in processed_ids:
                        processed_ids.add(prop_id)
                        chunk_lines.append(entity_index[prop_id])
    
    # Add parent and its properties
    add_entity_with_properties(parent_id)
    
    # Add property relation entities
    for entity_id, line in entity_index.items():
        if 'IFCRELDEFINESBYPROPERTIES' in line and parent_id in line:
            if entity_id not in processed_ids:
                processed_ids.add(entity_id)
                chunk_lines.append(line)
    
    # Add aggregation relationships
    for entity_id, line in entity_index.items():
        if 'IFCRELAGGREGATES' in line and parent_id in line:
            if entity_id not in processed_ids:
                processed_ids.add(entity_id)
                chunk_lines.append(line)
            
            # Get children from this aggregation
            children = rel_maps['aggregations'].get(parent_id, [])
            
            # Add all children and their properties
            for child_id in children:
                add_entity_with_properties(child_id)
                
                # Add child's property relations
                for rel_id, rel_line in entity_index.items():
                    if 'IFCRELDEFINESBYPROPERTIES' in rel_line and child_id in rel_line:
                        if rel_id not in processed_ids:
                            processed_ids.add(rel_id)
                            chunk_lines.append(rel_line)
    
    return '\n'.join(chunk_lines)
```

## Step 3: Integrate Chunking into generate_ifc_extraction

Modify the `generate_ifc_extraction` function in `drawing.py`:

```python
def generate_ifc_extraction(client, ifc_content, model, schema, use_chunking=True):
    """
    Generate extraction from IFC content with optional chunking strategy.
    """
    # Analyze IFC structure first
    structure_info = analyze_ifc_structure(ifc_content)
    st.session_state.ifc_structure_info = structure_info
    
    # Display analysis to user
    st.info(f"📊 IFC Analysis: Found {structure_info['total_components']} components across {len(structure_info['component_types'])} types")
    
    if use_chunking and structure_info['total_components'] > 50:
        # Use chunking strategy for larger files
        return generate_ifc_extraction_chunked(client, ifc_content, model, schema, structure_info)
    else:
        # Use original approach for smaller files
        return generate_ifc_extraction_original(client, ifc_content, model, schema, structure_info)

def generate_ifc_extraction_chunked(client, ifc_content, model, schema, structure_info):
    """
    Enhanced extraction using hierarchical chunking strategy.
    """
    # Pre-parse and index
    with st.spinner("Indexing IFC entities..."):
        entity_index = create_ifc_entity_index(ifc_content)
        rel_maps = build_relationship_maps(entity_index)
        core_assemblies = identify_core_assemblies(entity_index, rel_maps)
    
    st.info(f"🔧 Found {len(core_assemblies)} core assemblies to process")
    
    # Process assemblies in chunks
    all_components = []
    total_tokens = 0
    
    # Progress bar
    progress_bar = st.progress(0)
    
    for idx, assembly in enumerate(core_assemblies):
        # Update progress
        progress = (idx + 1) / len(core_assemblies)
        progress_bar.progress(progress, f"Processing {assembly['type']} {assembly['name']}")
        
        # Assemble chunk for this assembly
        chunk = assemble_hierarchical_chunk(assembly['id'], entity_index, rel_maps)
        
        # Create focused prompt for this chunk
        chunk_prompt = f"""Extract components from this IFC assembly chunk.
        
Assembly: {assembly['type']} - {assembly['name']}
Expected components: Analyze and extract all components in this assembly.

IFC Data:
{chunk}

Extract all components with their properties, coordinates, and relationships."""
        
        # Generate extraction for this chunk
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=chunk_prompt)]
            )
        ]
        
        # Use same generation config
        generate_content_config = types.GenerateContentConfig(
            temperature=0.05,
            max_output_tokens=8192,  # Smaller limit per chunk
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
        
        # Parse chunk result
        chunk_result = json.loads(response.text)
        if 'components' in chunk_result:
            all_components.extend(chunk_result['components'])
        
        # Count tokens
        token_count = client.models.count_tokens(model=model, contents=contents)
        total_tokens += token_count.total_tokens
    
    progress_bar.empty()
    
    # Assemble final result maintaining current structure
    final_result = {
        'projectMetadata': extract_project_metadata(ifc_content),
        'overallSpatialPlacement': extract_spatial_placement(entity_index),
        'components': all_components,
        'componentSummary': recalculate_component_summary(all_components)
    }
    
    # Create mock response object for compatibility
    class MockResponse:
        def __init__(self, text):
            self.text = text
    
    return MockResponse(json.dumps(final_result)), total_tokens
```

## Step 4: Add Configuration Option

Add a checkbox in the sidebar to enable/disable chunking:

```python
# In the sidebar configuration section
with st.sidebar:
    # ... existing configuration ...
    
    st.divider()
    st.subheader("⚙️ Advanced Options")
    
    use_chunking = st.checkbox(
        "Use Hierarchical Chunking",
        value=True,
        help="Enable chunking strategy for large IFC files (>50 components). This can improve speed and accuracy."
    )
    
    if use_chunking:
        st.info("🔧 Chunking enabled for files with >50 components")
```

## Performance Monitoring

Add performance metrics collection:

```python
def log_chunking_metrics(
    file_size: int,
    num_assemblies: int,
    num_components: int,
    execution_time: float,
    total_tokens: int,
    chunking_used: bool
):
    """Log performance metrics for analysis."""
    metrics = {
        'timestamp': time.time(),
        'file_size': file_size,
        'num_assemblies': num_assemblies,
        'num_components': num_components,
        'execution_time': execution_time,
        'total_tokens': total_tokens,
        'chunking_used': chunking_used,
        'tokens_per_component': total_tokens / num_components if num_components > 0 else 0,
        'components_per_second': num_components / execution_time if execution_time > 0 else 0
    }
    
    # Display metrics
    with st.expander("📊 Performance Metrics"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Components/Second", f"{metrics['components_per_second']:.1f}")
        with col2:
            st.metric("Tokens/Component", f"{metrics['tokens_per_component']:.0f}")
        with col3:
            st.metric("Strategy", "Chunked" if chunking_used else "Single")
```

## Rollback Plan

If chunking causes issues, you can quickly disable it:

1. Set `use_chunking=False` by default in the checkbox
2. The original extraction logic remains intact
3. Monitor error rates and performance metrics
4. Gradually increase usage based on success metrics

This implementation maintains the current output format while providing significant performance improvements for large IFC files.