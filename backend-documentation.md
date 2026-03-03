# Backend Assessment Documentation

## Assessment
Backend Assessment: WorkLog Settlement System

## Implemented Endpoints
1. `POST /api/v1/generate-remittances-for-all-users`
2. `GET /api/v1/list-all-worklogs?remittanceStatus=REMITTED|UNREMITTED`

## Required Documentation

### A) DBML Diagram
Saved as: `schema.dbml`

```dbml
Table user {
  id uuid [pk]
  email varchar(255) [not null, unique]
  is_active boolean [not null]
  is_superuser boolean [not null]
  full_name varchar(255)
  hashed_password varchar [not null]
}

Table worklog {
  id uuid [pk]
  user_id uuid [not null]
  title varchar(255) [not null]
  settled_amount numeric(12,2) [not null]
  is_active boolean [not null]
  created_at timestamp [not null]
}

Table work_segment {
  id uuid [pk]
  worklog_id uuid [not null]
  minutes int [not null]
  hourly_rate numeric(12,2) [not null]
  is_active boolean [not null]
  created_at timestamp [not null]
}

Table work_adjustment {
  id uuid [pk]
  worklog_id uuid [not null]
  amount numeric(12,2) [not null]
  reason varchar(255)
  is_active boolean [not null]
  created_at timestamp [not null]
}

Table remittance {
  id uuid [pk]
  user_id uuid [not null]
  period_start date [not null]
  period_end date [not null]
  status varchar(20) [not null]
  total_amount numeric(12,2) [not null]
  failure_reason varchar(255)
  created_at timestamp [not null]
  processed_at timestamp
}

Table remittance_line {
  id uuid [pk]
  remittance_id uuid [not null]
  worklog_id uuid [not null]
  amount numeric(12,2) [not null]
  created_at timestamp [not null]
}

Ref: worklog.user_id > user.id
Ref: work_segment.worklog_id > worklog.id
Ref: work_adjustment.worklog_id > worklog.id
Ref: remittance.user_id > user.id
Ref: remittance_line.remittance_id > remittance.id
Ref: remittance_line.worklog_id > worklog.id
```

### B) Sample API Responses
Saved as: `sample-responses.json`

```json
{
  "/api/v1/list-all-worklogs?remittanceStatus=UNREMITTED": {
    "data": [
      {
        "id": "d1a538fd-2865-4177-b8ec-f98cd1159dfb",
        "user_id": "27185e5b-137f-4f2a-b86a-f93fdb4749b3",
        "title": "Landing page redesign",
        "total_amount": "350.00",
        "settled_amount": "200.00",
        "unremitted_amount": "150.00",
        "remittance_status": "UNREMITTED"
      }
    ],
    "count": 1
  },
  "/api/v1/generate-remittances-for-all-users": {
    "data": [
      {
        "id": "fbe65718-e493-4481-844e-e558fb9d6f8f",
        "user_id": "27185e5b-137f-4f2a-b86a-f93fdb4749b3",
        "status": "REMITTED",
        "total_amount": "150.00",
        "period_start": "2026-03-01",
        "period_end": "2026-03-03",
        "failure_reason": null,
        "line_items": [
          {
            "worklog_id": "d1a538fd-2865-4177-b8ec-f98cd1159dfb",
            "amount": "150.00"
          }
        ]
      }
    ],
    "count": 1
  }
}
```

## Submission Checklist
- [x] Forked the repository
- [x] Implemented both required endpoints
- [x] Added DBML diagram of your database schema
- [x] Added JSON file with sample responses from both endpoints
- [x] Created Pull Request
