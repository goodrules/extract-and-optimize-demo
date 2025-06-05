# Document Extraction & Optimization Demo

AI-powered Streamlit application that extracts structured information from technical documents and 3D CAD files using Google Vertex AI Gemini models.

## Features

### 📋 Work Package Extraction
- Multiple predefined schemas (Basic, Advanced, Task-Based, Construction Work Package)
- Document input from Google Cloud Storage or local upload
- Interactive JSON editing with validation and analytics
- Critical path analysis and resource planning for task-based extractions

### 🎨 IFC Drawing Analysis
- Comprehensive 3D CAD processing (up to 1.2M characters)
- Real-time component extraction validation
- Spatial analysis with coordinates, materials, and dimensions
- Multiple visualization modes

### 🔧 Technical Capabilities
- Gemini 2.5 Pro/Flash model selection
- Google Authentication integration
- Export options (JSON download/clipboard)
- Custom schema upload support

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure authentication:**
```bash
cp .env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit both files with your credentials
```

3. **Set up Google Cloud:**
```bash
gcloud auth application-default login
```

4. **Run the application:**
```bash
streamlit run app.py
```

## Cloud Deployment

### Prerequisites
- Google Cloud project with Vertex AI API enabled
- Google Auth Platform OAuth 2.0 client configured

### Step 1: Update Dockerfile
Ensure your Dockerfile is configured for Cloud Run (already optimized):
```dockerfile
FROM python:3.13
EXPOSE 8080
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD streamlit run --server.port 8080 --server.enableCORS false app.py
```

### Step 2: Configure Google Authentication

Follow the [Streamlit Google Authentication Tutorial](https://docs.streamlit.io/develop/tutorials/authentication/google) to:

1. **Create OAuth 2.0 client in Google Cloud Console**
2. **Configure consent screen and test users**
3. **Save your credentials:**
   - Client ID
   - Client Secret
   - Server metadata URL: `https://accounts.google.com/.well-known/openid-configuration`

### Step 3: Deploy to Cloud Run
```bash
gcloud run deploy wp-extract-demo --source . --region="us-central1"
```

### Step 4: Configure Environment and Secrets
1. Go to Cloud Run service → Source → Edit source
2. Rename `.env.example` to `.env` and update with your configuration, for example:
```bash
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket
GCS_PREFIX=examples/
GCS_IFC_PREFIX=examples/drawings/
GCP_REGION=global
DEFAULT_MODEL=gemini-2.5-pro-preview-06-05
FLASH_MODEL=gemini-2.5-flash-preview-05-20
```
3. Rename `secrets.toml.example` to `secrets.toml`
4. Update with your Google Auth Platform credentials, for example:
```toml
[auth]
redirect_uri = "https://your-app-url/oauth2callback"
cookie_secret = "your-random-cookie-secret"
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

## Usage

### Work Package Extraction
1. Select schema (Basic, Advanced, Task-Based, CWP, or Custom)
2. Choose document source (GCS or local upload)
3. Extract and view in multiple formats (JSON editor, raw, expandable sections)
4. Export results or view analytics

### IFC Drawing Analysis
1. Upload IFC file
2. Review structure analysis
3. Process with AI extraction
4. Validate completeness and explore components

## Available Schemas

- **Work Package Basic**: Essential project information
- **Work Package Advanced**: Comprehensive details with stakeholders/permits
- **Task-Based**: Individual tasks with dependencies and resources
- **Construction Work Package (CWP)**: Technical construction specifications
- **IFC Analysis**: 3D CAD component extraction with spatial data

## Technologies

- **Streamlit** - Web framework
- **Google Vertex AI Gemini** - AI processing
- **Google Cloud Storage** - Document storage
- **Google Auth Platform** - Authentication
- **PyMuPDF** - PDF processing

Built by [goodrules](https://github.com/goodrules)