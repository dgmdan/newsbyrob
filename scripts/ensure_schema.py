import os
import sys

from psycopg import connect, sql


def _default_schema(environment: str) -> str:
    return 'newsbyrob' if environment == 'production' else 'public'


def main() -> int:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return 0

    environment = os.environ.get('DJANGO_ENV', 'development').strip().lower()
    schema = os.environ.get('DATABASE_SCHEMA') or _default_schema(environment)
    if schema.lower() == 'public':
        return 0

    try:
        with connect(database_url, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL('CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION CURRENT_USER').format(
                        sql.Identifier(schema)
                    )
                )
                cursor.execute(
                    sql.SQL('GRANT USAGE ON SCHEMA {} TO CURRENT_USER').format(sql.Identifier(schema))
                )
                cursor.execute(
                    sql.SQL('GRANT CREATE ON SCHEMA {} TO CURRENT_USER').format(sql.Identifier(schema))
                )
    except Exception as exc:  # pragma: no cover - best effort helper
        print(f'Unable to ensure schema "{schema}": {exc}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
