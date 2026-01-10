"""
Migration script to add email tracking fields to switches table
Run this once to add the new columns to your database.
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

def migrate_database():
    """Add reminder_sent and trigger_email_sent columns to switches table"""
    with app.app_context():
        try:
            print("Checking if columns already exist...")
            
            # Check if columns exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'switches' AND column_name IN ('reminder_sent', 'trigger_email_sent')
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'reminder_sent' not in existing_columns:
                print("Adding reminder_sent column...")
                db.session.execute(text("""
                    ALTER TABLE switches 
                    ADD COLUMN reminder_sent BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("✓ Added reminder_sent column")
            else:
                print("reminder_sent column already exists")
            
            if 'trigger_email_sent' not in existing_columns:
                print("Adding trigger_email_sent column...")
                db.session.execute(text("""
                    ALTER TABLE switches 
                    ADD COLUMN trigger_email_sent BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("✓ Added trigger_email_sent column")
            else:
                print("trigger_email_sent column already exists")
            
            db.session.commit()
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add Email Tracking Fields")
    print("=" * 60)
    migrate_database()
    print("=" * 60)





