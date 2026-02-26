## Knex installed but connection fails

Knex requires a database-specific driver to be installed separately. Ensure you installed the correct driver package for your DB:

```bash
npm install pg
$ npm install pg-native
$ npm install sqlite3
$ npm install better-sqlite3
$ npm install mysql
$ npm install mysql2
$ npm install oracledb
$ npm install tedious
```

## SQL differs across dialects (especially `.returning()`)

The same query can render different SQL depending on the configured `client`. Example from the docs:

```javascript
const pg = require('knex')({ client: 'pg' });

knex('table').insert({ a: 'b' }).returning('*').toString();
// "insert into "table" ("a") values ('b')"

pg('table').insert({ a: 'b' }).returning('*').toString();
// "insert into "table" ("a") values ('b') returning *"
```

## Need more context for async errors

Enable async stack traces:

```javascript
const knex = require('knex')({
  client: 'pg',
  connection: {
    // ... connection details
  },
  asyncStackTraces: true,
});
```

## Need to see queries during development

Enable debug mode:

```javascript
const knex = require('knex')({
  client: 'pg',
  connection: {
    // ... connection details
  },
  debug: true,
});
```

## postProcessResponse can mishandle raw results

The docs note a TODO about raw results being dialect-dependent:

```javascript
postProcessResponse: (result, queryContext) => {
  // TODO: add special case for raw results
  // (depends on dialect)
  if (Array.isArray(result)) {
    return result.map((row) => convertToCamel(row));
  } else {
    return convertToCamel(result);
  }
},
```

## Dynamic connections need correct return shape

If you use a function/async function for `connection`, it must return a configuration object (and can include an `expirationChecker` as shown):

```javascript
const knex = require('knex')({
  client: 'postgres',
  connection: async () => {
    const cfg = await fetchConfigFromVault(); // returns { settings, expiresAt }
    return {
      ...cfg.settings,
      expirationChecker: () => Date.now() > cfg.expiresAt,
    };
  },
});
```
