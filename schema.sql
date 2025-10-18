-- ============================================================================
-- FRAUD DETECTION DEMO - DATABASE SCHEMA
-- Event Sourced Architecture with Read Models
-- ============================================================================

-- ============================================================================
-- EVENT STORE (Append-Only Log)
-- ============================================================================

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,  -- UUID of the entity (transaction, account, etc.)
    aggregate_type TEXT NOT NULL,  -- 'Transaction', 'Account', 'Session', etc.
    event_data TEXT NOT NULL,  -- JSON blob with event-specific data
    metadata TEXT NOT NULL,  -- JSON: {user_id, ip_address, device_id, location, etc.}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INTEGER NOT NULL,  -- For optimistic locking
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);

-- ============================================================================
-- READ MODELS (Projections from Events)
-- ============================================================================

-- Accounts (Current State)
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    status TEXT DEFAULT 'active',  -- active, suspended, closed
    total_transactions INTEGER DEFAULT 0,
    total_volume REAL DEFAULT 0.0,
    fraud_flags INTEGER DEFAULT 0,
    last_login DATETIME,
    last_transaction DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_email ON accounts(user_email);
CREATE INDEX idx_accounts_status ON accounts(status);

-- Transactions (Current State)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    merchant_category TEXT,
    merchant_name TEXT,
    status TEXT NOT NULL,  -- initiated, completed, failed, flagged
    initiated_at DATETIME NOT NULL,
    completed_at DATETIME,
    failed_at DATETIME,
    latitude REAL,
    longitude REAL,
    device_id TEXT,
    ip_address TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_initiated ON transactions(initiated_at);
CREATE INDEX idx_transactions_amount ON transactions(amount);

-- Fraud Scores (ML-Generated)
CREATE TABLE IF NOT EXISTS fraud_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL UNIQUE,
    fraud_probability REAL NOT NULL,  -- 0.0 to 1.0
    is_fraud BOOLEAN,  -- Final classification
    model_version TEXT NOT NULL,
    features TEXT,  -- JSON blob of features used
    flagged_reasons TEXT,  -- JSON array of detected patterns
    scored_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

CREATE INDEX idx_fraud_scores_transaction ON fraud_scores(transaction_id);
CREATE INDEX idx_fraud_scores_probability ON fraud_scores(fraud_probability);
CREATE INDEX idx_fraud_scores_is_fraud ON fraud_scores(is_fraud);

-- User Behavioral Profiles (Aggregated Patterns)
CREATE TABLE IF NOT EXISTS user_profiles (
    account_id TEXT PRIMARY KEY,
    avg_transaction_amount REAL,
    median_transaction_amount REAL,
    std_transaction_amount REAL,
    typical_merchant_categories TEXT,  -- JSON array
    typical_transaction_hours TEXT,  -- JSON array [0-23]
    home_latitude REAL,
    home_longitude REAL,
    typical_radius_km REAL,  -- Usual geographic range
    max_velocity_kmh REAL,  -- Maximum plausible velocity
    known_devices TEXT,  -- JSON array of device_ids
    risk_score REAL DEFAULT 0.0,  -- 0.0 (low) to 1.0 (high)
    profile_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_user_profiles_risk ON user_profiles(risk_score);

-- Device Fingerprints
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    first_seen DATETIME NOT NULL,
    last_seen DATETIME NOT NULL,
    device_type TEXT,  -- mobile, desktop, tablet
    browser TEXT,
    os TEXT,
    is_trusted BOOLEAN DEFAULT 0,
    fraud_incidents INTEGER DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_devices_account ON devices(account_id);
CREATE INDEX idx_devices_trusted ON devices(is_trusted);

-- Login Attempts (for velocity/brute-force detection)
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    attempted_at DATETIME NOT NULL,
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    device_id TEXT,
    latitude REAL,
    longitude REAL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_login_attempts_account ON login_attempts(account_id);
CREATE INDEX idx_login_attempts_time ON login_attempts(attempted_at);

-- Location History (for geographic impossibility detection)
CREATE TABLE IF NOT EXISTS location_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    event_type TEXT NOT NULL,  -- transaction, login
    event_id TEXT,  -- Reference to transaction_id or login attempt id
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE INDEX idx_location_events_account ON location_events(account_id, timestamp);
CREATE INDEX idx_location_events_time ON location_events(timestamp);

-- ============================================================================
-- METADATA / SYSTEM TABLES
-- ============================================================================

-- Projections State (Track which events have been processed)
CREATE TABLE IF NOT EXISTS projection_state (
    projection_name TEXT PRIMARY KEY,
    last_event_id INTEGER NOT NULL,
    last_processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Model Metadata
CREATE TABLE IF NOT EXISTS ml_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT NOT NULL UNIQUE,
    algorithm TEXT NOT NULL,
    training_date DATETIME NOT NULL,
    accuracy REAL,
    precision REAL,
    recall REAL,
    f1_score REAL,
    feature_list TEXT,  -- JSON array
    hyperparameters TEXT,  -- JSON object
    is_active BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
