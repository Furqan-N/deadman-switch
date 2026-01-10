"""
Script to fix the foreign key constraint to point to 'users' table instead of 'user'
Run this once to fix your database foreign key.
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

def fix_foreign_key():
    """Fix foreign key constraint to point to 'users' table"""
    with app.app_context():
        try:
            print("Checking current foreign key constraint...")
            
            # Check what table the foreign key currently references
            result = db.session.execute(text("""
                SELECT 
                    tc.constraint_name, 
                    tc.table_name, 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND tc.table_name = 'switches'
                  AND kcu.column_name = 'user_id'
            """))
            
            fk_info = result.fetchone()
            if fk_info:
                print(f"Current foreign key: {fk_info[0]}")
                print(f"References table: {fk_info[3]}")
                print(f"References column: {fk_info[4]}")
                
                if fk_info[3] == 'users':
                    print("Foreign key already points to 'users' table. No changes needed.")
                    return
            else:
                print("No foreign key constraint found. This is unexpected.")
                return
            
            print("\nDropping old foreign key constraint...")
            # Drop the old constraint
            db.session.execute(text("""
                ALTER TABLE switches 
                DROP CONSTRAINT switches_user_id_fkey
            """))
            
            print("Creating new foreign key constraint pointing to 'users' table...")
            # Create new constraint pointing to 'users'
            db.session.execute(text("""
                ALTER TABLE switches 
                ADD CONSTRAINT switches_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES users(id)
            """))
            
            db.session.commit()
            print("✓ Successfully fixed foreign key constraint!")
            
            # Verify the change
            result = db.session.execute(text("""
                SELECT 
                    tc.constraint_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND tc.table_name = 'switches'
                  AND kcu.column_name = 'user_id'
            """))
            
            fk_info = result.fetchone()
            if fk_info:
                print(f"Verified: Foreign key now points to '{fk_info[1]}.{fk_info[2]}'")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing foreign key constraint")
    print("=" * 60)
    fix_foreign_key()
    print("=" * 60)
    print("Done! You can now try creating a switch again.")
    print("=" * 60)





