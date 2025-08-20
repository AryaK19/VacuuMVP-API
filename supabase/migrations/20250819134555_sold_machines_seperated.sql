-- 1. SOLD_MACHINES TABLE: Add columns as nullable first
ALTER TABLE sold_machines
    ADD COLUMN IF NOT EXISTS serial_no VARCHAR(255),
    ADD COLUMN IF NOT EXISTS customer_company VARCHAR(255),
    ADD COLUMN IF NOT EXISTS date_of_manufacturing DATE;

-- 2. Migrate data from machines to sold_machines
UPDATE sold_machines sm
SET serial_no = m.serial_no,
    date_of_manufacturing = m.date_of_manufacturing
FROM machines m
WHERE sm.machine_id = m.id;

-- 3. MACHINES TABLE: Remove serial_no and date_of_manufacturing
ALTER TABLE machines
    DROP COLUMN IF EXISTS serial_no,
    DROP COLUMN IF EXISTS date_of_manufacturing;

-- 4. Now set serial_no as NOT NULL and UNIQUE
ALTER TABLE sold_machines
    ALTER COLUMN serial_no SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sold_machines_serial_no ON sold_machines(serial_no);
CREATE INDEX IF NOT EXISTS idx_sold_machines_customer_company ON sold_machines(customer_company);
CREATE INDEX IF NOT EXISTS idx_sold_machines_date_of_manufacturing ON sold_machines(date_of_manufacturing);

-- 5. SERVICE_REPORT TABLE: Remove machine_id, add sold_machine_id
-- Drop foreign key and column for machine_id
ALTER TABLE service_report
    DROP CONSTRAINT IF EXISTS service_report_machine_id_fkey,
    DROP COLUMN IF EXISTS machine_id;

-- Add sold_machine_id (FK to sold_machines)
ALTER TABLE service_report
    ADD COLUMN IF NOT EXISTS sold_machine_id UUID REFERENCES sold_machines(id);

CREATE INDEX IF NOT EXISTS idx_service_report_sold_machine_id ON service_report(sold_machine_id);

-- End of migration