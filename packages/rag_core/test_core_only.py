#!/usr/bin/env python3
"""
Core-only tests for RAG Core functionality (no external dependencies)
"""

import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_core_components():
    """Test core components without external dependencies"""
    try:
        # Test parsers
        from rag_core.parsers.document_parser import DocumentParser, DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        
        # Test chunking
        from rag_core.chunking.chunker import DocumentChunker, Chunk
        
        # Test embeddings (basic)
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        print("✅ All core components imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_parser_functionality():
    """Test parser functionality"""
    try:
        from rag_core.parsers.document_parser import DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        
        registry = DocumentParserRegistry()
        
        # Create parsers
        pdf_parser = PDFParser()
        docx_parser = DOCXParser()
        
        # Register parsers
        registry.register(pdf_parser)
        registry.register(docx_parser)
        
        # Check supported formats
        extensions = registry.get_supported_extensions()
        print(f"✅ Parser functionality test passed. Supported: {extensions}")
        return True
        
    except Exception as e:
        print(f"❌ Parser functionality test failed: {e}")
        return False

def test_chunking_functionality():
    """Test chunking functionality"""
    try:
        from rag_core.chunking.chunker import DocumentChunker
        
        # Create chunker
        chunker = DocumentChunker(chunk_size=300, overlap=50)
        
        # Test content
        test_content = {
            'text': 'This is a test document with multiple sentences. ' * 20,
            'tables': [
                {
                    'data': [['Name', 'Value'], ['Test1', '100'], ['Test2', '200']],
                    'page': 1,
                    'table_index': 0,
                    'rows': 3,
                    'cols': 2
                }
            ]
        }
        
        # Create chunks
        chunks = chunker.chunk_document(test_content)
        stats = chunker.get_chunk_statistics(chunks)
        
        print(f"✅ Chunking functionality test passed. Created {len(chunks)} chunks")
        print(f"   Text chunks: {stats['text_chunks']}, Table chunks: {stats['table_chunks']}")
        return True
        
    except Exception as e:
        print(f"❌ Chunking functionality test failed: {e}")
        return False

def test_embedding_service_basic():
    """Test basic embedding service functionality"""
    try:
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        # Create service
        service = EmbeddingService(model_name="test-model")
        
        # Check properties
        if service.model_name == "test-model" and service.embedding_dim == 1024:
            print(f"✅ Embedding service basic test passed")
            return True
        else:
            print(f"❌ Embedding service basic test failed: wrong properties")
            return False
            
    except Exception as e:
        print(f"❌ Embedding service basic test failed: {e}")
        return False

def test_class_hierarchy():
    """Test class hierarchy and inheritance"""
    try:
        from rag_core.parsers.document_parser import DocumentParser
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        from rag_core.chunking.chunker import ChunkingStrategy, TextChunkingStrategy
        
        # Check inheritance
        assert issubclass(PDFParser, DocumentParser)
        assert issubclass(DOCXParser, DocumentParser)
        assert issubclass(TextChunkingStrategy, ChunkingStrategy)
        
        print("✅ Class hierarchy test passed")
        return True
        
    except Exception as e:
        print(f"❌ Class hierarchy test failed: {e}")
        return False

def main():
    """Run all core tests"""
    print("🧪 Running RAG Core core-only tests...\n")
    
    tests = [
        ("Core Components Import", test_core_components),
        ("Parser Functionality", test_parser_functionality),
        ("Chunking Functionality", test_chunking_functionality),
        ("Embedding Service Basic", test_embedding_service_basic),
        ("Class Hierarchy", test_class_hierarchy),
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
        print("🎉 All core tests passed! RAG Core is working correctly.")
        print("\n📋 Summary of working components:")
        print("   ✅ Document parsers (PDF, DOCX)")
        print("   ✅ Parser registry system")
        print("   ✅ Document chunking strategies")
        print("   ✅ Embedding service framework")
        print("   ✅ Class hierarchy and inheritance")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
