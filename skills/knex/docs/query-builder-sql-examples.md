## SQL Examples for .returning() Method

```sql
insert into "books" ("title") values (?) returning "id"

-- ----

insert into "books" ("title") values (?), (?) returning "id"

-- ----

insert into "books" ("title") values (?) returning "id", "title"
```

```sql
insert into [books] ([title]) output inserted.[id] values (?)

-- ----

insert into [books] ([title]) output inserted.[id] values (?), (?)

-- ----

insert into [books] ([title]) output inserted.[id], inserted.[title] values (?)
```

```sql
insert into `books` (`title`) values (?)

-- ----

insert into `books` (`title`) values (?), (?)

-- ----

insert into `books` (`title`) values (?)
```

```sql
insert into "books" ("title") values (?) returning "id" into ?

-- ----

begin execute immediate 'insert into "books" ("title") values (:1) returning "id" into :2' using ?, out ?; execute immediate 'insert into "books" ("title") values (:1) returning "id" into :2' using ?, out ?;end;

-- ----

insert into "books" ("title") values (?) returning "id","title" into ?,?
```

```sql
insert into "books" ("title") values (?) returning "id"

-- ----

insert into "books" ("title") values (?), (?) returning "id"

-- ----

insert into "books" ("title") values (?) returning "id", "title"
```

```sql
insert into "books" ("title") values (?)

-- ----

insert into "books" ("title") values (?), (?)

-- ----

insert into "books" ("title") values (?)
```

```sql
insert into `books` (`title`) values (?) returning `id`

-- ----

insert into `books` (`title`) select ? as `title` union all select ? as `title` returning `id`

-- ----

insert into `books` (`title`) values (?) returning `id`, `title`
```

## SQL Left Join Examples (Standard, SQL Server, MySQL)

```sql
select * from "users" left join "accounts" on "users"."id" = "accounts"."user_id"

-- ----

select * from "users" left join "accounts" on "accounts"."id" = "users"."account_id" or "accounts"."owner_id" = "users"."id"
```

```sql
select * from [users] left join [accounts] on [users].[id] = [accounts].[user_id]

-- ----

select * from [users] left join [accounts] on [accounts].[id] = [users].[account_id] or [accounts].[owner_id] = [users].[id]
```

```sql
select * from `users` left join `accounts` on `users`.`id` = `accounts`.`user_id`

-- ----

select * from `users` left join `accounts` on `accounts`.`id` = `users`.`account_id` or `accounts`.`owner_id` = `users`.`id`
```

## SQL Right Join Examples (Standard, SQL Server, MySQL)

```sql
select * from "users" right join "accounts" on "users"."id" = "accounts"."user_id"

-- ----

select * from "users" right join "accounts" on "accounts"."id" = "users"."account_id" or "accounts"."owner_id" = "users"."id"
```

```sql
select * from [users] right join [accounts] on [users].[id] = [accounts].[user_id]

-- ----

select * from [users] right join [accounts] on [accounts].[id] = [users].[account_id] or [accounts].[owner_id] = [users].[id]
```

```sql
select * from `users` right join `accounts` on `users`.`id` = `accounts`.`user_id`

-- ----

select * from `users` right join `accounts` on `accounts`.`id` = `users`.`account_id` or `accounts`.`owner_id` = `users`.`id`
```

## SQL fullOuterJoin Examples (Standard, SQL Server, MySQL)

```sql
select * from "users" full outer join "accounts" on "users"."id" = "accounts"."user_id"

-- ----

select * from "users" full outer join "accounts" on "accounts"."id" = "users"."account_id" or "accounts"."owner_id" = "users"."id"
```

```sql
select * from [users] full outer join [accounts] on [users].[id] = [accounts].[user_id]

-- ----

select * from [users] full outer join [accounts] on [accounts].[id] = [users].[account_id] or [accounts].[owner_id] = [users].[id]
```

```sql
select * from `users` full outer join `accounts` on `users`.`id` = `accounts`.`user_id`

-- ----

select * from `users` full outer join `accounts` on `accounts`.`id` = `users`.`account_id` or `accounts`.`owner_id` = `users`.`id`
```

## SQL WITH Clause Examples

```sql
with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias"("title") as (select "title" from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"
```

```sql
with [with_alias] as (select * from "books" where "author" = ?) select * from [with_alias]

-- ----

with [with_alias]([title]) as (select "title" from "books" where "author" = ?) select * from [with_alias]

-- ----

with [with_alias] as (select * from [books] where [author] = ?) select * from [with_alias]
```

