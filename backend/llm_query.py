"""LLM-powered natural language query interface for voter data."""
import logging
import json
import re
import threading
from typing import Dict, List, Optional
import database as db

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Raised when an operation times out"""
    pass

def run_with_timeout(func, args=(), kwargs=None, timeout=30):
    """Run a function with a timeout using threading.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments
        timeout: Timeout in seconds
    
    Returns:
        Function result
    
    Raises:
        TimeoutError: If function doesn't complete within timeout
    """
    if kwargs is None:
        kwargs = {}
    
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

class QueryAssistant:
    """Convert natural language questions to SQL queries using local LLM."""
    
    def __init__(self):
        self.model = "llama3.2:latest"
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

Table: voters (voter demographics and registration info)
Columns:
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

Table: voter_elections (voting history - one row per election per voter)
Columns:
- vuid (TEXT): Links to voters.vuid
- election_date (TEXT): Date of election (YYYY-MM-DD)
- election_year (TEXT): Year (e.g., '2026', '2024')
- election_type (TEXT): 'primary', 'general', 'runoff'
- voting_method (TEXT): 'early-voting', 'election-day', 'mail-in'
- party_voted (TEXT): 'Democratic', 'Republican', or other
- is_new_voter (INTEGER): 1 if first-time voter, 0 otherwise
- created_at (TEXT): When record was created

IMPORTANT: election_date, election_year, party_voted, and is_new_voter are ONLY in voter_elections table, NOT in voters table!

Common Query Patterns:
- Find voters by district: SELECT * FROM voters WHERE congressional_district = 'TX-15'
- Find voters who voted in specific election: SELECT v.* FROM voters v JOIN voter_elections ve ON v.vuid = ve.vuid WHERE ve.election_year = '2026'
- Find party switchers: Use two JOINs to voter_elections with different party_voted values
- Find voters who voted in X but not Y: Use EXISTS and NOT EXISTS subqueries
- Count by age group: Use CASE WHEN with birth_year ranges

Important Notes:
- Always JOIN voters and voter_elections on vuid
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

CRITICAL RULES - READ CAREFULLY:
1. Return ONLY the SQL query, no explanation or markdown
2. NEVER select columns from the wrong table:
   - voters table has: vuid, firstname, lastname, middlename, suffix, birth_year, sex, address, city, zip, county, lat, lng, geocoded, precinct, congressional_district, old_congressional_district, state_house_district, commissioner_district, registered_party, current_party, registration_date
   - voter_elections table has: vuid, election_date, election_year, election_type, voting_method, party_voted, is_new_voter, created_at
3. When selecting columns, use the correct table alias (v for voters, ve for voter_elections)
4. Always use proper JOINs when querying multiple tables
5. Use DISTINCT when counting unique voters
6. Add LIMIT 100 unless the question asks for counts/aggregates
7. For age groups, use CASE WHEN with birth_year ranges
8. To find voters who voted in one election but not another, use EXISTS/NOT EXISTS subqueries

EXAMPLE: "Show voters who voted in 2024 but not 2026"
SELECT DISTINCT v.vuid, v.firstname, v.lastname
FROM voters v
WHERE EXISTS (
    SELECT 1 FROM voter_elections ve WHERE ve.vuid = v.vuid AND ve.election_year = '2024'
)
AND NOT EXISTS (
    SELECT 1 FROM voter_elections ve WHERE ve.vuid = v.vuid AND ve.election_year = '2026'
);

SQL Query:"""

        try:
            import ollama
            
            # Wrap ollama.generate in timeout
            def call_ollama():
                return ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.1,  # Low temperature for consistent SQL
                        'top_p': 0.9,
                        'num_predict': 500,  # Max tokens for SQL query
                    }
                )
            
            logger.info("Calling Ollama with 30s timeout...")
            response = run_with_timeout(call_ollama, timeout=30)
            logger.info("Ollama call completed")
            
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
            
        except TimeoutError as e:
            logger.error(f"LLM query generation timed out: {e}")
            return {
                'error': 'Query generation timed out. Ollama may be overloaded or not responding.',
                'sql': None,
                'question': question
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
            
            # Wrap in timeout
            def call_ollama():
                return ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={'temperature': 0.3, 'num_predict': 150}
                )
            
            response = run_with_timeout(call_ollama, timeout=15)
            return response['response'].strip()
            
        except TimeoutError as e:
            logger.warning(f"Explanation generation timed out: {e}")
            if is_aggregate:
                return f"Found {count} result(s) from your aggregate query."
            else:
                return f"Found {count} voter(s) matching your criteria."
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
            
            # Wrap in timeout
            def call_ollama():
                return ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={'temperature': 0.5, 'num_predict': 200}
                )
            
            response = run_with_timeout(call_ollama, timeout=15)
            
            suggestions = [s.strip() for s in response['response'].strip().split('\n') if s.strip()]
            # Remove numbering if present
            suggestions = [re.sub(r'^\d+[\.\)]\s*', '', s) for s in suggestions]
            return suggestions[:3]
            
        except TimeoutError as e:
            logger.warning(f"Follow-up generation timed out: {e}")
            return []
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return []
