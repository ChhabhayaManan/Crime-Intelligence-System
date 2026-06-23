-- Check actual DB name first — SELECT datname FROM pg_database;
-- PostgreSQL lowercases everything — CrimeDB → crimedb, personID → personid
-- Exception: if you quoted the name on creation (e.g. CREATE DATABASE "CrimeDB"), case is preserved — but that creates more headaches than it solves, so just use lowercase consistently.

CREATE TABLE Address (
    address_id      INT PRIMARY KEY NOT NULL,
    street_address  VARCHAR(255),
    city            VARCHAR(100),
    state           VARCHAR(100),
    postal_code     VARCHAR(20),
    country         VARCHAR(100)
);

CREATE TABLE Person (
    personID        INT PRIMARY KEY NOT NULL,
    gender          VARCHAR(1),
    birth_date      DATE,
    first_name      VARCHAR(100),
    middle_name     VARCHAR(100),
    last_name       VARCHAR(100),
    address_id      INT,
    occupation      VARCHAR(100),
    contact_number  VARCHAR(15),
    FOREIGN KEY (address_id) REFERENCES Address(address_id)
);

CREATE TABLE Case_Details (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    crime_date      DATE,
    end_date        DATE,
    complaint_detail VARCHAR(255),
    crime_type      VARCHAR(50),
    crime_location  INT,
    case_status     VARCHAR(10),
    personID        INT,
    PRIMARY KEY (case_id, open_date),
    FOREIGN KEY (personID) REFERENCES Person(personID),
    FOREIGN KEY (crime_location) REFERENCES Address(address_id)
);

CREATE TABLE Trial (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    trial_number    INT NOT NULL,
    hearing         DATE,
    judge_id        INT,
    court_level     VARCHAR(50),
    PRIMARY KEY (case_id, open_date, trial_number),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date)
);

CREATE TABLE Police_Officer (
    p_personID      INT PRIMARY KEY NOT NULL,
    rank            VARCHAR(50),
    department      VARCHAR(100),
    FOREIGN KEY (p_personID) REFERENCES Person(personID)
);

CREATE TABLE Criminal (
    c_personID      INT PRIMARY KEY NOT NULL,
    c_family_contact VARCHAR(15),
    FOREIGN KEY (c_personID) REFERENCES Person(personID)
);

CREATE TABLE Suspect (
    s_personID          INT PRIMARY KEY NOT NULL,
    physical_description VARCHAR(255),
    family_contact      VARCHAR(15),
    arrest_status       VARCHAR(50),
    FOREIGN KEY (s_personID) REFERENCES Person(personID)
);

CREATE TABLE Victim (
    v_personID      INT PRIMARY KEY NOT NULL,
    harm_details    VARCHAR(255),
    family_contact  VARCHAR(15),
    FOREIGN KEY (v_personID) REFERENCES Person(personID)
);

CREATE TABLE Witness (
    w_personID      INT PRIMARY KEY NOT NULL,
    family_contact  VARCHAR(15),
    testimony       VARCHAR(255),
    FOREIGN KEY (w_personID) REFERENCES Person(personID)
);

CREATE TABLE Evidence (
    evidence_id       INT PRIMARY KEY NOT NULL,
    description       VARCHAR(255),
    collection_date   DATE,
    file_key          VARCHAR,
    file_content_type VARCHAR,
    file_size         INTEGER
);

ALTER TABLE Evidence
    ADD location_id INT;

CREATE TABLE Collected_For (
    evidence_id     INT NOT NULL,
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    PRIMARY KEY (evidence_id, case_id, open_date),
    FOREIGN KEY (evidence_id) REFERENCES Evidence(evidence_id),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date)
);

CREATE TABLE Testifies_In (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    w_personID      INT NOT NULL,
    PRIMARY KEY (case_id, open_date, w_personID),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date),
    FOREIGN KEY (w_personID) REFERENCES Witness(w_personID)
);

CREATE TABLE Assigned_To (
    p_personID      INT NOT NULL,
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    PRIMARY KEY (p_personID, case_id, open_date),
    FOREIGN KEY (p_personID) REFERENCES Police_Officer(p_personID),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date)
);

CREATE TABLE Affected_By (
    v_personID      INT NOT NULL,
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    PRIMARY KEY (v_personID, case_id, open_date),
    FOREIGN KEY (v_personID) REFERENCES Victim(v_personID),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date)
);

CREATE TABLE Punishment (
    c_personID      INT NOT NULL,
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    fine            INT,
    jail_start_date DATE,
    jail_end_date   DATE,
    death_penalty   VARCHAR(1),
    PRIMARY KEY (c_personID, case_id, open_date),
    FOREIGN KEY (c_personID) REFERENCES Criminal(c_personID),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date)
);

CREATE TABLE Involved_In (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    s_personID      INT NOT NULL,
    PRIMARY KEY (case_id, open_date, s_personID),
    FOREIGN KEY (case_id, open_date) REFERENCES Case_Details(case_id, open_date),
    FOREIGN KEY (s_personID) REFERENCES Suspect(s_personID)
);

CREATE TABLE Linked_to (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    s_personID      INT NOT NULL,
    evidence_id     INT NOT NULL,
    PRIMARY KEY (case_id, open_date, s_personID, evidence_id),
    FOREIGN KEY (case_id, open_date, evidence_id) REFERENCES Collected_For(case_id, open_date, evidence_id),
    FOREIGN KEY (s_personID) REFERENCES Suspect(s_personID)
);

CREATE TABLE Pointed_to (
    case_id         INT NOT NULL,
    open_date       DATE NOT NULL,
    s_personID      INT NOT NULL,
    w_personID      INT NOT NULL,
    PRIMARY KEY (case_id, open_date, s_personID, w_personID),
    FOREIGN KEY (case_id, open_date, w_personID) REFERENCES Testifies_In(case_id, open_date, w_personID),
    FOREIGN KEY (s_personID) REFERENCES Suspect(s_personID)
);
-- Authentication table for users
CREATE TABLE App_User (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,                  -- bcrypt hash, never plaintext
    role            VARCHAR(50) NOT NULL DEFAULT 'viewer'
                        CHECK (role IN ('admin', 'officer', 'analyst', 'viewer')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    mobile_number   VARCHAR(15)
);

