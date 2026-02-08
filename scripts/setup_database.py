"""
Setup database for horror movie recommender
Supports both PostgreSQL and SQLite
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlite3

project_root = Path(__file__).parent.parent

def setup_postgres():
    """Setup PostgreSQL database"""
    print("Setting up PostgreSQL database...")

    # Connection parameters (adjust as needed)
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }

    db_name = 'horror_recommender'

    try:
        # Connect to postgres to create database
        conn = psycopg2.connect(**db_params, database='postgres')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f'CREATE DATABASE {db_name}')
            print(f"✓ Created database: {db_name}")
        else:
            print(f"✓ Database already exists: {db_name}")

        cursor.close()
        conn.close()

        # Connect to new database and run schema
        conn = psycopg2.connect(**db_params, database=db_name)
        cursor = conn.cursor()

        # Read and execute schema
        schema_path = project_root / 'schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        cursor.execute(schema_sql)
        conn.commit()

        print("✓ Schema created successfully")

        cursor.close()
        conn.close()

        # Save connection string
        conn_string = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_name}"

        env_path = project_root / '.env'
        with open(env_path, 'a') as f:
            f.write(f"\n# Database\nDATABASE_URL={conn_string}\n")

        print(f"✓ Connection string saved to .env")
        return conn_string

    except Exception as e:
        print(f"❌ Error setting up PostgreSQL: {e}")
        return None


def setup_sqlite():
    """Setup SQLite database"""
    print("Setting up SQLite database...")

    db_path = project_root / 'data' / 'horror_recommender.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Read schema and adapt for SQLite
        schema_path = project_root / 'schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # SQLite adaptations
        schema_sql = schema_sql.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        schema_sql = schema_sql.replace('JSONB', 'TEXT')
        schema_sql = schema_sql.replace('NUMERIC', 'REAL')
        schema_sql = schema_sql.replace('TIMESTAMP', 'TEXT')
        schema_sql = schema_sql.replace('DEFAULT NOW()', "DEFAULT (datetime('now'))")

        # Remove PostgreSQL-specific syntax
        schema_sql = schema_sql.replace('CREATE OR REPLACE FUNCTION', '-- CREATE OR REPLACE FUNCTION')
        schema_sql = schema_sql.replace('CREATE TRIGGER', '-- CREATE TRIGGER')
        schema_sql = schema_sql.replace('USING GIN', '')

        # Execute schema
        cursor.executescript(schema_sql)
        conn.commit()

        print(f"✓ Database created: {db_path}")
        print(f"✓ Schema created successfully")

        cursor.close()
        conn.close()

        # Save database path
        env_path = project_root / '.env'
        with open(env_path, 'a') as f:
            f.write(f"\n# Database\nDATABASE_URL=sqlite:///{db_path}\n")

        print(f"✓ Database path saved to .env")
        return f"sqlite:///{db_path}"

    except Exception as e:
        print(f"❌ Error setting up SQLite: {e}")
        return None


if __name__ == '__main__':
    print("=" * 70)
    print("HORROR MOVIE RECOMMENDER - DATABASE SETUP")
    print("=" * 70)

    print("\nChoose database:")
    print("1. PostgreSQL (recommended for production)")
    print("2. SQLite (easier setup, good for development)")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == '1':
        conn_string = setup_postgres()
    elif choice == '2':
        conn_string = setup_sqlite()
    else:
        print("❌ Invalid choice")
        sys.exit(1)

    if conn_string:
        print("\n" + "=" * 70)
        print("✓ DATABASE SETUP COMPLETE")
        print("=" * 70)
        print(f"\nConnection string: {conn_string}")
        print("\nNext steps:")
        print("1. Run: python scripts/import_existing_data.py")
        print("2. Run: python scripts/download_letterboxd.py")
    else:
        print("\n❌ Setup failed")
        sys.exit(1)
