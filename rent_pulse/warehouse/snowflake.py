from __future__ import annotations

from pathlib import Path

from rent_pulse.config import RentPulseConfig


class SnowflakeRunner:
    def __init__(self, config: RentPulseConfig):
        config.require(
            "snowflake_account",
            "snowflake_user",
            "snowflake_password",
            "snowflake_warehouse",
            "snowflake_database",
            "snowflake_storage_integration",
            "snowflake_s3_stage_name",
            "s3_bucket",
        )
        self.config = config

    def _connect(self):
        import snowflake.connector

        return snowflake.connector.connect(
            account=self.config.snowflake_account,
            user=self.config.snowflake_user,
            password=self.config.snowflake_password,
            role=self.config.snowflake_role or None,
            warehouse=self.config.snowflake_warehouse,
            database=self.config.snowflake_database,
            schema=self.config.snowflake_schema,
        )

    def render_sql(self, sql: str) -> str:
        replacements = {
            "{{ snowflake_database }}": self.config.snowflake_database,
            "{{ snowflake_schema }}": self.config.snowflake_schema,
            "{{ snowflake_storage_integration }}": self.config.snowflake_storage_integration,
            "{{ snowflake_s3_stage_name }}": self.config.snowflake_s3_stage_name,
            "{{ s3_bucket }}": self.config.s3_bucket,
            "{{ s3_prefix }}": self.config.s3_prefix,
        }
        rendered = sql
        for token, value in replacements.items():
            rendered = rendered.replace(token, value)
        return rendered

    def execute_sql_text(self, sql: str) -> None:
        statements = [statement.strip() for statement in self.render_sql(sql).split(";") if statement.strip()]
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    def execute_sql_file(self, path: Path) -> None:
        self.execute_sql_text(path.read_text(encoding="utf-8"))

    def bootstrap(self) -> None:
        ddl_dir = self.config.project_root / "snowflake" / "ddl"
        for path in sorted(ddl_dir.glob("00*.sql")):
            self.execute_sql_file(path)

    def copy_raw_records(self) -> None:
        copy_path = self.config.project_root / "snowflake" / "copy_raw_records.sql"
        self.execute_sql_file(copy_path)
