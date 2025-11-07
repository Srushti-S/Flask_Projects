# 🍽️ Chicago Food Facility Inspections Database

<div align="center">

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.3-green.svg)
![SQLite](https://img.shields.io/badge/sqlite-3-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**A comprehensive CRUD web application for managing and analyzing Chicago Department of Public Health (CDPH) food facility inspection records.**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [Documentation](#-documentation) • [Team](#-team)

</div>

---

## 📖 About

This web application provides an intuitive interface for browsing, searching, and managing food facility inspection data from Chicago. It demonstrates full-stack development with real-world data integration.

## 🛠️ Technology Stack

### Backend
- **Flask 3.0.3** - Web framework
- **SQLite 3** - Database (production: PostgreSQL ready)
- **Python 3.11+** - Programming language

### Frontend
- **Pico CSS 2.0** - Modern CSS framework
- **Chart.js** - Data visualization
- **Vanilla JavaScript** - Client-side interactions

### Data Source
- **Chicago Data Portal** - Official CDPH inspection records
- **Real-time Updates** - Latest data from data.cityofchicago.org

---

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/chicago-food-inspections.git
cd chicago-food-inspections
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database

```bash
# Option 1: Run app (auto-creates database with seed data)
python app.py

# Option 2: Manual initialization
python -c "from app import init_db; init_db()"
```

### Step 5: Run Application

```bash
python app.py
```

Visit **http://localhost:1818** in your browser.

---

## 🚀 Quick Start

### Using Demo Data (Fastest)

```bash
# 1. Install and run
pip install -r requirements.txt
python app.py

# 2. Visit http://localhost:1818/init
# This seeds 3 sample facilities and 4 inspections

# 3. Start exploring!
```

### Using Real Chicago Data (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run data import script
python import_chicago_data.py

# 3. Choose option 1 (Download data)
# 4. Choose option 2 (Import 1000 records) - takes ~10 seconds

# 5. Start the app
python app.py

# 6. Visit http://localhost:5000
```

You'll now have **real Chicago restaurants** with actual inspection data!

---

## 📚 Usage

### Browsing Inspections

1. **Home Page** - View all inspections in a paginated table
2. **Search** - Enter facility name or address
3. **Filter** - Select result (Pass/Fail/Warning) and risk level
4. **Click Facility** - View detailed inspection history

### Creating Records

#### Add a Facility
1. Scroll to "Add New Facility" form on home page
2. Fill required fields:
   - License Number (e.g., `LIC-1234`)
   - DBA Name (business name)
   - Facility Type (e.g., `Restaurant`)
   - Address, City, State, ZIP
   - Phone (optional)
3. Click "Create Facility"

#### Add an Inspection
1. Navigate to facility detail page
2. Use "Add New Inspection" form
3. Fill fields:
   - Inspection Date
   - Inspection Type (Routine/Complaint/Follow-up)
   - Risk Level (High/Medium/Low)
   - Result (Pass/Fail/Warning/No Entry)
   - Violations (optional)
4. Click "Create Inspection"

### Editing Records

1. Click **Edit** button on facility detail page
2. Modify fields as needed
3. Click **Save Changes**

### Deleting Records

1. Click **Delete** button with confirmation
2. **Facilities** - Deletes facility + all inspections (CASCADE)
3. **Inspections** - Deletes single inspection only

---

## 📥 Importing Real Chicago Data

### Data Source

- **URL**: https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5
- **Size**: 250,000+ inspection records
- **Coverage**: 2010 - Present
- **License**: Open Government License (Public Domain)

### What Gets Imported

- **~300-400 facilities** (restaurants, grocery stores, bakeries, etc.)
- **~1000 inspection records** with real dates and violations
- **Real Chicago businesses** - McDonald's, Starbucks, Subway, local restaurants
- **Actual violations** - Real health code violation descriptions

---

## 📁 Project Structure

```
chicago-food-inspections/
├── app.py                      # Main Flask application
├── config.py                   # Environment configuration
├── schema.sql                  # Database schema and seed data
├── import_chicago_data.py      # Data import script
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
│
├── static/
│   ├── styles.css              # Main stylesheet
│   └── theme.js                # Theme toggle script
│
├── templates/
    ├── index.html              # Home page
    ├── detail.html             # Facility detail page
    ├── edit_facility.html      # Facility edit form
    └── edit_inspection.html    # Inspection edit form
```
