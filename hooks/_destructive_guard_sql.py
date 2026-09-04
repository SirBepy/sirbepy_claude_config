"""SQL statement matching (todo 911 split): DROP/TRUNCATE/DELETE-no-WHERE,
each gated on a same-statement execution-context signal since SQL verbs
never sit at command position (see the module docstring on the entry file
for why anchoring can't discriminate them).
"""

import re

from _destructive_guard_shared import LEADING_ENV_RE, LEADING_SUDO_RE, split_statements

# SQL verbs are matched anywhere in a statement, never at command position, so
# a statement whose own command only EMITS or SEARCHES text is prose, not SQL:
# `git commit -m "REFACTOR: python helper, drop table alias"` was DENIED before
# this exclusion, because `python` satisfied the SQL-context rule.
TEXT_EMITTER_RE = re.compile(
    r"^(git|gh|echo|printf|cat|grep|rg|sed|awk|head|tail|less|more|type|write-host|write-output)\b",
    re.IGNORECASE,
)

SQL_DROP_RE = re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE)
SQL_TRUNCATE_RE = re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE)
DELETE_FROM_RE = re.compile(r"\bDELETE\s+FROM\s+[A-Za-z_\"`\[]", re.IGNORECASE)
WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)
# SQL verbs never sit at command position, so anchoring cannot discriminate
# them: require a real client/migration binary or a driver CALL shape in the
# same statement. A bare `-c` flag or the word `python` is NOT enough - that
# denied a `python -c` call whose only SQL was prose in a -Note argument.
SQL_CONTEXT_RE = re.compile(
    r"\b(psql|mysql|mariadb|sqlite3|sqlcmd|mongo|mongosh|clickhouse|cockroach|duckdb"
    r"|alembic|prisma|sequelize|knex|flyway|liquibase)\b"
    r"|\b(execute|executemany|execute_batch|text|query|raw)\s*\(",
    re.IGNORECASE,
)


def statement_is_prose(statement: str) -> bool:
    """True when the statement's own command position only emits or searches
    text, so SQL words inside it are a message rather than a query.
    """
    s = statement.strip()
    while True:
        m = LEADING_SUDO_RE.match(s) or LEADING_ENV_RE.match(s)
        if not m:
            break
        s = s[m.end():]
    return bool(TEXT_EMITTER_RE.match(s))


def match_sql_drop(command: str):
    for stmt in split_statements(command):
        if SQL_DROP_RE.search(stmt) and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt):
            return "DROP TABLE/DATABASE/SCHEMA is unrecoverable without a separate backup"
    return None


def match_sql_truncate(command: str):
    for stmt in split_statements(command):
        if SQL_TRUNCATE_RE.search(stmt) and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt):
            return "TRUNCATE TABLE is unrecoverable without a separate backup"
    return None


def match_sql_delete_no_where(command: str):
    for stmt in split_statements(command):
        if (DELETE_FROM_RE.search(stmt) and not WHERE_RE.search(stmt)
                and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt)):
            return "DELETE FROM with no WHERE in this statement deletes every row"
    return None
