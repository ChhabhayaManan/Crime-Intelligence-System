SET SEARCH_PATH TO crimetrack;
-- 1.	Age group wise criminal list
SELECT 
    age_group,
    COUNT(*) AS criminal_count
FROM (
    SELECT 
        CASE 
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.birth_date)) < 18 THEN 'Under 18'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.birth_date)) BETWEEN 18 AND 24 THEN '18-24'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.birth_date)) BETWEEN 25 AND 34 THEN '25-34'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.birth_date)) BETWEEN 35 AND 44 THEN '35-44'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.birth_date)) BETWEEN 45 AND 54 THEN '45-54'
            ELSE '55+'
        END AS age_group
    FROM 
        Person p
    JOIN 
        Criminal c ON p.personID = c.c_personID
) AS age_data
GROUP BY 
    age_group
ORDER BY 
    age_group;

-- 2. A person who has been a witness for more than 3 years. With the past experience of being a victim in the same type of case.    
SELECT 
    p.personID,
    CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) AS full_name,
    MAX(cd_witness.open_date) AS latest_witness_date,
    MIN(cd_witness.open_date) AS first_witness_date,
    cd_victim.crime_type AS victim_crime_type,
    cd_witness.crime_type AS witness_crime_type
FROM 
    Person p
JOIN Victim v ON p.personID = v.v_personID
JOIN Witness w ON p.personID = w.w_personID
JOIN Affected_By ab ON v.v_personID = ab.v_personID
JOIN Case_Details cd_victim 
    ON ab.case_id = cd_victim.case_id AND ab.open_date = cd_victim.open_date
JOIN Testifies_In ti ON w.w_personID = ti.w_personID
JOIN Case_Details cd_witness 
    ON ti.case_id = cd_witness.case_id AND ti.open_date = cd_witness.open_date
WHERE 
    cd_victim.crime_type = cd_witness.crime_type
    AND EXISTS (
        SELECT 1
        FROM Testifies_In ti2
        JOIN Case_Details cd2 
            ON ti2.case_id = cd2.case_id AND ti2.open_date = cd2.open_date
        WHERE ti2.w_personID = w.w_personID
        GROUP BY ti2.w_personID
        HAVING CURRENT_DATE - MIN(cd2.open_date) > 1095  -- over 3 years
    )
GROUP BY 
    p.personID, full_name, cd_victim.crime_type, cd_witness.crime_type
HAVING 
    COUNT(DISTINCT cd_witness.case_id) >= 1;


-- 3. Count the number of cases by month and year
SELECT 
    EXTRACT(YEAR FROM open_date) AS year,
    EXTRACT(MONTH FROM open_date) AS month,
    COUNT(*) AS case_count
FROM Case_Details
GROUP BY year, month
ORDER BY year, month;

-- 4. Most active police officers (by case assignments)
SELECT po.p_personID, 
       CONCAT(p.first_name, ' ', p.middle_name, ' ', p.last_name) AS full_name, 
       po.rank, 
       COUNT(at.case_id) AS case_count
FROM Police_Officer po
JOIN Person p ON po.p_personID = p.personID
JOIN Assigned_To at ON po.p_personID = at.p_personID
GROUP BY po.p_personID, p.first_name, p.middle_name, p.last_name, po.rank
ORDER BY case_count DESC
LIMIT 5;

-- 5. Persons who were criminals and now not in jail and not dead
SELECT 
    p.personID,
    p.first_name,
    p.middle_name,
    p.last_name
FROM Criminal c
JOIN Punishment pu ON c.c_personID = pu.c_personID
JOIN Person p ON c.c_personID = p.personID
WHERE 
    (pu.jail_end_date IS NOT NULL AND pu.jail_end_date < CURRENT_DATE)
    AND (pu.death_penalty IS NULL OR LOWER(pu.death_penalty) = 'n');


-- 6. List cases with multiple suspects
SELECT cd.case_id, cd.crime_type, COUNT(ii.s_personID) AS suspect_count
FROM Case_Details cd
JOIN Involved_In ii ON cd.case_id = ii.case_id AND cd.open_date = ii.open_date
GROUP BY cd.case_id, cd.crime_type
HAVING COUNT(ii.s_personID) > 1
ORDER BY suspect_count DESC;


-- 7. Calculate the average duration of closed cases (output -> days)
SELECT AVG(end_date - open_date) AS avg_duration_days
FROM Case_Details
WHERE end_date IS NOT NULL;

-- 8. List criminals with multiple punishments
SELECT c.c_personID, 
       CONCAT(p.first_name, ' ', p.middle_name, ' ', p.last_name) AS full_name, 
       COUNT(pu.case_id) AS punishment_count
FROM Criminal c
JOIN Person p ON c.c_personID = p.personID
JOIN Punishment pu ON c.c_personID = pu.c_personID
GROUP BY c.c_personID, p.first_name, p.middle_name, p.last_name
HAVING COUNT(pu.case_id) > 1
ORDER BY punishment_count DESC;

-- 9. Find cases with the most evidence collected
SELECT cd.case_id, cd.crime_type, COUNT(cf.evidence_id) AS evidence_count
FROM Case_Details cd
JOIN Collected_For cf ON cd.case_id = cf.case_id AND cd.open_date = cf.open_date
GROUP BY cd.case_id, cd.crime_type
ORDER BY evidence_count DESC
LIMIT 5;

-- 10. Delete evidence records older than 10 years
DELETE FROM Evidence
WHERE evidence_id IN (
    SELECT e.evidence_id
    FROM Evidence e
    WHERE 3650 < CURRENT_DATE -  e.collection_date
);

-- 11. Find upcoming trials (hearings in the future)
SELECT t.case_id, t.trial_number, t.hearing, t.court_level, cd.crime_type
FROM Trial t
JOIN Case_Details cd ON t.case_id = cd.case_id AND t.open_date = cd.open_date
WHERE t.hearing > CURRENT_DATE
ORDER BY t.hearing;

-- 12. Officer case closure rates
SELECT po.p_personID, 
       CONCAT(p.first_name, ' ', p.middle_name, ' ', p.last_name) AS full_name,
       COUNT(CASE WHEN cd.case_status = 'Closed' THEN 1 END) AS closed_cases,
       COUNT(*) AS total_cases,
       ROUND(COUNT(CASE WHEN cd.case_status = 'Closed' THEN 1 END) * 100.0 / COUNT(*), 2) AS closure_rate
FROM Police_Officer po
JOIN Person p ON po.p_personID = p.personID
JOIN Assigned_To at ON po.p_personID = at.p_personID
JOIN Case_Details cd ON at.case_id = cd.case_id AND at.open_date = cd.open_date
GROUP BY po.p_personID, p.first_name, p.middle_name, p.last_name
HAVING COUNT(*) > 5
ORDER BY closure_rate DESC;


-- 13. Find cases with the longest duration (still open or recently closed)
SELECT case_id, crime_type, open_date, end_date, 
       COALESCE(end_date - open_date, CURRENT_DATE - open_date) AS duration_days
FROM Case_Details
ORDER BY duration_days DESC
LIMIT 10;

-- 14. Total Collected Fine
SELECT SUM(fine) AS total_collected_fine
FROM Punishment;


