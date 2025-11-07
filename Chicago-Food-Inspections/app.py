
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import os
import re
from datetime import datetime
import logging
from typing import Optional, Dict, List, Tuple

# ==================== CONFIGURATION ====================

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "app.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== FLASK APP SETUP ====================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# ==================== DATABASE HELPERS ====================

def get_db() -> sqlite3.Connection:
    """
    Get database connection with Row factory for dict-like access.
    
    Returns:
        sqlite3.Connection: Database connection with foreign keys enabled
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db() -> None:
    """Initialize database from schema.sql file."""
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql = f.read()
        conn = get_db()
        conn.executescript(sql)
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

# ==================== VALIDATION HELPERS ====================

def validate_zip(zip_code: str) -> bool:
    """Validate ZIP code format (5 or 9 digits)."""
    return bool(re.match(r'^\d{5}(-\d{4})?$', zip_code))

def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:  # Phone is optional
        return True
    # Allow various formats: (312) 555-0101, 312-555-0101, 3125550101
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\d{10}$', cleaned))

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_license_number(license_number: str) -> Tuple[bool, str]:
    """
    Validate license number format and uniqueness.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not license_number or len(license_number.strip()) < 3:
        return False, "License number must be at least 3 characters"
    
    if not re.match(r'^[A-Z0-9\-]+$', license_number):
        return False, "License number can only contain uppercase letters, numbers, and hyphens"
    
    return True, ""

def validate_facility_data(data: Dict) -> Tuple[bool, str]:
    """
    Validate facility form data.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    required_fields = ['license_number', 'dba_name', 'facility_type', 'address', 'city', 'state', 'zip']
    
    for field in required_fields:
        if not data.get(field, '').strip():
            return False, f"Field '{field}' is required"
    
    # Validate ZIP
    if not validate_zip(data['zip']):
        return False, "Invalid ZIP code format (use 12345 or 12345-6789)"
    
    # Validate phone
    if data.get('phone') and not validate_phone(data['phone']):
        return False, "Invalid phone number format"
    
    # Validate license number
    is_valid, msg = validate_license_number(data['license_number'])
    if not is_valid:
        return False, msg
    
    return True, ""

def validate_inspection_data(data: Dict) -> Tuple[bool, str]:
    """
    Validate inspection form data.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    required_fields = ['license_number', 'inspection_date', 'inspection_type', 'risk', 'result']
    
    for field in required_fields:
        if not data.get(field, '').strip():
            return False, f"Field '{field}' is required"
    
    # Validate date
    if not validate_date(data['inspection_date']):
        return False, "Invalid date format (use YYYY-MM-DD)"
    
    # Validate risk level
    if data['risk'] not in ['High', 'Medium', 'Low']:
        return False, "Invalid risk level"
    
    # Validate result
    if data['result'] not in ['Pass', 'Fail', 'Warning', 'No Entry']:
        return False, "Invalid inspection result"
    
    return True, ""

# ==================== ROUTES ====================

