-- Appointments table migration
-- Run this script if the database already exists

-- Enable vector extension if not exists
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create appointments table
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES call_logs(id) ON DELETE SET NULL,
    agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    customer_address TEXT,
    appointment_type VARCHAR(50) DEFAULT 'consultation',
    appointment_date TIMESTAMP NOT NULL,
    appointment_time VARCHAR(20),
    duration_minutes INTEGER DEFAULT 60,
    status VARCHAR(50) DEFAULT 'confirmed',
    notes TEXT,
    location VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_agent ON appointments(agent_id);
CREATE INDEX IF NOT EXISTS idx_appointments_campaign ON appointments(campaign_id);

-- Verify
DO $$
BEGIN
    RAISE NOTICE 'Appointments table created successfully!';
END $$;
