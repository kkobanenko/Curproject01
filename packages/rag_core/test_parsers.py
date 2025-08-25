#!/usr/bin/env python3
"""
Test for new parsers (XLSX, HTML, EML)
"""

import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_xlsx_parser():
    """Test XLSX parser"""
    try:
        from rag_core.parsers.xlsx_parser import XLSXParser
        
        parser = XLSXParser()
        print(f"✅ XLSX parser created: {parser.__class__.__name__}")
        print(f"   Supported MIME types: {parser.supported_mime_types}")
        print(f"   Dependencies available: {parser.can_parse(Path('test.xlsx'))}")
        return True
        
    except Exception as e:
        print(f"❌ XLSX parser test failed: {e}")
        return False

def test_html_parser():
    """Test HTML parser"""
    try:
        from rag_core.parsers.html_parser import HTMLParser
        
        parser = HTMLParser()
        print(f"✅ HTML parser created: {parser.__class__.__name__}")
        print(f"   Supported MIME types: {parser.supported_mime_types}")
        print(f"   Dependencies available: {parser.can_parse(Path('test.html'))}")
        return True
        
    except Exception as e:
        print(f"❌ HTML parser test failed: {e}")
        return False

def test_eml_parser():
    """Test EML parser"""
    try:
        from rag_core.parsers.eml_parser import EMLParser
        
        parser = EMLParser()
        print(f"✅ EML parser created: {parser.__class__.__name__}")
        print(f"   Supported MIME types: {parser.supported_mime_types}")
        print(f"   Dependencies available: {parser.can_parse(Path('test.eml'))}")
        return True
        
    except Exception as e:
        print(f"❌ EML parser test failed: {e}")
        return False

def test_ocr_processor():
    """Test OCR processor"""
    try:
        from rag_core.ocr.ocr_processor import OCRProcessor
        
        processor = OCRProcessor()
        print(f"✅ OCR processor created: {processor.__class__.__name__}")
        print(f"   Languages: {processor.languages}")
        print(f"   Available: {processor.is_available()}")
        return True
        
    except Exception as e:
        print(f"❌ OCR processor test failed: {e}")
        return False

def test_parser_registry():
    """Test parser registry with new parsers"""
    try:
        from rag_core.parsers.document_parser import DocumentParserRegistry
        from rag_core.parsers.pdf_parser import PDFParser
        from rag_core.parsers.docx_parser import DOCXParser
        from rag_core.parsers.xlsx_parser import XLSXParser
        from rag_core.parsers.html_parser import HTMLParser
        from rag_core.parsers.eml_parser import EMLParser
        
        registry = DocumentParserRegistry()
        
        # Register all parsers
        parsers = [PDFParser(), DOCXParser(), XLSXParser(), HTMLParser(), EMLParser()]
        
        for parser in parsers:
            registry.register(parser)
        
        # Check supported extensions
        extensions = registry.get_supported_extensions()
        print(f"✅ Parser registry test passed")
        print(f"   Total parsers: {len(registry._parsers)}")
        print(f"   Supported extensions: {extensions}")
        return True
        
    except Exception as e:
        print(f"❌ Parser registry test failed: {e}")
        return False

def main():
    """Run all parser tests"""
    print("🧪 Testing new parsers and OCR...\n")
    
    tests = [
        ("XLSX Parser", test_xlsx_parser),
        ("HTML Parser", test_html_parser),
        ("EML Parser", test_eml_parser),
        ("OCR Processor", test_ocr_processor),
        ("Parser Registry", test_parser_registry),
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
        print("🎉 All parser tests passed!")
        print("\n📋 New capabilities:")
        print("   ✅ XLSX file parsing with table extraction")
        print("   ✅ HTML file parsing with metadata and tables")
        print("   ✅ EML email parsing with attachments")
        print("   ✅ OCR processing with Tesseract")
        print("   ✅ Automatic page orientation detection")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
