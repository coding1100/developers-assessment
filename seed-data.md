# Local DB Seeding Guide

This guide shows how to seed local test data for the backend assessment without changing startup scripts.

## Prerequisites

1. Run the stack:

```bash
docker compose up
```

2. Make sure the target user exists.

Default user from this template is usually `admin@example.com`.

## Seed Data (PowerShell)

Replace `YOUR_EMAIL_HERE` with an email that exists in your local DB.

```powershell
@'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

WITH u AS (
  SELECT id FROM "user" WHERE email='YOUR_EMAIL_HERE' LIMIT 1
), wl1 AS (
  INSERT INTO worklog (id, user_id, title, settled_amount, is_active, created_at)
  SELECT gen_random_uuid(), u.id, 'Seed WL-1', 0.00, true, now()
  FROM u
  RETURNING id
), wl2 AS (
  INSERT INTO worklog (id, user_id, title, settled_amount, is_active, created_at)
  SELECT gen_random_uuid(), u.id, 'Seed WL-2', 0.00, true, now()
  FROM u
  RETURNING id
)
INSERT INTO work_segment (id, worklog_id, minutes, hourly_rate, is_active, created_at)
SELECT gen_random_uuid(), wl1.id, 180, 40.00, true, now() FROM wl1
UNION ALL
SELECT gen_random_uuid(), wl2.id, 75, 60.00, true, now() FROM wl2;

WITH wl AS (
  SELECT id
  FROM worklog
  WHERE user_id = (SELECT id FROM "user" WHERE email='YOUR_EMAIL_HERE' LIMIT 1)
    AND title = 'Seed WL-1'
  ORDER BY created_at DESC
  LIMIT 1
)
INSERT INTO work_adjustment (id, worklog_id, amount, reason, is_active, created_at)
SELECT gen_random_uuid(), wl.id, -20.00, 'Retro quality deduction', true, now()
FROM wl;
'@ | docker compose exec -T db psql -U postgres -d app
```

## Seed Data (Bash)

Replace `YOUR_EMAIL_HERE` with an email that exists in your local DB.

```bash
docker compose exec -T db psql -U postgres -d app <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

WITH u AS (
  SELECT id FROM "user" WHERE email='YOUR_EMAIL_HERE' LIMIT 1
), wl1 AS (
  INSERT INTO worklog (id, user_id, title, settled_amount, is_active, created_at)
  SELECT gen_random_uuid(), u.id, 'Seed WL-1', 0.00, true, now()
  FROM u
  RETURNING id
), wl2 AS (
  INSERT INTO worklog (id, user_id, title, settled_amount, is_active, created_at)
  SELECT gen_random_uuid(), u.id, 'Seed WL-2', 0.00, true, now()
  FROM u
  RETURNING id
)
INSERT INTO work_segment (id, worklog_id, minutes, hourly_rate, is_active, created_at)
SELECT gen_random_uuid(), wl1.id, 180, 40.00, true, now() FROM wl1
UNION ALL
SELECT gen_random_uuid(), wl2.id, 75, 60.00, true, now() FROM wl2;

WITH wl AS (
  SELECT id
  FROM worklog
  WHERE user_id = (SELECT id FROM "user" WHERE email='YOUR_EMAIL_HERE' LIMIT 1)
    AND title = 'Seed WL-1'
  ORDER BY created_at DESC
  LIMIT 1
)
INSERT INTO work_adjustment (id, worklog_id, amount, reason, is_active, created_at)
SELECT gen_random_uuid(), wl.id, -20.00, 'Retro quality deduction', true, now()
FROM wl;
SQL
```

## Verify Seeded Data

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/list-all-worklogs?remittanceStatus=UNREMITTED" | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/generate-remittances-for-all-users" | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/v1/list-all-worklogs?remittanceStatus=REMITTED" | ConvertTo-Json -Depth 8
```

## Optional Reset

```bash
docker compose exec db psql -U postgres -d app -c "TRUNCATE TABLE remittance_line, remittance, work_adjustment, work_segment, worklog;"
```
