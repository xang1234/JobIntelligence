from src.mcf.database import MCFDatabase
from src.mcf.db_backup import create_sqlite_hot_backup, verify_sqlite_backup


def test_create_and_verify_sqlite_hot_backup(temp_dir):
    db_path = temp_dir / "source.db"
    MCFDatabase(str(db_path))

    backup_path = create_sqlite_hot_backup(db_path, temp_dir / "backups", prefix="unit")
    metadata = verify_sqlite_backup(backup_path)

    assert backup_path.exists()
    assert metadata.integrity_check == "ok"
    assert metadata.jobs_count == 0
    assert metadata.size_bytes > 0
