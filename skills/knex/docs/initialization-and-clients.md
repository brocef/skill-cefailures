## Initialize Knex with Different Clients

```javascript
const pg = require('knex')({ client: 'pg' });

knex('table').insert({ a: 'b' }).returning('*').toString();
// "insert into "table" ("a") values ('b')"

pg('table').insert({ a: 'b' }).returning('*').toString();
// "insert into "table" ("a") values ('b') returning *"
```

## Configure MySQL Connection with Knex.js

```javascript
const knex = require('knex')({
  client: 'mysql',
  connection: {
    host: '127.0.0.1',
    port: 3306,
    user: 'your_database_user',
    password: 'your_database_password',
    database: 'myapp_test',
  },
});
```

## Configure MySQL Connection with Version

```javascript
const knex = require('knex')({
  client: 'mysql',
  version: '5.7',
  connection: {
    host: '127.0.0.1',
    port: 3306,
    user: 'your_database_user',
    password: 'your_database_password',
    database: 'myapp_test',
  },
});
```

## Configure PostgreSQL Connection with Knex.js

```javascript
const pg = require('knex')({
  client: 'pg',
  connection: process.env.PG_CONNECTION_STRING,
  searchPath: ['knex', 'public'],
});
```

## Configure PostgreSQL Connection with Version

```javascript
const knex = require('knex')({
  client: 'pg',
  version: '7.2',
  connection: {
    host: '127.0.0.1',
    port: 5432,
    user: 'your_database_user',
    password: 'your_database_password',
    database: 'myapp_test',
  },
});
```

## Configure PostgreSQL with Connection String and SSL using Knex.js

Prioritizes `connectionString` if provided.

```javascript
const pg = require('knex')({
  client: 'pg',
  connection: {
    connectionString: config.DATABASE_URL,
    host: config['DB_HOST'],
    port: config['DB_PORT'],
    user: config['DB_USER'],
    database: config['DB_NAME'],
    password: config['DB_PASSWORD'],
    ssl: config['DB_SSL'] ? { rejectUnauthorized: false } : false,
  },
});
```

## Configure SQLite3 File Connection with Knex.js

```javascript
const knex = require('knex')({
  client: 'sqlite3', // or 'better-sqlite3'
  connection: {
    filename: './mydb.sqlite',
  },
});
```

## Configure Better-SQLite3 in Read-Only Mode using Knex.js

```javascript
const knex = require('knex')({
  client: 'better-sqlite3',
  connection: {
    filename: '/path/to/db.sqlite3',
    options: {
      readonly: true,
    },
  },
});
```

## Configure Better-SQLite3 with Native Binding Path using Knex.js

```javascript
const knex = require('knex')({
  client: 'better-sqlite3',
  connection: {
    filename: ':memory:',
    options: {
      nativeBinding: '/path/to/better_sqlite3.node',
    },
  },
});
```

## Configure Aurora PostgreSQL with JSONB Support

```javascript
const knex = require('knex')({
  client: require('knex-aurora-data-api-client').postgres,
  connection: { resourceArn, secretArn, database: `mydb` },
  version: 'data-api',
  jsonbSupport: true,
});
```

## Configure MSSQL with Custom Binding Mapping using Knex.js

```javascript
import { TYPES } from 'tedious';

const knex = require('knex')({
  client: 'mssql',
  connection: {
    options: {
      mapBinding: (value) => {
        // bind all strings to varchar instead of nvarchar
        if (typeof value === 'string') {
          return {
            type: TYPES.VarChar,
            value,
          };
        }

        // allow devs to pass tedious type at query time
        if (value != null && value.type) {
          return {
            type: value.type,
            value: value.value,
          };
        }

        // undefined is returned; falling back to default mapping function
      },
    },
  },
});
```