```sql
with `with_alias` as (select * from "books" where "author" = ?) select * from `with_alias`

-- ----

with `with_alias`(`title`) as (select "title" from "books" where "author" = ?) select * from `with_alias`

-- ----

with `with_alias` as (select * from `books` where `author` = ?) select * from `with_alias`
```

```sql
with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias"("title") as (select "title" from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"
```

```sql
with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias"("title") as (select "title" from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"
```

```sql
with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias"("title") as (select "title" from "books" where "author" = ?) select * from "with_alias"

-- ----

with "with_alias" as (select * from "books" where "author" = ?) select * from "with_alias"
```

```sql
with `with_alias` as (select * from "books" where "author" = ?) select * from `with_alias`

-- ----

with `with_alias`(`title`) as (select "title" from "books" where "author" = ?) select * from `with_alias`

-- ----

with `with_alias` as (select * from `books` where `author` = ?) select * from `with_alias`
```

## Recursive CTEs - SQL Examples

```sql
with recursive "ancestors" as (select "people".* from "people" where "people"."id" = ? union all select "people".* from "people" inner join "ancestors" on "ancestors"."parentId" = "people"."id") select * from "ancestors"

-- ----

with recursive "family"("name", "parentName") as (select "name", "parentName" from "folks" where "name" = ? union all select "folks"."name", "folks"."parentName" from "folks" inner join "family" on "family"."parentName" = "folks"."name") select "name" from "family"
```

```sql
with [ancestors] as (select [people].* from [people] where [people].[id] = ? union all select [people].* from [people] inner join [ancestors] on [ancestors].[parentId] = [people].[id]) select * from [ancestors]

-- ----

with [family]([name], [parentName]) as (select [name], [parentName] from [folks] where [name] = ? union all select [folks].[name], [folks].[parentName] from [folks] inner join [family] on [family].[parentName] = [folks].[name]) select [name] from [family]
```

```sql
with recursive `ancestors` as (select `people`.* from `people` where `people`.`id` = ? union all select `people`.* from `people` inner join `ancestors` on `ancestors`.`parentId` = `people`.`id`) select * from `ancestors`

-- ----

with recursive `family`(`name`, `parentName`) as (select `name`, `parentName` from `folks` where `name` = ? union all select `folks`.`name`, `folks`.`parentName` from `folks` inner join `family` on `family`.`parentName` = `folks`.`name`) select `name` from `family`
```

```sql
with "ancestors" as (select "people".* from "people" where "people"."id" = ? union all select "people".* from "people" inner join "ancestors" on "ancestors"."parentId" = "people"."id") select * from "ancestors"

-- ----

with "family"("name", "parentName") as (select "name", "parentName" from "folks" where "name" = ? union all select "folks"."name", "folks"."parentName" from "folks" inner join "family" on "family"."parentName" = "folks"."name") select "name" from "family"
```

```sql
with recursive "ancestors" as (select "people".* from "people" where "people"."id" = ? union all select "people".* from "people" inner join "ancestors" on "ancestors"."parentId" = "people"."id") select * from "ancestors"

-- ----

with recursive "family"("name", "parentName") as (select "name", "parentName" from "folks" where "name" = ? union all select "folks"."name", "folks"."parentName" from "folks" inner join "family" on "family"."parentName" = "folks"."name") select "name" from "family"
```

```sql
with recursive `ancestors` as (select `people`.* from `people` where `people`.`id` = ? union all select `people`.* from `people` inner join `ancestors` on `ancestors`.`parentId` = `people`.`id`) select * from `ancestors`

-- ----

with recursive `family`(`name`, `parentName`) as (select `name`, `parentName` from `folks` where `name` = ? union all select `folks`.`name`, `folks`.`parentName` from `folks` inner join `family` on `family`.`parentName` = `folks`.`name`) select `name` from `family`
```

## SQL UNION ALL Examples

```sql
select * from "users" where "last_name" is null union all select * from "users" where "first_name" is null

```

```sql
select * from "users" where "last_name" is null union all select * from "users" where "first_name" is null

```

```sql
select * from "users" where "last_name" is null union all select * from users where first_name is null union all select * from users where email is null

```

```sql
select * from "users" where "last_name" is null union all select * from "users" where "first_name" is null

```

