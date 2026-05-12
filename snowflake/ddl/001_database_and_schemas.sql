create database if not exists {{ snowflake_database }};
create schema if not exists {{ snowflake_database }}.raw;
create schema if not exists {{ snowflake_database }}.staging;
create schema if not exists {{ snowflake_database }}.intermediate;
create schema if not exists {{ snowflake_database }}.analytics;
