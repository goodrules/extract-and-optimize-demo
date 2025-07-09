import pytest
import asyncio
from typing import Dict, List
from ifc_chunking import (
    create_ifc_entity_index,
    identify_core_assemblies,
    build_relationship_maps,
    assemble_hierarchical_chunk,
    extract_properties_for_entity,
    process_chunk_async
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
#155= IFCPROPERTYSET('pset1',$,'Branch Properties',$,(#159,#163));
#159= IFCPROPERTYSINGLEVALUE('E3DType',$,IFCLABEL('BRANCH'),$);
#163= IFCPROPERTYSINGLEVALUE('NAME',$,IFCLABEL('B1'),$);
#209= IFCPROPERTYSET('pset2',$,'Weld Properties',$,(#210,#211));
#210= IFCPROPERTYSINGLEVALUE('Type',$,IFCLABEL('BUTT_WELD'),$);
#211= IFCPROPERTYSINGLEVALUE('Size',$,IFCREAL(6.0),$);
#278= IFCFLOWFITTING('fitting1',$,'WELD 1',$,$,$,$,$);
#279= IFCRELDEFINESBYPROPERTIES('rel2',$,$,$,(#278),#209);
#316= IFCFLOWSEGMENT('segment1',$,'TUBE 1',$,$,$,$,$);
#4530= IFCELEMENTASSEMBLY('assembly1',$,'BRANCH B1',$,$,$,$,$,$);
#4532= IFCRELDEFINESBYPROPERTIES('rel1',$,$,$,(#4530),#155);
#4541= IFCRELAGGREGATES('agg1',$,$,$,#4530,(#278,#316));
ENDSEC;
END-ISO-10303-21;"""
    
    @pytest.fixture
    def large_ifc_content(self):
        """Larger IFC content with multiple assemblies."""
        return """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('large.ifc','2024-01-01T00:00:00',(),(),'','','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1= IFCPROJECT('project_id',$,'Large Project',$,$,$,$,$,$);
#100= IFCPROPERTYSET('pset_pipe1',$,'Pipe Properties',$,(#101,#102));
#101= IFCPROPERTYSINGLEVALUE('E3DType',$,IFCLABEL('PIPE'),$);
#102= IFCPROPERTYSINGLEVALUE('NAME',$,IFCLABEL('P1'),$);
#200= IFCPROPERTYSET('pset_branch1',$,'Branch Properties',$,(#201,#202));
#201= IFCPROPERTYSINGLEVALUE('E3DType',$,IFCLABEL('BRANCH'),$);
#202= IFCPROPERTYSINGLEVALUE('NAME',$,IFCLABEL('B1'),$);
#1000= IFCELEMENTASSEMBLY('pipe1',$,'PIPE P1',$,$,$,$,$,$);
#1001= IFCRELDEFINESBYPROPERTIES('rel_pipe1',$,$,$,(#1000),#100);
#2000= IFCELEMENTASSEMBLY('branch1',$,'BRANCH B1',$,$,$,$,$,$);
#2001= IFCRELDEFINESBYPROPERTIES('rel_branch1',$,$,$,(#2000),#200);
#3000= IFCWALL('wall1',$,'Wall 1',$,$,$,$,$);
ENDSEC;
END-ISO-10303-21;"""
    
    def test_create_entity_index(self, sample_ifc_content):
        """Test entity indexing creates correct ID to line mapping."""
        index = create_ifc_entity_index(sample_ifc_content)
        
        assert '#278' in index
        assert 'IFCFLOWFITTING' in index['#278']
        assert index['#278'].startswith('#278=')
        assert '#4530' in index
        assert 'IFCELEMENTASSEMBLY' in index['#4530']
        
        # Check multi-line entity handling
        assert len(index) >= 10  # Should have all entities
        
    def test_build_relationship_maps(self, sample_ifc_content):
        """Test relationship mapping between entities."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        # Check property relationships
        assert 'properties' in rel_maps
        assert '#4530' in rel_maps['properties']
        assert '#155' in rel_maps['properties']['#4530']
        
        # Check aggregation relationships
        assert 'aggregations' in rel_maps
        assert '#4530' in rel_maps['aggregations']
        assert '#278' in rel_maps['aggregations']['#4530']
        assert '#316' in rel_maps['aggregations']['#4530']
        
        # Check property sets
        assert 'property_sets' in rel_maps
        assert '#155' in rel_maps['property_sets']
        assert '#159' in rel_maps['property_sets']['#155']
        assert '#163' in rel_maps['property_sets']['#155']
    
    def test_identify_core_assemblies(self, sample_ifc_content):
        """Test identification of PIPE/BRANCH assemblies."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        assemblies = identify_core_assemblies(index, rel_maps)
        
        assert len(assemblies) == 1
        assert assemblies[0]['id'] == '#4530'
        assert assemblies[0]['type'] == 'BRANCH'
        assert assemblies[0]['name'] == 'B1'
    
    def test_identify_multiple_assemblies(self, large_ifc_content):
        """Test identification of multiple PIPE/BRANCH assemblies."""
        index = create_ifc_entity_index(large_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        assemblies = identify_core_assemblies(index, rel_maps)
        
        assert len(assemblies) == 2
        # Check PIPE assembly
        pipe_assembly = next(a for a in assemblies if a['type'] == 'PIPE')
        assert pipe_assembly['id'] == '#1000'
        assert pipe_assembly['name'] == 'P1'
        
        # Check BRANCH assembly
        branch_assembly = next(a for a in assemblies if a['type'] == 'BRANCH')
        assert branch_assembly['id'] == '#2000'
        assert branch_assembly['name'] == 'B1'
    
    def test_assemble_hierarchical_chunk(self, sample_ifc_content):
        """Test chunk assembly includes all related entities."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        chunk = assemble_hierarchical_chunk('#4530', index, rel_maps)
        
        # Verify chunk contains all expected entities
        assert '#4530=' in chunk  # Parent assembly
        assert '#4532=' in chunk  # Property relation
        assert '#155=' in chunk   # Property set
        assert '#159=' in chunk   # E3DType property
        assert '#163=' in chunk   # NAME property
        assert '#4541=' in chunk  # Aggregation relation
        assert '#278=' in chunk   # Child weld
        assert '#279=' in chunk   # Child property relation
        assert '#209=' in chunk   # Child property set
        assert '#316=' in chunk   # Child tube
        
        # Verify no duplicates
        lines = chunk.split('\n')
        unique_lines = set(lines)
        assert len(lines) == len(unique_lines)
    
    def test_extract_properties_for_entity(self, sample_ifc_content):
        """Test property extraction for a specific entity."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        properties = extract_properties_for_entity('#4530', index, rel_maps)
        
        assert 'E3DType' in properties
        assert properties['E3DType'] == 'BRANCH'
        assert 'NAME' in properties
        assert properties['NAME'] == 'B1'
    
    @pytest.mark.asyncio
    async def test_process_chunk_async_mock(self):
        """Test async chunk processing with mock client."""
        # Mock chunk data
        chunk_data = {
            'assembly': {'id': '#4530', 'type': 'BRANCH', 'name': 'B1'},
            'chunk': 'mock chunk content',
            'prompt': 'Extract components from this chunk'
        }
        
        # Mock client and response
        class MockResponse:
            text = '{"components": [{"globalId": "123", "type": "IFCFLOWFITTING"}]}'
        
        class MockTokenCount:
            total_tokens = 100
        
        class MockModel:
            async def generate_content_async(self, **kwargs):
                await asyncio.sleep(0.1)  # Simulate API delay
                return MockResponse()
            
            async def count_tokens_async(self, **kwargs):
                return MockTokenCount()
        
        class MockClient:
            models = MockModel()
        
        # Test async processing
        semaphore = asyncio.Semaphore(5)
        result = await process_chunk_async(
            MockClient(),
            'test-model',
            chunk_data,
            {},
            semaphore
        )
        
        assert result['success'] is True
        assert len(result['components']) == 1
        assert result['tokens'] == 100
        assert result['api_time'] > 0
    
    def test_chunk_completeness(self, sample_ifc_content):
        """Test that chunks contain complete information."""
        index = create_ifc_entity_index(sample_ifc_content)
        rel_maps = build_relationship_maps(index)
        
        # Get the branch assembly chunk
        chunk = assemble_hierarchical_chunk('#4530', index, rel_maps)
        
        # Verify the chunk can be parsed independently
        chunk_lines = chunk.split('\n')
        chunk_entities = {}
        
        for line in chunk_lines:
            if line.strip() and '=' in line:
                entity_id = line.split('=')[0].strip()
                chunk_entities[entity_id] = line
        
        # Verify all references within the chunk are resolved
        # The chunk should be self-contained
        assert len(chunk_entities) >= 10  # Should have all related entities
        
        # Check that property references are included
        if '#4532' in chunk_entities:  # Property relation
            # The referenced property set should be in the chunk
            assert '#155' in chunk_entities
        
        # Check that aggregation children are included
        if '#4541' in chunk_entities:  # Aggregation relation
            # The referenced children should be in the chunk
            assert '#278' in chunk_entities
            assert '#316' in chunk_entities