```sql
select * from "users" where "last_name" is null union all select * from "users" where "first_name" is null

```

```sql
select * from "users" where "last_name" is null union all select * from users where first_name is null union all select * from users where email is null

```

```sql
select * from `users` where `last_name` is null union all select * from `users` where `first_name` is null

```

```sql
select * from `users` where `last_name` is null union all select * from `users` where `first_name` is null

```

```sql
select * from `users` where `last_name` is null union all select * from users where first_name is null union all select * from users where email is null

```

## SQL EXCEPT Query Examples (SQL Server Syntax)

```sql
select * from [users] where [last_name] is null except select * from [users] where [first_name] is null

-- ----

select * from [users] where [last_name] is null except select * from [users] where [first_name] is null

-- ----

select * from [users] where [last_name] is null except select * from users where first_name is null except select * from users where email is null
```

## SQL Count Aggregation Examples

```sql
select count("active") from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a", count("valid") as "v" from "users"

-- ----

select count("id") from "users"

-- ----

select count("id", "active") as "count" from "users"

-- ----

select count("active") from "users"
```

```sql
select count([active]) from [users]

-- ----

select count([active]) as [a] from [users]

-- ----

select count([active]) as [a] from [users]

-- ----

select count([active]) as [a] from [users]

-- ----

select count([active]) as [a], count([valid]) as [v] from [users]

-- ----

select count([id]) from [users]

-- ----

select count([id], [active]) as [count] from [users]

-- ----

select count([active]) from [users]
```

```sql
select count(`active`) from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a`, count(`valid`) as `v` from `users`

-- ----

select count(`id`) from `users`

-- ----

select count(`id`, `active`) as `count` from `users`

-- ----

select count(`active`) from `users`
```

```sql
select count("active") from "users"

-- ----

select count("active") "a" from "users"

-- ----

select count("active") "a" from "users"

-- ----

select count("active") "a" from "users"

-- ----

select count("active") "a", count("valid") "v" from "users"

-- ----

select count("id") from "users"

-- ----

select count("id", "active") "count" from "users"

-- ----

select count("active") from "users"
```

```sql
select count("active") from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a", count("valid") as "v" from "users"

-- ----

select count("id") from "users"

-- ----

select count("id", "active") as "count" from "users"

-- ----

select count("active") from "users"
```

```sql
select count("active") from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a" from "users"

-- ----

select count("active") as "a", count("valid") as "v" from "users"

-- ----

select count("id") from "users"

-- ----

select count("id", "active") as "count" from "users"

-- ----

select count("active") from "users"
```

```sql
select count(`active`) from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a` from `users`

-- ----

select count(`active`) as `a`, count(`valid`) as `v` from `users`

-- ----

select count(`id`) from `users`

-- ----

select count(`id`, `active`) as `count` from `users`

-- ----

select count(`active`) from `users`
```

## SQL SELECT Statements for Knex.js Examples

```sql
select "id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "id" as "identifier" from "users"

-- ----

select "id" as "identifier" from "users"
```

```sql
select [id] from [users]

-- ----

select [users].[id] from [users]

-- ----

select [users].[id] from [users]

-- ----

select [id] as [identifier] from [users]

-- ----

select [id] as [identifier] from [users]
```

```sql
select `id` from `users`

-- ----

select `users`.`id` from `users`

-- ----

select `users`.`id` from `users`

-- ----

select `id` as `identifier` from `users`

-- ----

select `id` as `identifier` from `users`
```

```sql
select "id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "id" "identifier" from "users"

-- ----

select "id" as "identifier" from "users"
```

```sql
select "id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "id" as "identifier" from "users"

-- ----

select "id" as "identifier" from "users"
```

```sql
select "id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "users"."id" from "users"

-- ----

select "id" as "identifier" from "users"

-- ----

select "id" as "identifier" from "users"
```

```sql
select `id` from `users`

-- ----

select `users`.`id` from `users`

-- ----

select `users`.`id` from `users`

-- ----

select `id` as `identifier` from `users`

-- ----

select `id` as `identifier` from `users`
```

## SQL: WHERE RAW clause examples

```sql
select * from "users" where id = ?
```

```sql
select * from [users] where id = ?
```

```sql
select * from `users` where id = ?
```

```sql
select * from "users" where id = ?
```

```sql
select * from "users" where id = ?
```

```sql
select * from "users" where id = ?
```

```sql
select * from `users` where id = ?
```
