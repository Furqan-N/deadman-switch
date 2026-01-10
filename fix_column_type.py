"""
Script to fix the timeout_period column type from interval to integer
Run this once to fix your database schema.
"""
import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

load_dotenv()

user = os.environ.get("DB_USER")
password = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")
port = os.environ.get("DB_PORT")
database = os.environ.get("DB_NAME")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "temp-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
db = SQLAlchemy(app)

def fix_column_type():
    """Change timeout_period column from interval to integer"""
    with app.app_context():
        try:
            print("Checking current column type...")
            # Check current type
            result = db.session.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'switches' AND column_name = 'timeout_period'
            """))
            current_type = result.scalar()
            print(f"Current column type: {current_type}")
            
            if current_type == 'integer':
                print("Column is already integer type. No changes needed.")
                return
            
            print("Changing column type from interval to integer...")
            
            # Check if table has any data
            count_result = db.session.execute(text("SELECT COUNT(*) FROM switches"))
            row_count = count_result.scalar()
            print(f"Rows in switches table: {row_count}")
            
            if row_count > 0:
                print("Table has existing data. Converting interval values to seconds (integer)...")
                # Convert interval to integer (seconds)
                db.session.execute(text("""
                    ALTER TABLE switches 
                    ALTER COLUMN timeout_period TYPE INTEGER 
                    USING EXTRACT(EPOCH FROM timeout_period)::INTEGER
                """))
            else:
                print("Table is empty. Converting column type directly...")
                # Simple conversion for empty table
                db.session.execute(text("""
                    ALTER TABLE switches 
                    ALTER COLUMN timeout_period TYPE INTEGER
                """))
            
            db.session.commit()
            print("✓ Successfully changed column type to INTEGER!")
            
            # Verify the change
            result = db.session.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'switches' AND column_name = 'timeout_period'
            """))
            new_type = result.scalar()
            print(f"Verified new column type: {new_type}")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing timeout_period column type")
    print("=" * 60)
    fix_column_type()
    print("=" * 60)
    print("Done! You can now try creating a switch again.")
    print("=" * 60)





