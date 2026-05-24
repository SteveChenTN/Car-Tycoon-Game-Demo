"""
Migration: add AI decision queue and backfill five-dimension personalities.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

DEFAULT_TRAITS = {
    "aggression": 50,
    "innovation": 50,
    "risk_tolerance": 50,
    "loyalty": 50,
    "foresight": 50,
}


def migrate_database(db_path: str) -> bool:
    if not os.path.exists(db_path):
        logger.warning(f"Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_decision_queue (
                id INTEGER PRIMARY KEY,
                game_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                decision_type VARCHAR(30) NOT NULL,
                action VARCHAR(50) NOT NULL,
                parameters JSON NOT NULL DEFAULT '{}',
                reasoning TEXT NOT NULL DEFAULT '',
                priority INTEGER NOT NULL DEFAULT 1,
                target_key VARCHAR(120) NOT NULL DEFAULT 'global',
                created_turn INTEGER NOT NULL,
                due_turn INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                executed_turn INTEGER,
                failure_reason TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(game_id) REFERENCES game_state(id) ON DELETE CASCADE,
                FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_decision_game_status_due
            ON ai_decision_queue (game_id, status, due_turn)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_decision_company_status
            ON ai_decision_queue (company_id, status)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_decision_dedupe
            ON ai_decision_queue (company_id, decision_type, action, target_key, status)
            """
        )

        cursor.execute(
            """
            SELECT id, ai_personality_traits
            FROM companies
            WHERE is_ai = 1
            """
        )
        for company_id, raw_traits in cursor.fetchall():
            traits = DEFAULT_TRAITS.copy()
            if raw_traits:
                try:
                    parsed = json.loads(raw_traits)
                    if isinstance(parsed, dict):
                        traits.update(parsed)
                except json.JSONDecodeError:
                    pass
            cursor.execute(
                """
                UPDATE companies
                SET ai_personality_traits = ?
                WHERE id = ?
                """,
                (json.dumps(traits), company_id),
            )

        conn.commit()
        logger.info(f"AI decision queue migration complete: {db_path}")
        return True
    except Exception as exc:
        conn.rollback()
        logger.error(f"AI decision queue migration failed for {db_path}: {exc}", exc_info=True)
        return False
    finally:
        conn.close()


def migrate_all_databases() -> bool:
    from backend.core.save_manager import GameSessionManager, SaveManager

    save_mgr = SaveManager()
    databases = []

    current_save_path = GameSessionManager.get_current_save_path()
    if current_save_path and current_save_path.exists():
        databases.append(("current save", current_save_path))

    if save_mgr.template_db_path.exists():
        databases.append(("template database", save_mgr.template_db_path))

    main_db_path = project_root / "data" / "automogul.db"
    if main_db_path.exists():
        databases.append(("main database", main_db_path))

    if save_mgr.saves_dir.exists():
        known_paths = {str(path) for _, path in databases}
        for save_file in save_mgr.saves_dir.glob("*.db"):
            if str(save_file) not in known_paths:
                databases.append((f"save: {save_file.name}", save_file))

    if not databases:
        logger.warning("No databases found to migrate")
        return True

    success_count = 0
    for name, path in databases:
        logger.info(f"Migrating {name}: {path}")
        if migrate_database(str(path)):
            success_count += 1

    logger.info(f"Migration complete: {success_count}/{len(databases)} database(s)")
    return success_count == len(databases)


if __name__ == "__main__":
    import argparse

    setup_logging()
    parser = argparse.ArgumentParser(description="Add AI decision queue table")
    parser.add_argument("--db", type=str, help="Specific SQLite database path")
    args = parser.parse_args()

    ok = migrate_database(args.db) if args.db else migrate_all_databases()
    sys.exit(0 if ok else 1)
