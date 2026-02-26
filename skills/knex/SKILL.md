---
name: knex
description: Use when setting up Knex configuration, installing Knex/drivers, customizing connection behavior (pooling, dynamic connections, hooks), or interpreting Knex-generated SQL for queries and schema across different SQL dialects.
---

# knex

Knex.js is a Node.js SQL query builder that supports configuring connections, running migrations, building schema, and generating SQL across multiple database clients.

## When to Use

- You need to initialize Knex for a specific database client (pg/mysql/sqlite3/better-sqlite3/mssql) with correct connection options
- You need to install Knex and the appropriate database driver packages
- You need to configure migrations (e.g., migrations table name)
- You need dynamic connections (function/async connection) or custom per-instance parameters (userParams/withUserParams)
- You need to understand dialect differences in generated SQL (e.g., returning(), joins, CTEs, union all, except, count)
- You need to configure debugging/async stack traces or post-process query results

## Reference

Read the relevant doc based on your task:

- **Installation (Knex core + DB drivers + CLI)** — `docs/installation.md` — Commands to install Knex and the required database drivers, plus the migration CLI.
- **Initialize Knex and Configure Clients** — `docs/initialization-and-clients.md` — Initialize Knex with different clients and configure common connection options (versions, connection strings, SSL, custom clients).
- **Advanced Configuration (migrations, pool, dynamic connections, user params, hooks, debugging)** — `docs/advanced-configuration.md` — Configure migrations, pooling, dynamic connections, user parameters, response hooks, and debugging options.
- **Query Builder SQL Examples (dialect output)** — `docs/query-builder-sql-examples.md` — Reference SQL output examples for common Knex query-builder features like returning, joins, CTEs, unions, except, count, and where raw.
- **Schema Builder SQL Examples (tables, columns, constraints)** — `docs/schema-builder-sql-examples.md` — Reference SQL output examples for schema builder features like timestamps, nullability, unsigned integers, adding columns, foreign keys, and unique constraints/indexes.
- **Troubleshooting and Gotchas** — `docs/troubleshooting.md` — Common Knex setup pitfalls and debugging tactics shown in the docs.

## Key Patterns

- Client selection affects SQL output: the same query builder can render different SQL depending on { client: 'pg' | 'mysql' | ... } (e.g., .returning('*') differs by dialect).
- Driver installation is required separately: installing `knex` is not enough; you must install the database-specific driver package (pg/mysql/sqlite3/etc.).
- Connection can be static or dynamic: `connection` may be an object, a function returning an object, or an async function returning config (e.g., vault-based config with expirationChecker).
- Custom instance metadata via userParams: pass arbitrary `userParams` in config or clone an instance with `withUserParams()` and access via `knex.userParams`.
- Debugging aids are opt-in: enable `debug: true` for query debugging and `asyncStackTraces: true` for better async error context; use postProcessResponse to transform results.
