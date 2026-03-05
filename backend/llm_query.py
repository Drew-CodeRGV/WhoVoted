"""LLM-powered natural language query interface for voter data."""
import logging
import json
import re
from typing import Dict, List, Optional
import database as db

logger = logging.getLogger(__name__)

class QueryAssistant:
    """Convert natural language questions to SQL queries using local LLM."""
    
    def __init__(self):
        self.model = "llama3.2:3b-instruct"
        self.schema = self._load_schema()
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is available"""
        try:
            import ollama
            # Test connection
            ollama.list()
            logger.info("Ollama connection successful")
        except ImportError:
            logger.warning("Ollama package not installed. Install with: pip install ollama")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
    
    def _load_schema(self) -> str:
        """Load database schema for LLM context"""
        return """
Database Schema for Texas Voter Data:

Table: voters
- vuid (TEXT, PRIMARY KEY): Unique voter ID
- firstname, lastname, middlename, suffix (TEXT): Name components
- birth_year (INTEGER): Year of birth
- sex (TEXT): 'M', 'F', or NULL
- address, city, zip (TEXT): Mailing address
- county (TEXT): County name (e.g., 'Hidalgo', 'Brooks')
- lat, lng (REAL): Geocoded coordinates
- geocoded (INTEGER): 1 if geocoded, 0 if not
- precinct (TEXT): Voting precinct
- congressional_district (TEXT): Current district (e.g., 'TX-15')
- old_congressional_district (TEXT): Previous district (for redistricting analysis)
- state_house_district (TEXT): State house district (e.g., 'HD-35')
- commissioner_district (TEXT): County commissioner precinct
- registered_party (TEXT): Registered party affiliation
- current_party (TEXT): Most recent primary voted in
- registration_date (TEXT): Date registered to vote

Table: voter_elections
- vuid (TEXT): Links to voters.vuid
- election_date (TEXT): Date of election (YYYY-MM-DD)
- election_year (TEXT): Year (e.g., '2026')
- election_type (TEXT): 'primary', 'general', 'runoff'
- voting_method (TEXT): 'early-voting', 'election-day', 'mail-in'
- party_voted (TEXT): 'Democratic', 'Republican', or other
- is_new_voter (INTEGER): 1 if first-time voter, 0 otherwise
- created_at (TEXT): When record was created

Common Queries:
- Find voters by district: WHERE congressional_district = 'TX-15'
- Find new voters: WHERE is_new_voter = 1
- Find party switchers: JOIN voter_elections twice on same vuid with different party_voted
- Count by age group: Use CASE WHEN birth_year BETWEEN ... for age ranges
- Turnout analysis: COUNT voters who voted in specific election_date

Important Notes:
- Always use JOINs when querying across tables
- Use DISTINCT when counting unique voters
- Party names are 'Democratic' and 'Republican' (capitalized)
- Dates are in 'YYYY-MM-DD' format
- Current election is '2026-03-03'
"""
    
    def question_to_sql(self, question: str, context: Optional[Dict] = None) -> Dict:
        """Convert natural language question to SQL query.
        
        Args:
            question: Natural language question
            context: Optional context (e.g., selected district, county)
        
        Returns:
            Dict with 'sql', 'explanation', 'question'
        """
        try:
            import ollama
        except ImportError:
            return {
                'error': 'Ollama not installed. Run: pip install ollama',
                'sql': None
            }
        
        # Add context to question if provided
        context_str = ""
        if context:
            if context.get('district'):
                context_str += f"\nContext: User is viewing {context['district']}"
            if context.get('county'):
                context_str += f"\nContext: User is viewing {context['county']} county"
        
        prompt = f"""You are a SQL expert for a Texas voter database. Convert this question to a SQLite query.

{self.schema}
{context_str}

User Question: {question}

Generate a valid SQLite query that answers the question. Follow these rules:
1. Return ONLY the SQL query, no explanation or markdown
2. Use proper JOINs when querying multiple tables
3. Always use DISTINCT when counting unique voters
4. Add LIMIT 100 unless the question asks for counts/aggregates
5. Use meaningful column aliases
6. For age groups, use CASE WHEN with birth_year ranges

