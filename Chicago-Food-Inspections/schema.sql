-- Database: Food Facility Inspections (SQLite)

PRAGMA foreign_keys = ON;

-- Recreate (dev only)
DROP TABLE IF EXISTS violations;
DROP TABLE IF EXISTS inspections;
DROP TABLE IF EXISTS facilities;

-- Entities -------------------------------------------------------------------
CREATE TABLE facilities (
  license_number TEXT PRIMARY KEY,         -- natural key
  dba_name       TEXT NOT NULL,
  facility_type  TEXT NOT NULL,
  address        TEXT NOT NULL,
  city           TEXT NOT NULL DEFAULT 'Chicago',
  state          TEXT NOT NULL DEFAULT 'IL',
  zip            TEXT NOT NULL CHECK (length(zip) BETWEEN 5 AND 10),
  phone          TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE inspections (
  inspection_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  license_number   TEXT NOT NULL,
  inspection_date  TEXT NOT NULL,     -- YYYY-MM-DD
  inspection_type  TEXT NOT NULL CHECK (length(inspection_type) > 0),
  risk             TEXT NOT NULL CHECK (risk IN ('High','Medium','Low')),
  result           TEXT NOT NULL CHECK (result IN ('Pass','Fail','Warning','No Entry')),
  violations_text  TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (license_number) REFERENCES facilities(license_number) ON DELETE CASCADE
);

CREATE TABLE violations (
  violation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  inspection_id  INTEGER NOT NULL,
  code           TEXT,
  description    TEXT NOT NULL,
  critical       INTEGER NOT NULL CHECK (critical IN (0,1)) DEFAULT 0,
  FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE CASCADE
);

-- Indexes --------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_facilities_name ON facilities (dba_name);
CREATE INDEX IF NOT EXISTS idx_inspections_license_date ON inspections (license_number, inspection_date);
CREATE INDEX IF NOT EXISTS idx_inspections_result ON inspections (result);

-- Triggers -------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_facilities_updated_at
AFTER UPDATE ON facilities
FOR EACH ROW BEGIN
  UPDATE facilities SET updated_at = datetime('now') WHERE license_number = NEW.license_number;
END;

CREATE TRIGGER IF NOT EXISTS trg_inspections_updated_at
AFTER UPDATE ON inspections
FOR EACH ROW BEGIN
  UPDATE inspections SET updated_at = datetime('now') WHERE inspection_id = NEW.inspection_id;
END;

-- Seed data ------------------------------------------------------------------
INSERT INTO facilities (license_number,dba_name,facility_type,address,city,state,zip,phone) VALUES
('LIC-1001','Sunrise Diner','Restaurant','101 Main St','Chicago','IL','60601','312-555-0101'),
('LIC-1002','Lotus Express','Restaurant','55 W Lake St','Chicago','IL','60602','312-555-0102'),
('LIC-1003','Green Grocer','Grocery Store','200 Oak Ave','Chicago','IL','60610','312-555-0103');

INSERT INTO inspections (license_number,inspection_date,inspection_type,risk,result,violations_text) VALUES
('LIC-1001', DATE('now','-15 days'),'Routine','High','Fail','#21: Inadequate cooling; #6: Hand washing sinks blocked'),
('LIC-1001', DATE('now','-40 days'),'Follow-up','Medium','Pass',NULL),
('LIC-1002', DATE('now','-70 days'),'Complaint','High','Warning','#3: Food not protected; #7: Improper hot holding'),
('LIC-1003', DATE('now','-90 days'),'Routine','Low','Pass',NULL);

INSERT INTO violations (inspection_id,code,description,critical) VALUES
(1,'#21','Inadequate cooling of TCS foods',1),
(1,'#6','Hand washing sinks blocked',1),
(3,'#3','Food not protected from contamination',1);
