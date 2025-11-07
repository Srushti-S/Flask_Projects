
import sqlite3
import csv
import requests
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "app.db"
CSV_URL = "https://data.cityofchicago.org/api/views/4ijn-s7e5/rows.csv?accessType=DOWNLOAD"
CSV_FILE = "chicago_food_inspections.csv"

def download_data():
    """Download the CSV file from Chicago Data Portal"""
    logger.info(f"Downloading data from {CSV_URL}")
    
    try:
        response = requests.get(CSV_URL, stream=True)
        response.raise_for_status()
        
        with open(CSV_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {os.path.getsize(CSV_FILE)} bytes to {CSV_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
        return False

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def clean_zip(zip_code):
    """Clean and validate ZIP code"""
    if not zip_code:
        return None
    # Remove any extra spaces, take first 5 digits
    cleaned = ''.join(c for c in str(zip_code) if c.isdigit())
    return cleaned[:5] if len(cleaned) >= 5 else None

def clean_phone(phone):
    """Clean phone number"""
    if not phone:
        return None
    # Remove all non-digits
    cleaned = ''.join(c for c in str(phone) if c.isdigit())
    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    return None

def parse_date(date_str):
    """Parse date from various formats"""
    if not date_str:
        return None
    
    try:
        # Try MM/DD/YYYY format (most common in Chicago data)
        dt = datetime.strptime(date_str.split()[0], '%m/%d/%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        try:
            # Try YYYY-MM-DD format
            dt = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
        except:
            return None

def map_risk(risk_str):
    """Map risk categories to our schema"""
    if not risk_str:
        return 'Medium'
    
    risk_lower = risk_str.lower().strip()
    if 'high' in risk_lower or 'risk 1' in risk_lower:
        return 'High'
    elif 'low' in risk_lower or 'risk 3' in risk_lower:
        return 'Low'
    else:
        return 'Medium'

def map_result(result_str):
    """Map inspection results to our schema"""
    if not result_str:
        return 'No Entry'
    
    result_lower = result_str.lower().strip()
    if 'pass' in result_lower:
        return 'Pass'
    elif 'fail' in result_lower:
        return 'Fail'
    elif 'pass w/ conditions' in result_lower:
        return 'Warning'
    elif 'no entry' in result_lower or 'not ready' in result_lower:
        return 'No Entry'
    else:
        return 'Warning'

def import_data(limit=1000):
    """
    Import data from CSV into database
    
    Args:
        limit: Maximum number of records to import (default 1000)
               Set to None to import all records (WARNING: may take a long time)
    """
    logger.info(f"Starting data import (limit: {limit if limit else 'all records'})")
    
    if not os.path.exists(CSV_FILE):
        logger.error(f"CSV file {CSV_FILE} not found. Run download_data() first.")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Track statistics
    facilities_added = 0
    facilities_skipped = 0
    inspections_added = 0
    inspections_skipped = 0
    
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    logger.info(f"Reached limit of {limit} records")
                    break
                
                if i % 100 == 0:
                    logger.info(f"Processing record {i}...")
                
                # Extract facility data
                license_number = row.get('License #', '').strip()
                if not license_number or license_number == 'None':
                    facilities_skipped += 1
                    continue
                
                dba_name = row.get('DBA Name', '').strip() or row.get('AKA Name', '').strip()
                if not dba_name:
                    facilities_skipped += 1
                    continue
                
                facility_type = row.get('Facility Type', 'Restaurant').strip()
                address = row.get('Address', '').strip()
                city = row.get('City', 'Chicago').strip()
                state = row.get('State', 'IL').strip()
                zip_code = clean_zip(row.get('Zip', ''))
                
                if not zip_code:
                    facilities_skipped += 1
                    continue
                
                # Insert or update facility
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO facilities 
                        (license_number, dba_name, facility_type, address, city, state, zip, phone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (license_number, dba_name, facility_type, address, city, state, zip_code, None))
                    
                    if cursor.rowcount > 0:
                        facilities_added += 1
                except Exception as e:
                    logger.debug(f"Error inserting facility: {e}")
                    facilities_skipped += 1
                    continue
                
                # Extract inspection data
                inspection_date = parse_date(row.get('Inspection Date', ''))
                if not inspection_date:
                    inspections_skipped += 1
                    continue
                
                inspection_type = row.get('Inspection Type', 'Routine').strip()
                risk = map_risk(row.get('Risk', ''))
                result = map_result(row.get('Results', ''))
                violations = row.get('Violations', '').strip() or None
                
                # Insert inspection
                try:
                    cursor.execute("""
                        INSERT INTO inspections 
                        (license_number, inspection_date, inspection_type, risk, result, violations_text)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (license_number, inspection_date, inspection_type, risk, result, violations))
                    
                    if cursor.rowcount > 0:
                        inspections_added += 1
                except Exception as e:
                    logger.debug(f"Error inserting inspection: {e}")
                    inspections_skipped += 1
        
        conn.commit()
        
        # Print summary
        logger.info("="*60)
        logger.info("IMPORT COMPLETE")
        logger.info("="*60)
        logger.info(f"Facilities added: {facilities_added}")
        logger.info(f"Facilities skipped: {facilities_skipped}")
        logger.info(f"Inspections added: {inspections_added}")
        logger.info(f"Inspections skipped: {inspections_skipped}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Error during import: {e}")
        conn.rollback()
    finally:
        conn.close()

def quick_stats():
    """Display quick statistics about the database"""
    conn = get_db()
    
    facility_count = conn.execute("SELECT COUNT(*) FROM facilities").fetchone()[0]
    inspection_count = conn.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
    
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    print(f"Total Facilities: {facility_count}")
    print(f"Total Inspections: {inspection_count}")
    
    if inspection_count > 0:
        results = conn.execute("""
            SELECT result, COUNT(*) as count
            FROM inspections
            GROUP BY result
            ORDER BY count DESC
        """).fetchall()
        
        print("\nInspection Results:")
        for row in results:
            print(f"  {row['result']}: {row['count']}")
        
        risks = conn.execute("""
            SELECT risk, COUNT(*) as count
            FROM inspections
            GROUP BY risk
            ORDER BY count DESC
        """).fetchall()
        
        print("\nRisk Levels:")
        for row in risks:
            print(f"  {row['risk']}: {row['count']}")
    
    print("="*60 + "\n")
    
    conn.close()

def main():
    """Main function to run the import"""
    print("\n🍽️  Chicago Food Inspections Data Import")
    print("="*60)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        print("   Run 'python app.py' first to create the database.")
        return
    
    print("Options:")
    print("1. Download latest data from Chicago Data Portal")
    print("2. Import data (first 1000 records - fast)")
    print("3. Import data (first 5000 records)")
    print("4. Import ALL data (WARNING: slow, may take 5-10 minutes)")
    print("5. Show current database stats")
    print("6. Exit")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == '1':
        if download_data():
            print("✅ Download complete!")
            print(f"   File saved: {CSV_FILE}")
            print("   Now run option 2 or 3 to import the data.")
    
    elif choice == '2':
        if not os.path.exists(CSV_FILE):
            print("❌ CSV file not found. Run option 1 first to download data.")
        else:
            import_data(limit=1000)
            quick_stats()
            print("✅ Import complete! Visit http://localhost:5000/ to see the data.")
    
    elif choice == '3':
        if not os.path.exists(CSV_FILE):
            print("❌ CSV file not found. Run option 1 first to download data.")
        else:
            import_data(limit=5000)
            quick_stats()
            print("✅ Import complete! Visit http://localhost:5000/ to see the data.")
    
    elif choice == '4':
        if not os.path.exists(CSV_FILE):
            print("❌ CSV file not found. Run option 1 first to download data.")
        else:
            confirm = input("⚠️  This will import ALL records (250K+). Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                import_data(limit=None)
                quick_stats()
                print("✅ Import complete! Visit http://localhost:5000/ to see the data.")
    
    elif choice == '5':
        quick_stats()
    
    elif choice == '6':
        print("👋 Goodbye!")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
