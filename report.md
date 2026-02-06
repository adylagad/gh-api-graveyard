# API Endpoint Usage Analysis: demo-service
**Generated:** 2026-02-06 02:56:22 UTC
**Total Endpoints:** 8
**Unused Endpoints:** 3
**High Confidence Unused (≥80):** 4

## Endpoint Analysis

| Confidence | Method | Path | Calls | Last Seen | Callers | Reasons |
|------------|--------|------|-------|-----------|---------|----------|
| 100 | DELETE | /users/{id} | 0 | Never | 0 | Never called in logs |
| 100 | GET | /posts | 0 | Never | 0 | Never called in logs |
| 100 | GET | /posts/{id} | 1 | 2025-08-15 | 1 | Called only once; Last seen 174 days ago (>3 months); Sin... |
| 100 | GET | /admin/settings | 0 | Never | 0 | Never called in logs |
| 70 | GET | /users | 2 | 2026-02-05 | 1 | Very low call count (2 calls); Recently active (0 days ag... |
| 70 | GET | /health | 3 | 2026-02-05 | 1 | Very low call count (3 calls); Recently active (0 days ag... |
| 65 | POST | /users | 2 | 2026-02-05 | 2 | Very low call count (2 calls); Recently active (0 days ag... |
| 65 | GET | /users/{id} | 3 | 2026-02-05 | 2 | Very low call count (3 calls); Recently active (0 days ag... |

## Confidence Score Legend

- **100**: Never called in logs
- **80-99**: Very likely unused (low calls, old, few callers)
- **60-79**: Possibly unused (some usage but limited)
- **40-59**: Moderate usage
- **0-39**: Actively used
