import pymysql
from config import DB_CONFIG
import json
from datetime import date, datetime

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
            print("Successfully connected to MySQL database")
            return True
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database connection: {str(e)}")
    
    def execute_query(self, sql_query):
        """Execute SQL query and return results"""
        try:
            if not self.connection or not self.cursor:
                if not self.connect():
                    return None, "Failed to connect to database"
            
            self.cursor.execute(sql_query)
            
            if sql_query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                
                for row in results:
                    for key, value in row.items():
                        if isinstance(value, (date, datetime)):
                            row[key] = value.strftime('%Y-%m-%d')
                
                return results, None
            else:
                self.connection.commit()
                affected_rows = self.cursor.rowcount
                return f"Query executed successfully. {affected_rows} rows affected.", None
                
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(f"{error_msg}")
            return None, error_msg
    
    def test_connection(self):
        """Test database connection and show sample data"""
        try:
            if self.connect():
                test_query = "SELECT COUNT(*) as total_employees FROM emp_info"
                result, error = self.execute_query(test_query)
                if result:
                    print(f"Database test successful. Total employees: {result[0]['total_employees']}")
                    return True
                else:
                    print(f"Database test failed: {error}")
                    return False
            return False
        except Exception as e:
            print(f"Database test failed: {str(e)}")
            return False