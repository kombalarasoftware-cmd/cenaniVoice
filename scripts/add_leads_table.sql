-- Lead Capture System Migration
-- Run this SQL to add leads table and call_logs tags field

-- Add tags column to call_logs if not exists
ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]';

-- Create leads table
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES call_logs(id) ON DELETE SET NULL,
    agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Customer info
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    customer_address TEXT,
    
    -- Lead details
    interest_type VARCHAR(50) NOT NULL DEFAULT 'callback',
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    customer_statement TEXT,
    notes TEXT,
    priority INTEGER DEFAULT 1,
    source VARCHAR(100),
    
    -- Follow-up tracking
    last_contacted_at TIMESTAMP,
    next_follow_up TIMESTAMP,
    follow_up_count INTEGER DEFAULT 0,
    converted_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_interest_type ON leads(interest_type);
CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);
CREATE INDEX IF NOT EXISTS idx_leads_agent_id ON leads(agent_id);
CREATE INDEX IF NOT EXISTS idx_leads_campaign_id ON leads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_customer_phone ON leads(customer_phone);

-- Comments
COMMENT ON TABLE leads IS 'Potansiyel müşteriler - AI aramalarından yakalanan lead bilgileri';
COMMENT ON COLUMN leads.interest_type IS 'callback, address_collection, purchase_intent, demo_request, quote_request, subscription, information, other';
COMMENT ON COLUMN leads.status IS 'new, contacted, qualified, converted, lost';
COMMENT ON COLUMN leads.priority IS '1=low, 2=medium, 3=high';
