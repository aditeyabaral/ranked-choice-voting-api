CREATE TABLE IF NOT EXISTS ELECTION(
    election_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR NOT NULL,
    election_name VARCHAR,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    description VARCHAR,
    anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    candidates VARCHAR NOT NULL,
    votes VARCHAR,
    round_number INTEGER,
    winner VARCHAR
);