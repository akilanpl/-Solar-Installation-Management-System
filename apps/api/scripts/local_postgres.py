"""Manage an isolated portable Windows PostgreSQL cluster (no system service).

Download official EDB PostgreSQL 16 binaries into var/postgresql16/pgsql first.
All data, credentials and logs stay under gitignored var/. Never print secrets.
"""

import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

from local_secrets import protect

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "var" / "postgresql16"
DATA = LOCAL / "data"
BIN = LOCAL / "pgsql" / "bin"
CONFIG = LOCAL / "local-config.json"
PORT = 55432


def run(name: str, *args: str) -> None:
    subprocess.run(
        [str(BIN / f"{name}.exe"), *args],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def connect(config: dict, database: str = "postgres", role: str = "admin"):
    account = config[role]
    return psycopg.connect(
        host="127.0.0.1",
        port=PORT,
        dbname=database,
        user=account["user"],
        password=account["password"],
        connect_timeout=3,
        autocommit=True,
    )


def initialize() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    protect(LOCAL)
    if not CONFIG.exists():
        if DATA.exists():
            raise SystemExit("Existing data without local config; refusing to replace credentials.")
        config = {
            name: {"user": user, "password": secrets.token_urlsafe(32)}
            for name, user in (
                ("admin", "solarops_local_admin"),
                ("dev", "solarops"),
                ("test", "solarops_test_runner"),
            )
        }
        CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        protect(CONFIG)
    config = load_config()
    if not (DATA / "PG_VERSION").exists():
        password_file = LOCAL / "init-password.txt"
        password_file.write_text(config["admin"]["password"] + "\n", encoding="utf-8")
        protect(password_file)
        try:
            run(
                "initdb",
                "-D",
                str(DATA),
                "-U",
                config["admin"]["user"],
                "--pwfile",
                str(password_file),
                "--auth",
                "scram-sha-256",
                "--encoding",
                "UTF8",
                "--locale",
                "C",
            )
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a", encoding="utf-8") as file:
            file.write(
                "\nlisten_addresses = '127.0.0.1'\nport = 55432\npassword_encryption = 'scram-sha-256'\n"
            )
    start()
    with connect(config) as db:
        for name, database in (("dev", "solarops_dev"), ("test", "solarops_test")):
            account = config[name]
            if not db.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (account["user"],)
            ).fetchone():
                db.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(account["user"]), sql.Literal(account["password"])
                    )
                )
            if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
                db.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(database), sql.Identifier(account["user"])
                    )
                )
            db.execute(
                sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(database)
                )
            )
    env_path = ROOT / ".env"
    if not env_path.exists():

        def url(role: str, database: str) -> str:
            account = config[role]
            return URL.create(
                "postgresql+psycopg",
                username=account["user"],
                password=account["password"],
                host="127.0.0.1",
                port=PORT,
                database=database,
                query={"connect_timeout": "3"},
            ).render_as_string(hide_password=False)

        env_path.write_text(
            "SOLAROPS_APP_ENV=development\n"
            f"SOLAROPS_DATABASE_URL={url('dev', 'solarops_dev')}\n"
            f"SOLAROPS_TEST_DATABASE_URL={url('test', 'solarops_test')}\n"
            f"SOLAROPS_SECRET_KEY={secrets.token_urlsafe(48)}\n"
            "SOLAROPS_COOKIE_SECURE=false\n"
            "SOLAROPS_TRUSTED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000\n"
            "SOLAROPS_MAILBOX_PATH=var/dev-mailbox.jsonl\n",
            encoding="utf-8",
        )
        protect(env_path)
    else:
        print("Existing .env preserved; ensure its dev/test URLs use this isolated cluster.")
    protect(env_path)
    for role, database in (("dev", "solarops_dev"), ("test", "solarops_test")):
        with connect(config, database, role) as db:
            row = db.execute("SELECT current_database(), version()").fetchone()
            print(f"Connected: {row[0]}; {row[1].split(',')[0]}")
    print("Separate database owners configured; PUBLIC cannot connect to either database.")


def start() -> None:
    status = subprocess.run(
        [str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"], capture_output=True
    )
    if status.returncode != 0:
        run("pg_ctl", "-D", str(DATA), "-l", str(LOCAL / "server.log"), "-w", "start")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "start", "stop", "status"])
    action = parser.parse_args().action
    if action == "init":
        initialize()
    elif action == "start":
        start()
    elif action == "stop":
        run("pg_ctl", "-D", str(DATA), "-m", "fast", "-w", "stop")
    else:
        run("pg_ctl", "-D", str(DATA), "status")
