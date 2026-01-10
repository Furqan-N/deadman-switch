"""
Migration script to create password_reset_tokens table
Run this once to create the table for password reset functionality.
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
    """Create password_reset_tokens table"""
    with app.app_context():
        try:
            print("Checking if password_reset_tokens table exists...")
            
            # Check if table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'password_reset_tokens'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("password_reset_tokens table already exists")
                return
            
            print("Creating password_reset_tokens table...")
            db.session.execute(text("""
                CREATE TABLE password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """))
            
            # Create index on token for faster lookups
            db.session.execute(text("""
                CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
            """))
            
            # Create index on user_id
            db.session.execute(text("""
                CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
            """))
            
            db.session.commit()
            print("✓ Successfully created password_reset_tokens table")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Create Password Reset Tokens Table")
    print("=" * 60)
    migrate_database()
    print("=" * 60)





