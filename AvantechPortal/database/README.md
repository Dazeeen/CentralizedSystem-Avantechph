# Database Storage Convention

Database-related files are stored using this structure:

./database/<dbname>/filename.file

Example for SQLite:

./database/avantech/db.sqlite3

## Environment Variables

Set these in `.env` to switch database backends:

- `DJANGO_DB_ENGINE=sqlite3|mysql|mariadb|postgres|postgresql`
- `DJANGO_DB_NAME=<database_name>`
- `DJANGO_DB_FILE=<sqlite_filename>` (SQLite only, default: `db.sqlite3`)
- `DJANGO_DB_USER=<db_user>`
- `DJANGO_DB_PASSWORD=<db_password>`
- `DJANGO_DB_HOST=<db_host>`
- `DJANGO_DB_PORT=<db_port>`
- `DJANGO_DB_CONN_MAX_AGE=<seconds>`
- `DJANGO_DB_CONNECT_TIMEOUT=<seconds>`
