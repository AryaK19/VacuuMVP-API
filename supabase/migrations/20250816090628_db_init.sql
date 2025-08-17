-- Create role table
CREATE TABLE role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create type table
CREATE TABLE type (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create service_types table
CREATE TABLE service_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create machines table (updated with reduced fields)
CREATE TABLE machines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_no VARCHAR(100) NOT NULL UNIQUE,
    model_no VARCHAR(255) NOT NULL,
    date_of_manufacturing DATE,
    part_no VARCHAR(100),
    type_id UUID REFERENCES type(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create sold_machines table
CREATE TABLE sold_machines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id UUID REFERENCES machines(id),
    customer_name VARCHAR(255),
    customer_contact VARCHAR(50),
    customer_email VARCHAR(255),
    customer_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table (fixed the multiple PRIMARY KEY issue)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE, -- Supabase user auth id
    role_id UUID REFERENCES role(id),
    name VARCHAR(255),
    phone_number VARCHAR(50),
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create service_report table
CREATE TABLE service_report (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    machines_id UUID REFERENCES machines(id),
    problem TEXT,
    solution TEXT,
    service_person_name VARCHAR(255),
    service_type_id UUID REFERENCES service_types(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create service_report_parts table
CREATE TABLE service_report_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_report_id UUID REFERENCES service_report(id),
    machine_id UUID REFERENCES machines(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create files table
CREATE TABLE service_report_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_report_id UUID REFERENCES service_report(id),
    file_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_service_report_user_id ON service_report(user_id);
CREATE INDEX idx_service_report_sold_machines_id ON service_report(sold_machines_id);
CREATE INDEX idx_service_report_service_type_id ON service_report(service_type_id);
CREATE INDEX idx_machines_type_id ON machines(type_id);
CREATE INDEX idx_service_report_parts_machine_id ON service_report_parts(machine_id);
CREATE INDEX idx_service_report_files_service_report_id ON service_report_files(service_report_id);
CREATE INDEX idx_sold_machines_machine_id ON sold_machines(machine_id);


INSERT INTO role (role_name) VALUES
    ('admin'),
    ('distributer');

INSERT INTO type (type) VALUES
    ('pump'),
    ('part');

INSERT INTO service_types (service_type) VALUES
    ('Paid'),
    ('Health Check'),
    ('Warranty'),
    ('AMC');
