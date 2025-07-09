# IFC Hierarchical & Relational Chunking Strategy

## Overview

This document outlines a chunking strategy for IFC files to improve both speed and accuracy of component extraction in the `drawing.py` application. The strategy treats IFC files as graphs of interconnected objects, creating context-rich chunks that contain primary objects and all information needed to understand them.

## Goals

1. **Maintain Current Output**: The final extracted JSON structure remains unchanged
2. **Improve Speed**: Reduce the number of API calls by processing fewer, larger chunks
3. **Improve Accuracy**: Provide complete context for each component in a single chunk
4. **Scalability**: Handle very large IFC files (>1.2M characters) effectively

## Implementation Strategy

### Phase 1: Pre-Parse and Index (Following Code Agent Rules)

Before implementing, we must:
1. **Search for existing IFC parsing implementations** (minimum 3 search patterns)
2. **Read existing IFC-related code** (analyze_ifc_structure function, etc.)
3. **Write failing tests first** (TDD Red phase)

```python
def create_ifc_entity_index(ifc_content: str) -> Dict[str, str]:
    """
    Pre-parse IFC file to create entity ID -> full line mapping.
    
    Args:
        ifc_content: Raw IFC file content
        
    Returns:
        Dictionary mapping entity IDs (e.g., '#44') to full lines
        
    Example:
        {
            '#44': '#44= IFCPROPERTYSET(...)',
            '#278': '#278= IFCFLOWFITTING(...)',
            ...
        }
    """
    # Implementation after tests are written
    pass
```

### Phase 2: Core Object Identification

```python
def identify_core_objects(entity_index: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Identify primary parent objects (IFCELEMENTASSEMBLY with E3DType of PIPE/BRANCH).
    
    Args:
        entity_index: Pre-parsed entity mapping
        
    Returns:
        List of core objects with their IDs and types
    """
    # Implementation after tests are written
    pass
```

### Phase 3: Hierarchical Chunk Assembly

```python
def assemble_hierarchical_chunk(
    parent_id: str, 
    entity_index: Dict[str, str],
    relationship_map: Dict[str, List[str]]
) -> str:
    """
    Assemble a complete chunk for a parent object and all its children.
    
    The chunk includes:
    1. Parent definition
    2. Parent properties (via IFCRELDEFINESBYPROPERTIES)
    3. All child objects (via IFCRELAGGREGATES)
    4. All child properties
    
    Args:
        parent_id: Entity ID of the parent object
        entity_index: Pre-parsed entity mapping
        relationship_map: Mapping of relationships between entities
        
    Returns:
        Complete chunk as concatenated text
    """
    # Implementation after tests are written
    pass
```

## Detailed Process Flow

### 1. Pre-Parse Phase

```python
# Step 1: Split IFC content into header and data sections
header_section, data_section = split_ifc_content(ifc_content)

# Step 2: Create entity index from DATA section
entity_index = {}
for line in data_section.split('\n'):
    if line.strip() and '=' in line:
        entity_id = line.split('=')[0].strip()
        entity_index[entity_id] = line

# Step 3: Build relationship maps
property_relations = {}  # Object ID -> Property Set IDs
aggregation_relations = {}  # Parent ID -> Child IDs
```

### 2. Core Object Identification

```python
# Identify IFCELEMENTASSEMBLY objects with E3DType of PIPE or BRANCH
core_objects = []
for entity_id, line in entity_index.items():
    if 'IFCELEMENTASSEMBLY' in line:
        # Check if this assembly has E3DType of PIPE or BRANCH
        # by following its property relationships
        if has_pipe_or_branch_type(entity_id, entity_index, property_relations):
            core_objects.append({
                'id': entity_id,
                'type': get_e3d_type(entity_id, entity_index, property_relations),
                'name': extract_name(entity_id, entity_index, property_relations)
            })
```

### 3. Chunk Assembly Example

