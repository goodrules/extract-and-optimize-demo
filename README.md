# Document Extraction & Optimization Demo

A sophisticated Streamlit application that extracts structured information from technical documents and 3D CAD files using Google Vertex AI Gemini models.

## Features

### 📋 Work Package Extraction
- **Advanced Schema Support**: Multiple predefined schemas including Work Package (Basic & Advanced), Task-Based Work Package, and Construction Work Package (CWP)
- **Dynamic Schema Discovery**: Automatically detects all available schemas in config/schema.py
- **Custom Schema Upload**: Support for uploading custom JSON schemas and system prompts
- **Document Input Options**: 
  - Browse and select documents from Google Cloud Storage
  - Upload local PDF files directly from your computer
- **Interactive JSON Editor**: Form-based editing with validation, statistics calculation, and project analytics
- **Advanced Analytics**: Critical path analysis, resource calculations, specialist breakdowns for task-based extractions

### 🎨 IFC Drawing Analysis  
- **Comprehensive 3D CAD Processing**: Analyzes IFC (Industry Foundation Classes) files up to 1.2M characters
- **Complete Component Extraction**: Advanced preprocessing and validation ensures ALL components are captured
- **Real-time Validation**: Pre-analysis identifies expected component counts and validates extraction completeness
- **Multiple Visualization Modes**: Project overview, component summary, detailed component analysis, and raw JSON
- **Spatial Analysis**: Extracts coordinates, materials, dimensions, and placement data for each component

