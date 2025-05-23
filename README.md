# Document Extraction & Optimization Demo

A Streamlit application that extracts structured information from technical documents using Google Vertex AI Gemini models.

## Features

- **Model Selection**: Choose between Gemini 2.5 Flash (default) and Pro models
- **Schema Options**: Select between basic and advanced extraction schemas
- **GCS Integration**: Browse and select documents from Google Cloud Storage
- **Multiple View Modes**: View results as formatted JSON, raw JSON, or expandable sections
- **Export Options**: Download extracted data as JSON or copy to clipboard

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have Google Cloud credentials configured:
```bash
gcloud auth application-default login
```

3. Run the application:
```bash
streamlit run app.py
```

## Project Structure

```
extract-and-optimize-demo/
├── app.py                 # Main Streamlit application
├── config/
│   ├── schema.py         # JSON schemas for extraction
│   └── system_prompt.py  # System prompt for the AI model
├── requirements.txt      # Python dependencies
└── scratchpad.ipynb     # Original Jupyter notebook
```

## Usage

1. Select a model from the sidebar (defaults to Gemini 2.5 Flash)
2. Choose a schema type (Advanced or Basic)
3. Select a document from the GCS bucket
4. Optionally modify the extraction prompt
5. Click "Extract Information" to process the document
6. View results in your preferred format
7. Download the JSON file or copy to clipboard

## Configuration

- **Bucket**: `wec_demo_files`
- **Prefix**: `examples/`
- **Region**: `us-central1` (configurable)