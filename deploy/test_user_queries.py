#!/usr/bin/env python3
"""
Test the exact user queries to verify LLM functionality.
This script tests both queries the user requested:
1. "Show me Female voters in TX-15 who voted in 2024 but not 2026"
2. "Show me which of my neighbors are Republican"
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import time
from llm_query import QueryAssistant

def test_query_1():
    """Test: Show me Female voters in TX-15 who voted in 2024 but not 2026"""
    print("=" * 80)
    print("QUERY 1: Female voters in TX-15 who voted in 2024 but not 2026")
    print("=" * 80)
    
    try:
        qa = QueryAssistant()
        question = "Show me Female voters in TX-15 who voted in 2024 but not 2026"
        context = {"district": "TX-15", "county": "Hidalgo"}
        
        print(f"Question: {question}")
        print(f"Context: {context}")
        print()
        
        # Step 1: Generate SQL
        print("Step 1: Generating SQL...")
        start = time.time()
        sql_result = qa.question_to_sql(question, context)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        
        if 'error' in sql_result:
            print(f"  ✗ Error: {sql_result['error']}")
            return False
        
        print(f"  ✓ SQL generated")
        print(f"  SQL: {sql_result['sql']}")
        print()
        
        # Step 2: Execute SQL
        print("Step 2: Executing SQL...")
        start = time.time()
        exec_result = qa.execute_and_format(sql_result['sql'])
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        
        if not exec_result['success']:
            print(f"  ✗ Execution failed: {exec_result['error']}")
            return False
        
        print(f"  ✓ Query executed successfully")
        print(f"  Results: {exec_result['count']} voters found")
        
        # Show sample results
        if exec_result['count'] > 0:
            print(f"  Columns: {', '.join(exec_result['columns'])}")
            print(f"  Sample (first 3):")
            for i, row in enumerate(exec_result['rows'][:3], 1):
                print(f"    {i}. {row}")
        print()
        
        # Step 3: Generate explanation
        print("Step 3: Generating explanation...")
        start = time.time()
        explanation = qa.explain_results(question, sql_result['sql'], exec_result)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Explanation: {explanation}")
        print()
        
        # Step 4: Generate suggestions
        print("Step 4: Generating suggestions...")
        start = time.time()
        suggestions = qa.suggest_followups(question, exec_result)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        if suggestions:
            print(f"  Suggestions:")
            for i, s in enumerate(suggestions, 1):
                print(f"    {i}. {s}")
        else:
            print(f"  No suggestions generated")
        print()
        
        print("✓ QUERY 1 PASSED")
        return True
        
    except Exception as e:
        print(f"✗ QUERY 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_2():
    """Test: Show me which of my neighbors are Republican"""
    print("=" * 80)
    print("QUERY 2: Which of my neighbors are Republican")
    print("=" * 80)
    
    try:
        qa = QueryAssistant()
        question = "Show me which of my neighbors are Republican"
        # Simulate user location (Hidalgo County coordinates)
        context = {
            "county": "Hidalgo",
            "user_location": {"lat": 26.2034, "lng": -98.2300}
        }
        
        print(f"Question: {question}")
        print(f"Context: {context}")
        print()
        
        # Step 1: Generate SQL
        print("Step 1: Generating SQL...")
        start = time.time()
        sql_result = qa.question_to_sql(question, context)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        
        if 'error' in sql_result:
            print(f"  ✗ Error: {sql_result['error']}")
            return False
        
        print(f"  ✓ SQL generated")
        print(f"  SQL: {sql_result['sql']}")
        print()
        
        # Step 2: Execute SQL
        print("Step 2: Executing SQL...")
        start = time.time()
        exec_result = qa.execute_and_format(sql_result['sql'])
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        
        if not exec_result['success']:
            print(f"  ✗ Execution failed: {exec_result['error']}")
            return False
        
        print(f"  ✓ Query executed successfully")
        print(f"  Results: {exec_result['count']} voters found")
        
        # Show sample results
        if exec_result['count'] > 0:
            print(f"  Columns: {', '.join(exec_result['columns'])}")
            print(f"  Sample (first 3):")
            for i, row in enumerate(exec_result['rows'][:3], 1):
                print(f"    {i}. {row}")
        print()
        
        # Step 3: Generate explanation
        print("Step 3: Generating explanation...")
        start = time.time()
        explanation = qa.explain_results(question, sql_result['sql'], exec_result)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Explanation: {explanation}")
        print()
        
        print("✓ QUERY 2 PASSED")
        return True
        
    except Exception as e:
        print(f"✗ QUERY 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print()
    print("=" * 80)
    print("TESTING USER QUERIES")
    print("=" * 80)
    print()
    
    results = []
    
    # Test Query 1
    results.append(("Query 1 (Female TX-15 voters)", test_query_1()))
    print()
    
    # Test Query 2
    results.append(("Query 2 (Republican neighbors)", test_query_2()))
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    print()
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print()
        print("The LLM is working correctly. Deploy to production and test via browser.")
    else:
        print("✗ SOME TESTS FAILED")
        print()
        print("Fix the issues before deploying to production.")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