### 🔧 Technical Capabilities
- **Model Selection**: Choose between Gemini 2.5 Pro (default) and Flash models with environment-configurable defaults
- **Environment Variable Management**: Secure configuration through .env files for sensitive data
- **Export Options**: Download extracted data as JSON or copy to clipboard
- **Validation & Quality Assurance**: Built-in completeness checking and troubleshooting guidance

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env file with your specific values
```

3. Ensure you have Google Cloud credentials configured:
```bash
gcloud auth application-default login
```

4. Run the application:
```bash
streamlit run app.py
```

## Project Structure

```
extract-and-optimize-demo/
├── app.py                 # Main Streamlit application with navigation
├── wp.py                  # Work Package Extraction page
├── drawing.py             # IFC Drawing Analysis page
├── config/
│   ├── schema.py         # JSON schemas for extraction (Work Package, IFC, CWP)
│   └── system_prompt.py  # System prompts for different extraction types
├── requirements.txt      # Python dependencies
├── scratchpad.ipynb     # Development notebook with IFC processing examples
├── .env.example         # Environment variable template
├── .env                 # Environment configuration (not in git)
└── .gitignore          # Git ignore file with security patterns
```

## Usage

### Work Package Extraction
1. Navigate to "Work Package Extraction" page
2. Select a model from the sidebar (defaults to Gemini 2.5 Pro)
3. Choose a schema from the dropdown:
   - **Work Package - Basic**: Simple project information extraction
   - **Work Package - Advanced**: Comprehensive project details with stakeholders, milestones, permits
   - **Task-Based Work Package**: Individual task extraction with dependencies and resource requirements
   - **Construction Work Package (CWP)**: Detailed construction scope with technical specifications
   - **Custom Schema**: Upload your own JSON schema
4. Select your document source:
   - **Google Cloud Storage**: Browse and select from available documents
   - **Upload Local File**: Upload a PDF file from your computer
5. Optionally modify the extraction prompt
6. Click "Extract Information" to process the document
7. Choose your view format:
   - **Formatted JSON**: Interactive form-based editor with validation
   - **Raw JSON**: Direct JSON editing
   - **Expandable Sections**: Organized hierarchical view
   - **Statistics Summary**: Project analytics and critical path analysis (for Task-Based extractions)

### IFC Drawing Analysis
1. Navigate to "Drawing Analysis" page
2. Select a model from the sidebar
3. Upload an IFC file (up to 1.2M characters supported)
4. Review the automatic structure analysis showing expected component counts
5. Click "Analyze IFC Data" to process the file
6. View validation results to ensure complete extraction
7. Explore results in multiple formats:
   - **Project Overview**: Metadata and spatial placement information
   - **Component Summary**: Statistical overview with extraction validation
   - **Detailed Components**: Individual component properties with search and pagination
   - **Raw JSON**: Complete extracted data structure

## Configuration

All sensitive configuration is handled via environment variables. Copy `.env.example` to `.env` and configure:

### Available Schemas

#### Work Package Schemas
- **Basic**: Essential project information (name, type, location, timeline, cost)
- **Advanced**: Comprehensive extraction including stakeholders, technical specs, permits, financial details
- **Task-Based**: Individual task extraction with dependencies, resource requirements, and project analytics
- **Construction Work Package (CWP)**: Detailed construction scope for piping projects with technical specifications

#### IFC Schema
- **3D CAD Analysis**: Comprehensive building component extraction including coordinates, materials, dimensions, and spatial relationships

### Processing Capabilities

#### Document Processing
- **PDF Analysis**: Technical documents, statements of work, project specifications
- **Smart Content Extraction**: Context-aware field mapping and validation
- **Custom Prompts**: Specialized extraction logic for different document types

#### IFC File Processing  
- **Large File Support**: Up to 1.2M characters with intelligent truncation
- **Complete Component Extraction**: Advanced preprocessing ensures all building elements are captured
- **Validation System**: Real-time verification of extraction completeness
- **Coordinate Processing**: 3D spatial data with coordinate transformation support

### Required Variables
- `GCP_PROJECT_ID`: Your Google Cloud Project ID (critical for Vertex AI authentication)
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name (default: `wec_demo_files`)
- `GCS_PREFIX`: Prefix for files in the bucket (default: `examples/`)
- `GCP_REGION`: Google Cloud region for Vertex AI services (default: `us-central1`)

### Optional Variables
- `DEFAULT_MODEL`: Default Gemini model (default: `gemini-2.5-pro-preview-05-06`)
- `FLASH_MODEL`: Flash model option (default: `gemini-2.5-flash-preview-05-20`)
- `STREAMLIT_PORT`: Port for Streamlit app (default: `8501`)

### Security Features
- Environment variables prevent hardcoded credentials in source code
- `.gitignore` configured to exclude sensitive files
- Fallback to `gcloud` config if environment variables not set
- Service account key files automatically excluded from version control

## Key Technologies

- **Streamlit**: Interactive web application framework
- **Google Vertex AI Gemini**: Advanced language models for structured extraction
- **Google Cloud Storage**: Document storage and retrieval
- **IFC Processing**: Industry Foundation Classes 3D CAD file analysis
- **JSON Schema Validation**: Structured data validation and transformation
- **Python-dotenv**: Environment variable management

## Advanced Features

### Task-Based Analytics
- **Critical Path Calculation**: Automatic project timeline analysis
- **Resource Planning**: Specialist allocation and hour calculations
- **Dependency Management**: Task sequencing and parallel execution analysis
- **Project Statistics**: Comprehensive project metrics and insights

### IFC Validation System
- **Pre-processing Analysis**: Structure identification before extraction
- **Component Count Validation**: Real-time verification of extraction completeness
- **Type-specific Validation**: Ensures all IFC entity types are captured
- **Troubleshooting Guidance**: Actionable recommendations for incomplete extractions

### Interactive Editing
- **Form-based JSON Editor**: User-friendly editing with validation
- **Real-time Statistics**: Live calculation of project metrics
- **Data Reset Capability**: Restore to original extracted values
- **Export Flexibility**: Multiple download and sharing options

## Author

Built by **goodrules** - [GitHub Profile](https://github.com/goodrules)

## License

This project demonstrates advanced AI-powered document processing capabilities for technical and construction industry applications.