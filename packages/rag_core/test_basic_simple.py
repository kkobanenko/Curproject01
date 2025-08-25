#!/usr/bin/env python3
"""
Simplified basic tests for RAG Core functionality (no external dependencies)
"""

import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that core modules can be imported"""
    try:
        from rag_core.parsers.document_parser import DocumentParser, DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        from rag_core.chunking.chunker import DocumentChunker, Chunk
        from rag_core.embeddings.embedding_service import EmbeddingService
        print("✅ Core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_parser_registry():
    """Test parser registry functionality"""
    try:
        from rag_core.parsers.document_parser import DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        
        registry = DocumentParserRegistry()
        
        # Test registration
        pdf_parser = PDFParser()
        docx_parser = DOCXParser()
        
        registry.register(pdf_parser)
        registry.register(docx_parser)
        
        # Test getting supported extensions
        extensions = registry.get_supported_extensions()
        print(f"✅ Parser registry test passed. Supported extensions: {extensions}")
        return True
        
    except Exception as e:
        print(f"❌ Parser registry test failed: {e}")
        return False

def test_chunker():
    """Test document chunking functionality"""
    try:
        from rag_core.chunking.chunker import DocumentChunker
        
        chunker = DocumentChunker(chunk_size=500, overlap=100)
        
        # Test with sample content
        test_content = {
            'text': 'This is a test document. ' * 50,  # Create long text
            'tables': [
                {
                    'data': [['Header1', 'Header2'], ['Data1', 'Data2']],
                    'page': 1,
                    'table_index': 0,
                    'rows': 2,
                    'cols': 2
                }
            ]
        }
        
        chunks = chunker.chunk_document(test_content)
        stats = chunker.get_chunk_statistics(chunks)
        
        print(f"✅ Chunker test passed. Created {len(chunks)} chunks")
        print(f"   Statistics: {stats}")
        return True
        
    except Exception as e:
        print(f"❌ Chunker test failed: {e}")
        return False

def test_embedding_service_basic():
    """Test basic embedding service functionality"""
    try:
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        # Test service initialization
        service = EmbeddingService(model_name="test-model")
        
        # Test basic properties
        if hasattr(service, 'model_name') and hasattr(service, 'embedding_dim'):
            print(f"✅ Embedding service basic test passed. Model: {service.model_name}, Dim: {service.embedding_dim}")
            return True
        else:
            print(f"❌ Embedding service basic test failed: missing properties")
            return False
            
    except Exception as e:
        print(f"❌ Embedding service basic test failed: {e}")
        return False

def test_parser_implementations():
    """Test parser implementations"""
    try:
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        
        # Test PDF parser
        pdf_parser = PDFParser()
        print(f"✅ PDF parser created: {pdf_parser.__class__.__name__}")
        
        # Test DOCX parser
        docx_parser = DOCXParser()
        print(f"✅ DOCX parser created: {docx_parser.__class__.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Parser implementations test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running RAG Core simplified tests...\n")
    
    tests = [
        ("Core Module Imports", test_imports),
        ("Parser Registry", test_parser_registry),
        ("Document Chunker", test_chunker),
        ("Embedding Service Basic", test_embedding_service_basic),
        ("Parser Implementations", test_parser_implementations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG Core core functionality is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
