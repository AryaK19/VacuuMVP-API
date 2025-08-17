-- Update service_report table: change machine_id to sold_machines_id (already done in previous migration)
-- This appears to already be updated in the current schema

-- Add quantity field to service_report_parts table
ALTER TABLE service_report_parts 
ADD COLUMN quantity INTEGER DEFAULT 1;

-- Add file_key field to machines table
ALTER TABLE machines 
ADD COLUMN file_key VARCHAR(255);

-- Add user_id field to sold_machines table
ALTER TABLE sold_machines 
ADD COLUMN user_id UUID REFERENCES users(id);

-- Create index for the new user_id field in sold_machines
CREATE INDEX idx_sold_machines_user_id ON sold_machines(user_id);

-- Update service_report table to reference machines directly instead of sold_machines
-- First, add the machine_id column back
ALTER TABLE service_report 
ADD COLUMN machine_id UUID REFERENCES machines(id);

-- Create index for machine_id in service_report
CREATE INDEX idx_service_report_machine_id ON service_report(machine_id);

-- Note: You may want to migrate existing data from sold_machines_id to machine_id
-- This would require a data migration script based on your business logic

-- Optional: If you want to remove sold_machines_id from service_report after migration
-- ALTER TABLE service_report DROP COLUMN sold_machines_id;
-- DROP INDEX idx_service_report_sold_machines_id;
