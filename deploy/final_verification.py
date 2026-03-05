#!/usr/bin/env python3
"""Final verification of AI search functionality with user's exact queries."""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

from llm_query import QueryAssistant

print("=" * 80)
print("FINAL VERIFICATION - USER'S EXACT QUERIES")
print("=" * 80)

qa = QueryAssistant()

# User's exact test queries
test_cases = [
    {
        "name": "Query 1: Female voters in TX-15",
        "question": "Show me Female voters in TX-15 who voted in 2024 but not 2026",
        "context": {}
    },
    {
        "name": "Query 2: Republican neighbors (with location)",
        "question": "Show me which of my neighbors are Republican",
        "context": {"lat": 26.2034, "lng": -98.2300}  # Example Hidalgo County coords
    }
]

all_passed = True

for i, test in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}: {test['name']}")
    print(f"{'=' * 80}")
    print(f"Question: {test['question']}")
    print(f"Context: {test['context']}")
    
    try:
        # Generate SQL
        print("\n[Step 1/4] Generating SQL...")
        sql_result = qa.question_to_sql(test['question'], test['context'])
        
        if 'error' in sql_result:
            print(f"✗ FAILED: {sql_result['error']}")
            all_passed = False
            continue
        
        print(f"✓ SQL Generated:")
        print(f"  {sql_result['sql'][:200]}...")
        
        # Execute SQL
        print("\n[Step 2/4] Executing SQL...")
        exec_result = qa.execute_and_format(sql_result['sql'])
        
        if not exec_result['success']:
            print(f"✗ FAILED: {exec_result.get('error', 'Unknown error')}")
            print(f"  SQL: {sql_result['sql']}")
            all_passed = False
            continue
        
        print(f"✓ Execution successful: {exec_result['count']} rows returned")
        if exec_result['count'] > 0:
            print(f"  Columns: {', '.join(exec_result['columns'][:5])}...")
            print(f"  Sample row: {exec_result['rows'][0] if exec_result['rows'] else 'N/A'}")
        
        # Generate explanation
        print("\n[Step 3/4] Generating explanation...")
        explanation = qa.explain_results(test['question'], sql_result['sql'], exec_result)
        print(f"✓ Explanation: {explanation[:150]}...")
        
        # Generate suggestions
        print("\n[Step 4/4] Generating follow-up suggestions...")
        suggestions = qa.suggest_followups(test['question'], exec_result)
        print(f"✓ Suggestions ({len(suggestions)}):")
        for j, suggestion in enumerate(suggestions, 1):
            print(f"  {j}. {suggestion}")
        
        print(f"\n✓✓✓ TEST {i} PASSED ✓✓✓")
        
    except Exception as e:
        print(f"\n✗✗✗ TEST {i} FAILED ✗✗✗")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✓✓✓ ALL TESTS PASSED - SYSTEM READY ✓✓✓")
    print("=" * 80)
    print("\nThe AI search is fully functional and ready for use.")
    print("Users can now:")
    print("  1. Sign in to https://politiquera.com")
    print("  2. Click the brain icon (🧠) to open AI search")
    print("  3. Enter natural language queries")
    print("  4. View results with AI explanations and suggestions")
    sys.exit(0)
else:
    print("✗✗✗ SOME TESTS FAILED ✗✗✗")
    print("=" * 80)
    sys.exit(1)
