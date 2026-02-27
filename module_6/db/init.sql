-- Initialize the applicants table and ingestion_watermarks table
CREATE TABLE IF NOT EXISTS applicants (
    p_id SERIAL PRIMARY KEY,
    program TEXT,
    university TEXT,
    degree TEXT,
    status TEXT,
    term TEXT,
    us_or_international TEXT,
    comments TEXT,
    decision_date TEXT,
    date_added DATE,
    url TEXT,
    gpa FLOAT,
    gre FLOAT,
    gre_v FLOAT,
    gre_aw FLOAT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);

ALTER TABLE applicants ADD CONSTRAINT applicants_url_unique UNIQUE (url);

CREATE TABLE IF NOT EXISTS ingestion_watermarks (
    source TEXT PRIMARY KEY,
    last_seen TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Materialized view for analytics summary
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_summary AS
SELECT
    COUNT(*) AS total_records,
    COUNT(*) FILTER (WHERE term = 'Fall 2026') AS fall_2026_count,
    ROUND(
        (COUNT(*) FILTER (WHERE us_or_international NOT IN ('American', 'Other')) * 100.0)
        / NULLIF(COUNT(*), 0), 2
    ) AS international_pct,
    ROUND(AVG(gpa)::numeric, 2) AS avg_gpa,
    ROUND(AVG(gre)::numeric, 2) AS avg_gre,
    ROUND(AVG(gre_v)::numeric, 2) AS avg_gre_v,
    ROUND(AVG(gre_aw)::numeric, 2) AS avg_gre_aw,
    ROUND(
        AVG(gpa) FILTER (WHERE us_or_international = 'American' AND term = 'Fall 2026')::numeric, 2
    ) AS avg_gpa_american_f26,
    ROUND(
        (COUNT(*) FILTER (WHERE status ILIKE '%Accepted%' AND term = 'Fall 2026') * 100.0)
        / NULLIF(COUNT(*) FILTER (WHERE term = 'Fall 2026'), 0), 2
    ) AS acceptance_rate_f26,
    ROUND(
        AVG(gpa) FILTER (WHERE term = 'Fall 2026' AND status ILIKE '%Accepted%')::numeric, 2
    ) AS avg_gpa_accepted_f26,
    COUNT(*) FILTER (
        WHERE (university ILIKE '%Johns Hopkins%' OR university ILIKE '%JHU%')
        AND degree ILIKE '%Masters%'
        AND (program ILIKE '%Computer Science%' OR llm_generated_program ILIKE '%Computer Science%')
    ) AS jhu_ms_cs_count,
    COUNT(*) FILTER (
        WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%'
        AND degree ILIKE '%PhD%'
        AND (university ILIKE '%Georgetown%' OR university ILIKE '%MIT%'
             OR university ILIKE '%Stanford%' OR university ILIKE '%Carnegie Mellon%')
        AND program ILIKE '%Computer Science%'
    ) AS phd_cs_target_standard,
    COUNT(*) FILTER (
        WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%'
        AND degree ILIKE '%PhD%'
        AND llm_generated_university IN (
            'Georgetown University', 'Massachusetts Institute of Technology',
            'Stanford University', 'Carnegie Mellon University'
        )
        AND llm_generated_program ILIKE '%Computer Science%'
    ) AS phd_cs_target_llm
FROM applicants;