@app.route("/init")
def init():
    """DEV ONLY: Drops & recreates tables; seeds data."""
    try:
        init_db()
        flash('Database initialized successfully!', 'success')
        logger.info("Database reinitialized via /init endpoint")
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Init error: {e}")
        flash(f'Error initializing database: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/")
def home():
    """Display main page with search, filters, and results."""
    try:
        q = request.args.get("q", "").strip()
        result = request.args.get("result", "All")
        risk = request.args.get("risk", "All")
        page = max(1, int(request.args.get("page", 1)))
        per_page = 50
        offset = (page - 1) * per_page

        sql = """
        SELECT f.license_number, f.dba_name, f.facility_type, f.zip,
               i.inspection_id, i.inspection_date, i.result, i.risk
        FROM facilities f
        LEFT JOIN inspections i ON i.license_number = f.license_number
        WHERE 1=1
        """
        params = []

        if q:
            sql += " AND (LOWER(f.dba_name) LIKE ? OR LOWER(f.address) LIKE ?)"
            params += [f"%{q.lower()}%", f"%{q.lower()}%"]
        if result != "All":
            sql += " AND (i.result = ?)"
            params.append(result)
        if risk != "All":
            sql += " AND (i.risk = ?)"
            params.append(risk)

        sql += " ORDER BY i.inspection_date DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        conn = get_db()
        rows = conn.execute(sql, params).fetchall()
        
        # Get total count for pagination
        count_sql = """
        SELECT COUNT(DISTINCT f.license_number || '-' || COALESCE(i.inspection_id, ''))
        FROM facilities f
        LEFT JOIN inspections i ON i.license_number = f.license_number
        WHERE 1=1
        """
        count_params = []
        if q:
            count_sql += " AND (LOWER(f.dba_name) LIKE ? OR LOWER(f.address) LIKE ?)"
            count_params += [f"%{q.lower()}%", f"%{q.lower()}%"]
        if result != "All":
            count_sql += " AND (i.result = ?)"
            count_params.append(result)
        if risk != "All":
            count_sql += " AND (i.risk = ?)"
            count_params.append(risk)
        
        total = conn.execute(count_sql, count_params).fetchone()[0]
        total_pages = (total + per_page - 1) // per_page
        
        conn.close()
        
        return render_template(
            "index.html", 
            rows=rows, 
            q=q, 
            result=result, 
            risk=risk,
            page=page,
            total_pages=total_pages,
            total=total
        )
    except Exception as e:
        logger.error(f"Home route error: {e}")
        flash(f'Error loading data: {str(e)}', 'error')
        return render_template("index.html", rows=[], q="", result="All", risk="All", page=1, total_pages=1, total=0)

@app.route("/facility/<license_number>")
def facility_detail(license_number: str):
    """Display facility details and inspection history."""
    try:
        conn = get_db()
        f = conn.execute(
            "SELECT * FROM facilities WHERE license_number=?",
            (license_number,)
        ).fetchone()
        
        if not f:
            conn.close()
            flash('Facility not found', 'error')
            return redirect(url_for('home'))
        
        ins = conn.execute("""
            SELECT * FROM inspections
            WHERE license_number=?
            ORDER BY inspection_date DESC
        """, (license_number,)).fetchall()
        
        conn.close()
        return render_template("detail.html", f=f, inspections=ins)
    except Exception as e:
        logger.error(f"Facility detail error: {e}")
        flash(f'Error loading facility: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/facility/new", methods=["POST"])
def create_facility():
    """Create a new facility."""
    try:
        data = {k: request.form.get(k, "").strip() for k in
                ["license_number", "dba_name", "facility_type", "address", 
                 "city", "state", "zip", "phone"]}
        
        # Validate input
        is_valid, error_msg = validate_facility_data(data)
        if not is_valid:
            flash(f'Validation error: {error_msg}', 'error')
            return redirect(url_for('home'))
        
        conn = get_db()
        
        # Check if license already exists
        existing = conn.execute(
            "SELECT license_number FROM facilities WHERE license_number=?",
            (data["license_number"],)
        ).fetchone()
        
        if existing:
            conn.close()
            flash('License number already exists', 'error')
            return redirect(url_for('home'))
        
        conn.execute("""
            INSERT INTO facilities(license_number,dba_name,facility_type,address,city,state,zip,phone)
            VALUES(?,?,?,?,?,?,?,?)
        """, (data["license_number"], data["dba_name"], data["facility_type"], data["address"],
              data["city"], data["state"], data["zip"], data["phone"] or None))
        conn.commit()
        conn.close()
        
        logger.info(f"Created facility: {data['license_number']}")
        flash(f'Facility "{data["dba_name"]}" created successfully!', 'success')
        return redirect(url_for('facility_detail', license_number=data['license_number']))
    
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error creating facility: {e}")
        flash('Database error: Duplicate or invalid data', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error creating facility: {e}")
        flash(f'Error creating facility: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/facility/<license_number>/edit", methods=["GET", "POST"])
def edit_facility(license_number: str):
    """Edit an existing facility."""
    conn = None
    try:
        if request.method == "GET":
            conn = get_db()
            facility = conn.execute(
                "SELECT * FROM facilities WHERE license_number=?",
                (license_number,)
            ).fetchone()
            conn.close()
            
            if not facility:
                flash('Facility not found', 'error')
                return redirect(url_for('home'))
            
            return render_template("edit_facility.html", f=facility)
        
        else:  # POST
            data = {k: request.form.get(k, "").strip() for k in
                    ["dba_name", "facility_type", "address", "city", "state", "zip", "phone"]}
            
            # Validate (excluding license_number since we're editing)
            required_fields = ['dba_name', 'facility_type', 'address', 'city', 'state', 'zip']
            for field in required_fields:
                if not data.get(field):
                    flash(f'Field "{field}" is required', 'error')
                    return redirect(url_for('edit_facility', license_number=license_number))
            
            if not validate_zip(data['zip']):
                flash('Invalid ZIP code format', 'error')
                return redirect(url_for('edit_facility', license_number=license_number))
            
            if data.get('phone') and not validate_phone(data['phone']):
                flash('Invalid phone number format', 'error')
                return redirect(url_for('edit_facility', license_number=license_number))
            
            conn = get_db()
            conn.execute("""
                UPDATE facilities 
                SET dba_name=?, facility_type=?, address=?, city=?, state=?, zip=?, phone=?
                WHERE license_number=?
            """, (data["dba_name"], data["facility_type"], data["address"], data["city"],
                  data["state"], data["zip"], data["phone"] or None, license_number))
            conn.commit()
            conn.close()
            
            logger.info(f"Updated facility: {license_number}")
            flash('Facility updated successfully!', 'success')
            return redirect(url_for('facility_detail', license_number=license_number))
    
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Error editing facility: {e}")
        flash(f'Error updating facility: {str(e)}', 'error')
        return redirect(url_for('facility_detail', license_number=license_number))

@app.route("/facility/<license_number>/delete", methods=["POST"])
def delete_facility(license_number: str):
    """Delete a facility and all its inspections (CASCADE)."""
    try:
        conn = get_db()
        facility = conn.execute(
            "SELECT dba_name FROM facilities WHERE license_number=?",
            (license_number,)
        ).fetchone()
        
        if facility:
            conn.execute("DELETE FROM facilities WHERE license_number=?", (license_number,))
            conn.commit()
            logger.info(f"Deleted facility: {license_number}")
            flash(f'Facility "{facility["dba_name"]}" deleted successfully', 'success')
        else:
            flash('Facility not found', 'error')
        
        conn.close()
        return redirect(url_for('home'))
    
    except Exception as e:
        logger.error(f"Error deleting facility: {e}")
        flash(f'Error deleting facility: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/inspection/new", methods=["POST"])
def create_inspection():
    """Create a new inspection for a facility."""
    try:
        data = {k: request.form.get(k, "").strip() for k in
                ["license_number", "inspection_date", "inspection_type", "risk", "result", "violations_text"]}
        
        # Validate input
        is_valid, error_msg = validate_inspection_data(data)
        if not is_valid:
            flash(f'Validation error: {error_msg}', 'error')
            return redirect(url_for('facility_detail', license_number=data.get('license_number', '')))
        
        conn = get_db()
        conn.execute("""
            INSERT INTO inspections(license_number,inspection_date,inspection_type,risk,result,violations_text)
            VALUES(?,?,?,?,?,?)
        """, (data["license_number"], data["inspection_date"], data["inspection_type"],
              data["risk"], data["result"], data["violations_text"] or None))
        conn.commit()
        conn.close()
        
        logger.info(f"Created inspection for facility: {data['license_number']}")
        flash('Inspection added successfully!', 'success')
        return redirect(url_for('facility_detail', license_number=data["license_number"]))
    
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error creating inspection: {e}")
        flash('Error: Invalid facility license number', 'error')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error creating inspection: {e}")
        flash(f'Error creating inspection: {str(e)}', 'error')
        return redirect(url_for('facility_detail', license_number=data.get('license_number', '')))

@app.route("/inspection/<int:inspection_id>/edit", methods=["GET", "POST"])
def edit_inspection(inspection_id: int):
    """Edit an existing inspection."""
    conn = None
    try:
        if request.method == "GET":
            conn = get_db()
            inspection = conn.execute(
                "SELECT * FROM inspections WHERE inspection_id=?",
                (inspection_id,)
            ).fetchone()
            conn.close()
            
            if not inspection:
                flash('Inspection not found', 'error')
                return redirect(url_for('home'))
            
            return render_template("edit_inspection.html", inspection=inspection)
        
        else:  # POST
            data = {k: request.form.get(k, "").strip() for k in
                    ["inspection_date", "inspection_type", "risk", "result", "violations_text"]}
            
            # Validate
            if not validate_date(data['inspection_date']):
                flash('Invalid date format', 'error')
                return redirect(url_for('edit_inspection', inspection_id=inspection_id))
            
            if data['risk'] not in ['High', 'Medium', 'Low']:
                flash('Invalid risk level', 'error')
                return redirect(url_for('edit_inspection', inspection_id=inspection_id))
            
            if data['result'] not in ['Pass', 'Fail', 'Warning', 'No Entry']:
                flash('Invalid result', 'error')
                return redirect(url_for('edit_inspection', inspection_id=inspection_id))
            
            conn = get_db()
            row = conn.execute("SELECT license_number FROM inspections WHERE inspection_id=?",
                             (inspection_id,)).fetchone()
            
            if not row:
                conn.close()
                flash('Inspection not found', 'error')
                return redirect(url_for('home'))
            
            conn.execute("""
                UPDATE inspections 
                SET inspection_date=?, inspection_type=?, risk=?, result=?, violations_text=?
                WHERE inspection_id=?
            """, (data["inspection_date"], data["inspection_type"], data["risk"],
                  data["result"], data["violations_text"] or None, inspection_id))
            conn.commit()
            
            license_number = row["license_number"]
            conn.close()
            
            logger.info(f"Updated inspection: {inspection_id}")
            flash('Inspection updated successfully!', 'success')
            return redirect(url_for('facility_detail', license_number=license_number))
    
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Error editing inspection: {e}")
        flash(f'Error updating inspection: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/inspection/<int:inspection_id>/delete", methods=["POST"])
def delete_inspection(inspection_id: int):
    """Delete an inspection."""
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT license_number FROM inspections WHERE inspection_id=?",
            (inspection_id,)
        ).fetchone()
        
        if row:
            conn.execute("DELETE FROM inspections WHERE inspection_id=?", (inspection_id,))
            conn.commit()
            license_number = row["license_number"]
            conn.close()
            
            logger.info(f"Deleted inspection: {inspection_id}")
            flash('Inspection deleted successfully', 'success')
            return redirect(url_for('facility_detail', license_number=license_number))
        
        conn.close()
        flash('Inspection not found', 'error')
        return redirect(url_for('home'))
    
    except Exception as e:
        logger.error(f"Error deleting inspection: {e}")
        flash(f'Error deleting inspection: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route("/chart/monthly-fails.json")
def chart_monthly_fails():
    """API endpoint for monthly fail chart data."""
    try:
        conn = get_db()
        rows = conn.execute("""
            SELECT strftime('%Y-%m', inspection_date) AS ym,
                   SUM(CASE WHEN result='Fail' THEN 1 ELSE 0 END) AS fails,
                   COUNT(*) AS total
            FROM inspections
            WHERE inspection_date >= date('now','-6 months')
            GROUP BY ym ORDER BY ym
        """).fetchall()
        conn.close()
        
        return jsonify({
            "labels": [r["ym"] for r in rows],
            "fails":  [r["fails"] for r in rows],
            "total":  [r["total"] for r in rows]
        })
    except Exception as e:
        logger.error(f"Chart data error: {e}")
        return jsonify({"error": str(e), "labels": [], "fails": [], "total": []}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    flash('Page not found', 'error')
    return redirect(url_for('home'))

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('home'))

# ==================== APP INITIALIZATION ====================

if __name__ == "__main__":
    # Initialize database if it doesn't exist
    if not os.path.exists(DB_PATH):
        logger.info("Database not found, initializing...")
        init_db()
    
    # Run the app
    port = int(os.environ.get('PORT', 1818))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
