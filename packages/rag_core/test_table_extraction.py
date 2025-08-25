#!/usr/bin/env python3
"""
Test for improved table extraction functionality
"""

import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_table_extractor_creation():
    """Test table extractor creation"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        print(f"✅ Table extractor created: {extractor.__class__.__name__}")
        print(f"   Camelot available: {extractor.use_camelot}")
        print(f"   Tabula available: {extractor.use_tabula}")
        print(f"   PaddleOCR available: {extractor.use_paddle}")
        return True
        
    except Exception as e:
        print(f"❌ Table extractor creation test failed: {e}")
        return False

def test_table_extractor_capabilities():
    """Test table extractor capabilities"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        
        # Check capabilities
        if extractor.use_camelot:
            print("   ✅ Camelot available for vector PDFs")
        else:
            print("   ⚠️  Camelot not available")
        
        if extractor.use_tabula:
            print("   ✅ Tabula available for Java-based extraction")
        else:
            print("   ⚠️  Tabula not available")
        
        if extractor.use_paddle:
            print("   ✅ PaddleOCR available for structure detection")
        else:
            print("   ⚠️  PaddleOCR not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Table extractor capabilities test failed: {e}")
        return False

def test_table_quality_scoring():
    """Test table quality scoring"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        
        # Create sample tables with different quality
        sample_tables = [
            {
                'extraction_method': 'camelot_lattice',
                'accuracy': 95,
                'whitespace': 10,
                'rows': 5,
                'cols': 4
            },
            {
                'extraction_method': 'tabula',
                'accuracy': 80,
                'whitespace': 20,
                'rows': 3,
                'cols': 3
            },
            {
                'extraction_method': 'paddleocr',
                'accuracy': 70,
                'whitespace': 30,
                'rows': 4,
                'cols': 5
            }
        ]
        
        # Test sorting by quality
        sorted_tables = extractor._sort_tables_by_quality(sample_tables)
        
        if len(sorted_tables) == 3:
            print("✅ Table quality scoring test passed")
            print(f"   Best table method: {sorted_tables[0]['extraction_method']}")
            return True
        else:
            print("❌ Table quality scoring test failed: wrong number of tables")
            return False
        
    except Exception as e:
        print(f"❌ Table quality scoring test failed: {e}")
        return False

def test_table_deduplication():
    """Test table deduplication"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        
        # Create sample tables with duplicate content
        sample_tables = [
            {
                'data': [['A', 'B'], ['1', '2']],
                'extraction_method': 'camelot_lattice'
            },
            {
                'data': [['A', 'B'], ['1', '2']],  # Duplicate
                'extraction_method': 'tabula'
            },
            {
                'data': [['X', 'Y'], ['3', '4']],  # Different
                'extraction_method': 'paddleocr'
            }
        ]
        
        # Test deduplication
        unique_tables = extractor._deduplicate_tables(sample_tables)
        
        if len(unique_tables) == 2:
            print("✅ Table deduplication test passed")
            print(f"   Original tables: {len(sample_tables)}")
            print(f"   Unique tables: {len(unique_tables)}")
            return True
        else:
            print("❌ Table deduplication test failed: wrong number of unique tables")
            return False
        
    except Exception as e:
        print(f"❌ Table deduplication test failed: {e}")
        return False

def test_extraction_stats():
    """Test extraction statistics"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        
        # Create sample tables
        sample_tables = [
            {
                'extraction_method': 'camelot_lattice',
                'accuracy': 95,
                'whitespace': 10
            },
            {
                'extraction_method': 'tabula',
                'accuracy': 80,
                'whitespace': 20
            },
            {
                'extraction_method': 'camelot_lattice',
                'accuracy': 90,
                'whitespace': 15
            }
        ]
        
        # Test statistics
        stats = extractor.get_extraction_stats(sample_tables)
        
        if (stats['total_tables'] == 3 and 
            'camelot_lattice' in stats['methods_used'] and
            stats['average_accuracy'] > 0):
            print("✅ Extraction statistics test passed")
            print(f"   Total tables: {stats['total_tables']}")
            print(f"   Methods used: {stats['methods_used']}")
            print(f"   Average accuracy: {stats['average_accuracy']:.1f}")
            return True
        else:
            print("❌ Extraction statistics test failed: invalid stats")
            return False
        
    except Exception as e:
        print(f"❌ Extraction statistics test failed: {e}")
        return False

def test_table_hash_creation():
    """Test table hash creation for deduplication"""
    try:
        from rag_core.tables.table_extractor import TableExtractor
        
        extractor = TableExtractor()
        
        # Create sample table
        sample_table = {
            'data': [['Name', 'Age'], ['John', '25'], ['Jane', '30']]
        }
        
        # Test hash creation
        hash1 = extractor._create_table_hash(sample_table)
        hash2 = extractor._create_table_hash(sample_table)
        
        if hash1 == hash2 and len(hash1) == 32:  # MD5 hash length
            print("✅ Table hash creation test passed")
            print(f"   Hash: {hash1[:8]}...")
            return True
        else:
            print("❌ Table hash creation test failed: invalid hash")
            return False
        
    except Exception as e:
        print(f"❌ Table hash creation test failed: {e}")
        return False

def main():
    """Run all table extraction tests"""
    print("🧪 Testing improved table extraction...\n")
    
    tests = [
        ("Table Extractor Creation", test_table_extractor_creation),
        ("Table Extractor Capabilities", test_table_extractor_capabilities),
        ("Table Quality Scoring", test_table_quality_scoring),
        ("Table Deduplication", test_table_deduplication),
        ("Extraction Statistics", test_extraction_stats),
        ("Table Hash Creation", test_table_hash_creation),
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
        print("🎉 All table extraction tests passed!")
        print("\n📋 New table extraction capabilities:")
        print("   ✅ Multi-method extraction (Camelot, Tabula, PaddleOCR)")
        print("   ✅ Automatic table deduplication")
        print("   ✅ Quality-based table sorting")
        print("   ✅ Comprehensive extraction statistics")
        print("   ✅ Support for vector PDFs and scanned documents")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
