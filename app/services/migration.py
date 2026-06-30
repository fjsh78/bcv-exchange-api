import sqlite3
import logging

logger = logging.getLogger("bcv.migration")

def check_and_migrate(conn: sqlite3.Connection):
    # Check if the unique constraint exists by checking the sqlite_master schema for exchange_records
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exchange_records'").fetchone()
    if row and "UNIQUE" in row[0]:
        logger.info("Found UNIQUE constraint on exchange_records. Migrating...")

        # Create new table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_records_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                usd REAL,
                eur REAL,
                cny REAL,
                try_rate REAL,
                rub REAL,
                binance REAL,
                timestamp TEXT NOT NULL
            )
            """
        )
        # Copy data
        conn.execute(
            """
            INSERT INTO exchange_records_new (id, date, usd, eur, cny, try_rate, rub, binance, timestamp)
            SELECT id, date, usd, eur, cny, try_rate, rub, binance, timestamp FROM exchange_records
            """
        )
        # Drop old
        conn.execute("DROP TABLE exchange_records")
        # Rename new
        conn.execute("ALTER TABLE exchange_records_new RENAME TO exchange_records")
        logger.info("Migration completed successfully.")