For a BRANCH object (e.g., #4530), the chunk assembly process:

```python
chunk_lines = []

# A. Add parent definition
chunk_lines.append(entity_index['#4530'])  # IFCELEMENTASSEMBLY

# B. Add parent properties
property_rel_ids = property_relations.get('#4530', [])
for rel_id in property_rel_ids:  # e.g., #4532
    chunk_lines.append(entity_index[rel_id])  # IFCRELDEFINESBYPROPERTIES
    
    # Get property sets referenced
    property_set_ids = extract_property_sets(entity_index[rel_id])
    for ps_id in property_set_ids:  # e.g., #155, #160
        chunk_lines.append(entity_index[ps_id])  # IFCPROPERTYSET
        
        # Get individual properties
        property_ids = extract_properties(entity_index[ps_id])
        for prop_id in property_ids:  # e.g., #161, #162, #163
            chunk_lines.append(entity_index[prop_id])  # IFCPROPERTYSINGLEVALUE

# C. Add child aggregation
aggregation_ids = aggregation_relations.get('#4530', [])
for agg_id in aggregation_ids:  # e.g., #4541
    chunk_lines.append(entity_index[agg_id])  # IFCRELAGGREGATES
    
    # Get all child IDs
    child_ids = extract_child_ids(entity_index[agg_id])
    
    # D. Add all children and their properties
    for child_id in child_ids:  # e.g., #278 (WELD), #316 (TUBE)
        # Add child definition
        chunk_lines.append(entity_index[child_id])
        
        # Add child properties (same process as parent)
        # ... (recursive property extraction)

# E. Create final chunk
chunk_text = '\n'.join(chunk_lines)
```

## Integration with drawing.py

### Modified generate_ifc_extraction Function

```python
def generate_ifc_extraction_chunked(client, ifc_content, model, schema):
    """
    Enhanced extraction using hierarchical chunking strategy.
    """
    # 1. Pre-parse and index
    entity_index = create_ifc_entity_index(ifc_content)
    relationship_map = build_relationship_maps(entity_index)
    
    # 2. Identify core objects
    core_objects = identify_core_objects(entity_index)
    
    # 3. Process chunks in parallel batches
    all_components = []
    batch_size = 5  # Process 5 parent objects at a time
    
    for i in range(0, len(core_objects), batch_size):
        batch = core_objects[i:i+batch_size]
        batch_results = []
        
        # Create chunks for this batch
        for parent_obj in batch:
            chunk = assemble_hierarchical_chunk(
                parent_obj['id'], 
                entity_index, 
                relationship_map
            )
            
            # Extract components from this chunk
            result = extract_components_from_chunk(
                client, chunk, model, schema, parent_obj
            )
            batch_results.append(result)
        
        # Aggregate results
        for result in batch_results:
            all_components.extend(result['components'])
    
    # 4. Handle remaining ungrouped components
    ungrouped_components = find_ungrouped_components(entity_index, core_objects)
    if ungrouped_components:
        # Process remaining components in a final chunk
        # ...
    
    # 5. Assemble final result maintaining current output structure
    return assemble_final_result(all_components, ifc_content)
```

## Benefits of This Approach

1. **Reduced API Calls**: Instead of processing the entire file at once or many small chunks, we process one chunk per major assembly
2. **Complete Context**: Each chunk contains all information needed to understand a component and its relationships
3. **Parallel Processing**: Multiple chunks can be processed concurrently
4. **Scalability**: Large files are broken into manageable, logical units
5. **Accuracy**: Related information stays together, improving extraction quality

## Test-Driven Development Plan

Following the code agent rules for TDD:

### RED Phase Tests
```python
# test_ifc_chunking.py

def test_create_entity_index():
    """Test that entity index correctly maps IDs to lines."""
    # Write this test first, expect it to fail
    
def test_identify_pipe_branch_assemblies():
    """Test identification of PIPE/BRANCH assemblies."""
    # Write this test first, expect it to fail
    
def test_chunk_includes_all_properties():
    """Test that chunks include all related properties."""
    # Write this test first, expect it to fail
    
def test_chunk_includes_all_children():
    """Test that chunks include all child components."""
    # Write this test first, expect it to fail
```

### Implementation Order

1. **Search Phase**: Search for existing IFC parsing patterns in codebase
2. **Test Phase**: Write all failing tests
3. **Index Implementation**: Create entity indexing
4. **Relationship Mapping**: Build parent-child relationships
5. **Chunk Assembly**: Implement hierarchical chunking
6. **Integration**: Modify generate_ifc_extraction to use chunks
7. **Refactor**: Clean up and optimize

## Performance Metrics

Track these metrics to validate improvements:

1. **Execution Time**: Compare before/after chunking
2. **Token Usage**: Measure total tokens used
3. **Accuracy**: Component extraction completeness
4. **Memory Usage**: Peak memory during processing

## Migration Path

1. **Phase 1**: Implement chunking as optional feature (flag-controlled)
2. **Phase 2**: A/B test chunked vs. non-chunked on sample files
3. **Phase 3**: Make chunking default after validation
4. **Phase 4**: Remove old non-chunked code path

## Error Handling

- Handle malformed IFC files gracefully
- Provide fallback to non-chunked processing
- Log chunking statistics for debugging
- Validate chunk sizes stay within model limits

## Future Enhancements

1. **Adaptive Chunking**: Adjust chunk size based on model and file characteristics
2. **Chunk Caching**: Cache processed chunks for repeated analyses
3. **Incremental Updates**: Process only changed sections on file updates
4. **Custom Chunking Rules**: Allow users to define chunking strategies for specific IFC schemas