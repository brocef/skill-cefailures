## Timestamps Table Creation SQL Examples

```sql
create table "timestamps_example" ("created_at" timestamptz not null default CURRENT_TIMESTAMP, "updated_at" timestamptz not null default CURRENT_TIMESTAMP)
```

```sql
CREATE TABLE [timestamps_example] ([created_at] datetime2 not null CONSTRAINT [timestamps_example_created_at_default] DEFAULT CURRENT_TIMESTAMP, [updated_at] datetime2 not null CONSTRAINT [timestamps_example_updated_at_default] DEFAULT CURRENT_TIMESTAMP)
```

```sql
create table `timestamps_example` (`created_at` timestamp not null default CURRENT_TIMESTAMP, `updated_at` timestamp not null default CURRENT_TIMESTAMP)
```

```sql
create table "timestamps_example" ("created_at" timestamp with local time zone default CURRENT_TIMESTAMP not null, "updated_at" timestamp with local time zone default CURRENT_TIMESTAMP not null)
```

```sql
create table `timestamps_example` (`created_at` datetime not null default CURRENT_TIMESTAMP, `updated_at` datetime not null default CURRENT_TIMESTAMP)
```

## SQL Examples for Nullable Column

```sql
create table "nullable_example" ("nickname" varchar(255) null)
```

```sql
CREATE TABLE [nullable_example] ([nickname] nvarchar(255) null)
```

```sql
create table `nullable_example` (`nickname` varchar(255) null)
```

```sql
create table "nullable_example" ("nickname" varchar2(255) null)
```

## SQL Examples for Not Nullable Column

```sql
create table "not_nullable_example" ("email" varchar(255) not null)
```

```sql
CREATE TABLE [not_nullable_example] ([email] nvarchar(255) not null)
```

```sql
create table `not_nullable_example` (`email` varchar(255) not null)
```

```sql
create table "not_nullable_example" ("email" varchar2(255) not null)
```

## SQL Examples for Unsigned Integer

```sql
create table "unsigned_example" ("age" integer unsigned)
```

```sql
create table `unsigned_example` (`age` int unsigned)
```

## SQL Examples for Adding a Column

```sql
alter table "users" add column "nickname" varchar(255)
```

```sql
ALTER TABLE [users] ADD [nickname] nvarchar(255)
```

```sql
alter table `users` add `nickname` varchar(255) first
```

```sql
alter table "users" add "nickname" varchar2(255)
```

```sql
alter table `users` add column `nickname` varchar(255)
```

## SQL Examples for Adding a Not Nullable Column

```sql
alter table "users" add column "nickname" varchar(255)
```

```sql
ALTER TABLE [users] ADD [nickname] nvarchar(255)
```

```sql
alter table `users` add `nickname` varchar(255) after `email`
```

```sql
alter table "users" add "nickname" varchar2(255)
```

```sql
alter table `users` add column `nickname` varchar(255)
```

## SQL Examples for Creating Tables with Foreign Keys

```sql
create table "references_example" ("company_id" integer)

alter table "references_example" add constraint "references_example_company_id_foreign" foreign key ("company_id") references "company" ("companyId")
```

```sql
CREATE TABLE [references_example] ([company_id] int, CONSTRAINT [references_example_company_id_foreign] FOREIGN KEY ([company_id]) REFERENCES [company] ([companyId]))
```

```sql
create table `references_example` (`company_id` int)

alter table `references_example` add constraint `references_example_company_id_foreign` foreign key (`company_id`) references `company` (`companyId`)
```

```sql
create table `references_example` (`company_id` integer, foreign key(`company_id`) references `company`(`companyId`))
```

## SQL Examples for Creating Tables with Primary Keys (shown with foreign key constraint)

```sql
create table "in_table_example" ("company_id" integer)

alter table "in_table_example" add constraint "in_table_example_company_id_foreign" foreign key ("company_id") references "company" ("companyId")
```

```sql
CREATE TABLE [in_table_example] ([company_id] int, CONSTRAINT [in_table_example_company_id_foreign] FOREIGN KEY ([company_id]) REFERENCES [company] ([companyId]))
```

```sql
create table `in_table_example` (`company_id` int)

alter table `in_table_example` add constraint `in_table_example_company_id_foreign` foreign key (`company_id`) references `company` (`companyId`)
```

```sql
create table `in_table_example` (`company_id` integer, foreign key(`company_id`) references `company`(`companyId`))
```

## SQL Examples for Adding Unique Constraints and Indexes

```sql
alter table "users" add constraint "users_email_unique" unique ("email")

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id") deferrable initially deferred

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id")

-- ----

create unique index "job_composite_index" on "job" ("account_id", "program_id") where "account_id" is not null
```

```sql
CREATE UNIQUE INDEX [users_email_unique] ON [users] ([email]) WHERE [email] IS NOT NULL

-- ----

CREATE UNIQUE INDEX [job_composite_index] ON [job] ([account_id], [program_id]) WHERE [account_id] IS NOT NULL AND [program_id] IS NOT NULL

-- ----

ALTER TABLE [job] ADD CONSTRAINT [job_composite_index] UNIQUE ([account_id], [program_id])

-- ----

CREATE UNIQUE INDEX [job_composite_index] ON [job] ([account_id], [program_id]) where [account_id] is not null
```

```sql
alter table `users` add unique `users_email_unique`(`email`)

-- ----

alter table `job` add unique `job_composite_index`(`account_id`, `program_id`) using hash

-- ----

alter table `job` add unique `job_composite_index`(`account_id`, `program_id`)

-- ----

alter table `job` add unique `job_composite_index`(`account_id`, `program_id`)
```

```sql
alter table "users" add constraint "users_email_unique" unique ("email")

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id") deferrable initially deferred

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id")

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id")
```

```sql
alter table "users" add constraint "users_email_unique" unique ("email")

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id") deferrable initially deferred

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id")

-- ----

create unique index "job_composite_index" on "job" ("account_id", "program_id") where "account_id" is not null
```

```sql
alter table "users" add constraint "users_email_unique" unique ("email")

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id") deferrable initially deferred

-- ----

alter table "job" add constraint "job_composite_index" unique ("account_id", "program_id")

-- ----

create unique index "job_composite_index" on "job" ("account_id", "program_id") where "account_id" is not null
```

```sql
create unique index `users_email_unique` on `users` (`email`)

-- ----

create unique index `job_composite_index` on `job` (`account_id`, `program_id`)

-- ----

create unique index `job_composite_index` on `job` (`account_id`, `program_id`)

-- ----

create unique index `job_composite_index` on `job` (`account_id`, `program_id`) where `account_id` is not null
```
