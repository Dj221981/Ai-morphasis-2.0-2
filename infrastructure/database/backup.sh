#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL must be set}"
pg_dump "$DATABASE_URL" > "backup-$(date +%Y%m%d%H%M%S).sql"
