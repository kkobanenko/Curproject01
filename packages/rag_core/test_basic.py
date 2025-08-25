#!/usr/bin/env python3
"""
Basic tests for RAG Core functionality
"""

import asyncio
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from rag_core.parsers.document_parser import DocumentParser, DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        from rag_core.chunking.chunker import DocumentChunker, Chunk
        from rag_core.embeddings.embedding_service import EmbeddingService
        from rag_core.vectorstore.pgvector_store import PgVectorStore
        from rag_core.rag_pipeline import RAGPipeline
        print("✅ All modules imported successfully")
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

def test_embedding_service():
    """Test embedding service functionality"""
    try:
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        # Test local service (doesn't require Ollama)
        service = EmbeddingService(model_name="test-model")
        
        # Test embedding generation
        test_text = "This is a test sentence."
        embedding = service.get_embedding(test_text)
        
        if len(embedding) == service.get_embedding_dimension():
            print(f"✅ Embedding service test passed. Generated {len(embedding)}-dim embedding")
            return True
        else:
            print(f"❌ Embedding service test failed: wrong dimension")
            return False
            
    except Exception as e:
        print(f"❌ Embedding service test failed: {e}")
        return False

async def test_async_functionality():
    """Test async functionality"""
    try:
        from rag_core.embeddings.embedding_service import EmbeddingService
        
        service = EmbeddingService(model_name="test-model")
        
        # Test async embedding generation
        test_texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = await service.get_embeddings_batch_async(test_texts)
        
        if len(embeddings) == len(test_texts):
            print(f"✅ Async functionality test passed. Generated {len(embeddings)} embeddings")
            return True
        else:
            print(f"❌ Async functionality test failed: wrong number of embeddings")
            return False
            
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running RAG Core basic tests...\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Parser Registry", test_parser_registry),
        ("Document Chunker", test_chunker),
        ("Embedding Service", test_embedding_service),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    # Test async functionality
    print("Testing Async Functionality...")
    try:
        if asyncio.run(test_async_functionality()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
    print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG Core is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
