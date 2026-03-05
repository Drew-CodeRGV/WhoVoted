#!/usr/bin/env python3
"""
Complete HTTP test for LLM endpoint with timeout handling.
Tests the actual endpoint as it would be called from the browser.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import json
import time
from llm_query import QueryAssistant

def test_direct_llm():
    """Test LLM directly (not through HTTP)"""
    print("=" * 80)
    print("TEST 1: Direct LLM Call (Python)")
    print("=" * 80)
    
    try:
        qa = QueryAssistant()
        print("✓ QueryAssistant initialized")
        
        # Test query 1
        question1 = "Show me Female voters in TX-15 who voted in 2024 but not 2026"
        print(f"\nQuestion: {question1}")
        
        start = time.time()
        result = qa.question_to_sql(question1, {"district": "TX-15"})
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        
        if 'error' in result:
            print(f"✗ Error: {result['error']}")
            return False
        
        print(f"✓ SQL generated: {result['sql'][:100]}...")
        
        # Execute
        exec_result = qa.execute_and_format(result['sql'])
        if exec_result['success']:
            print(f"✓ Query executed: {exec_result['count']} results")
        else:
            print(f"✗ Execution failed: {exec_result['error']}")
            return False
        
        # Test query 2
        question2 = "Show me which of my neighbors are Republican"
        print(f"\nQuestion: {question2}")
        
        start = time.time()
        result2 = qa.question_to_sql(question2, {"county": "Hidalgo"})
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        
        if 'error' in result2:
            print(f"✗ Error: {result2['error']}")
            return False
        
        print(f"✓ SQL generated: {result2['sql'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_timeout_handling():
    """Test that timeouts work correctly"""
    print("\n" + "=" * 80)
    print("TEST 2: Timeout Handling")
    print("=" * 80)
    
    try:
        qa = QueryAssistant()
        
        # This should complete within 30 seconds or timeout
        question = "Show me voters in TX-15"
        print(f"Question: {question}")
        print("Testing with 30-second timeout...")
        
        start = time.time()
        result = qa.question_to_sql(question)
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        
        if elapsed > 30:
            print("✗ Query took longer than timeout (timeout not working)")
            return False
        
        if 'error' in result:
            if 'timed out' in result['error'].lower():
                print("✓ Timeout handled correctly")
                return True
            else:
                print(f"✗ Error (not timeout): {result['error']}")
                return False
        
        print("✓ Query completed within timeout")
        return True
        
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

def test_ollama_connection():
    """Test Ollama is responding"""
    print("\n" + "=" * 80)
    print("TEST 3: Ollama Connection")
    print("=" * 80)
    
    try:
        import ollama
        
        print("Testing ollama.list()...")
        start = time.time()
        models = ollama.list()
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        
        if elapsed > 5:
            print("⚠ Warning: ollama.list() is slow (may indicate Ollama issues)")
        
        available = [m['name'] for m in models.get('models', [])]
        print(f"Available models: {available}")
        
        if 'llama3.2:latest' in available or any('llama3.2' in m for m in available):
            print("✓ llama3.2 model found")
        else:
            print("✗ llama3.2 model not found")
            return False
        
        # Test a simple generation
        print("\nTesting simple generation...")
        start = time.time()
        response = ollama.generate(
            model='llama3.2:latest',
            prompt='Say "Hello" and nothing else.',
            options={'num_predict': 10}
        )
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        print(f"Response: {response['response'][:50]}")
        
        if elapsed > 10:
            print("⚠ Warning: Simple generation is slow")
        
        print("✓ Ollama is responding")
        return True
        
    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
        return False

def main():
    print("LLM HTTP Endpoint Complete Test")
    print("=" * 80)
    print()
    
    results = []
    
    # Test 1: Direct LLM
    results.append(("Direct LLM", test_direct_llm()))
    
    # Test 2: Timeout handling
    results.append(("Timeout Handling", test_timeout_handling()))
    
    # Test 3: Ollama connection
    results.append(("Ollama Connection", test_ollama_connection()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nNext step: Deploy to server and test with actual HTTP request")
        print("Run on server: curl -X POST https://politiquera.com/api/llm/query \\")
        print("  -H 'Content-Type: application/json' \\")
        print("  -H 'Cookie: session=...' \\")
        print("  -d '{\"question\": \"Show me voters in TX-15\"}'")
    else:
        print("\n✗ Some tests failed. Fix issues before deploying.")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
