# RAG Core

Core RAG functionality for document processing, embeddings, and vector search.

## Features

- **Document Parsing**: Support for PDF, DOCX, XLSX, HTML, and email formats
- **Table Extraction**: Advanced table extraction using Camelot and Tabula
- **OCR Support**: Tesseract integration for scanned documents
- **Smart Chunking**: Configurable text and table chunking strategies
- **Embedding Generation**: Local embedding generation via Ollama
- **Vector Storage**: PostgreSQL + pgvector integration with HNSW indexing
- **RAG Pipeline**: Complete document processing pipeline

## Installation

```bash
pip install rag-core
```

Or install from source:

```bash
git clone https://github.com/your-org/rag-platform.git
cd rag-platform/packages/rag_core
pip install -e .
```

## Quick Start

```python
from pathlib import Path
from rag_core.rag_pipeline import RAGPipeline
from rag_core.embeddings.embedding_service import EmbeddingService
from rag_core.vectorstore.pgvector_store import PgVectorStore

# Initialize services
embedding_service = EmbeddingService(model_name="bge-m3")
vector_store = PgVectorStore("postgresql://user:pass@localhost/rag_db")
pipeline = RAGPipeline(vector_store, embedding_service)

# Process a document
file_path = Path("document.pdf")
result = await pipeline.process_document(file_path)
print(f"Processed {result['chunks_count']} chunks")

# Search
results = await pipeline.search("your query", top_k=10)
for result in results:
    print(f"Score: {result['score']}, Content: {result['content'][:100]}...")
```

## Architecture

### Document Parsers

- **PDFParser**: Handles vector PDFs with table extraction
- **DOCXParser**: Processes Word documents with table support
- **Extensible**: Easy to add new format parsers

### Chunking Strategies

- **TextChunkingStrategy**: Sentence-based text chunking
- **TableChunkingStrategy**: Table-aware chunking
- **MixedChunkingStrategy**: Combines text and table chunking

### Embedding Service

- **Ollama Integration**: Local embedding generation
- **Batch Processing**: Efficient batch embedding generation
- **Async Support**: Non-blocking embedding operations

### Vector Store

- **PostgreSQL + pgvector**: Production-ready vector storage
- **HNSW Indexing**: Fast approximate nearest neighbor search
- **ACL Support**: Document-level access control

## Configuration

The pipeline can be configured with various parameters:

```python
pipeline = RAGPipeline(
    vector_store=vector_store,
    embedding_service=embedding_service,
    chunk_size=1000,      # Characters per chunk
    overlap=200           # Overlap between chunks
)
```

## Supported Formats

| Format | Parser | Table Support | OCR Required |
|--------|--------|---------------|--------------|
| PDF    | PDFParser | ✅ Camelot/Tabula | Conditional |
| DOCX   | DOCXParser | ✅ Native | ❌ |
| XLSX   | XLSXParser | ✅ Native | ❌ |
| HTML   | HTMLParser | ✅ BeautifulSoup | ❌ |
| Images | ImageParser | ❌ | ✅ Tesseract |

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
black .
ruff check .
mypy .
```

## Dependencies

### Required

- `psycopg[binary]` - PostgreSQL adapter
- `requests` - HTTP client
- `PyPDF2` - PDF processing
- `python-docx` - Word document processing
- `camelot-py` - Table extraction
- `pytesseract` - OCR support

### Optional

- `opencv-python` - Image processing
- `paddleocr` - Alternative OCR engine
- `tabula-py` - Java-based table extraction

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