SQL Query:"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent SQL
                    'top_p': 0.9,
                    'num_predict': 500,  # Max tokens for SQL query
                }
            )
            
            sql = response['response'].strip()
            
            # Clean up common formatting issues
            sql = sql.replace('```sql', '').replace('```', '').strip()
            sql = re.sub(r'^SQL Query:\s*', '', sql, flags=re.IGNORECASE)
            sql = sql.strip(';') + ';'  # Ensure single semicolon at end
            
            # Basic SQL injection prevention
            dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
            sql_upper = sql.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {
                        'error': f'Query contains dangerous keyword: {keyword}',
                        'sql': sql,
                        'question': question
                    }
            
            return {
                'sql': sql,
                'question': question,
                'model': self.model,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"LLM query generation failed: {e}")
            return {
                'error': str(e),
                'sql': None,
                'question': question
            }
    
    def execute_and_format(self, sql: str, limit: int = 100) -> Dict:
        """Execute SQL query and format results.
        
        Args:
            sql: SQL query to execute
            limit: Maximum rows to return
        
        Returns:
            Dict with 'success', 'rows', 'count', 'columns', 'sql'
        """
        try:
            # Enforce LIMIT if not present and not an aggregate query
            sql_upper = sql.upper()
            is_aggregate = any(kw in sql_upper for kw in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(', 'GROUP BY'])
            
            if not is_aggregate and 'LIMIT' not in sql_upper:
                sql = sql.rstrip(';') + f' LIMIT {limit};'
            
            conn = db.get_connection()
            cursor = conn.execute(sql)
            results = cursor.fetchall()
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convert to list of dicts
            rows = [dict(row) for row in results]
            
            # Format values for display
            for row in rows:
                for key, value in row.items():
                    if value is None:
                        row[key] = ''
                    elif isinstance(value, float):
                        row[key] = round(value, 2)
            
            return {
                'success': True,
                'rows': rows,
                'count': len(rows),
                'columns': columns,
                'sql': sql,
                'is_aggregate': is_aggregate
            }
            
        except Exception as e:
            logger.error(f"SQL execution failed: {e}\nSQL: {sql}")
            return {
                'success': False,
                'error': str(e),
                'sql': sql,
                'rows': [],
                'count': 0
            }
    
    def explain_results(self, question: str, sql: str, result: Dict) -> str:
        """Generate natural language explanation of query results.
        
        Args:
            question: Original question
            sql: Generated SQL
            result: Query execution result
        
        Returns:
            Natural language explanation
        """
        if not result['success']:
            return f"Query failed: {result.get('error', 'Unknown error')}"
        
        count = result['count']
        is_aggregate = result.get('is_aggregate', False)
        
        if count == 0:
            return "No results found for your query."
        
        try:
            import ollama
            
            # Sample results for context
            sample_rows = result['rows'][:3]
            
            prompt = f"""Explain these query results in 1-2 simple sentences.

Question: {question}
Results: {count} rows returned
Sample data: {json.dumps(sample_rows, indent=2)}

Provide a brief, clear explanation of what the data shows. Be specific about numbers.

Explanation:"""
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.3, 'num_predict': 150}
            )
            
            return response['response'].strip()
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            if is_aggregate:
                return f"Found {count} result(s) from your aggregate query."
            else:
                return f"Found {count} voter(s) matching your criteria."
    
    def suggest_followups(self, question: str, result: Dict) -> List[str]:
        """Suggest related follow-up questions.
        
        Args:
            question: Original question
            result: Query execution result
        
        Returns:
            List of suggested questions
        """
        if not result['success'] or result['count'] == 0:
            return []
        
        try:
            import ollama
            
            prompt = f"""Based on this query, suggest 3 related follow-up questions.

Original question: {question}
Results: {result['count']} rows

Suggest 3 specific follow-up questions (one per line, no numbering):"""
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': 0.5, 'num_predict': 200}
            )
            
            suggestions = [s.strip() for s in response['response'].strip().split('\n') if s.strip()]
            # Remove numbering if present
            suggestions = [re.sub(r'^\d+[\.\)]\s*', '', s) for s in suggestions]
            return suggestions[:3]
            
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return []
