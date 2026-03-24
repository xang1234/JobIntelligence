class _FakeDB:
    def __init__(self):
        self.events = []

    def upsert_job(self, *args, **kwargs):
        self.events.append(("upsert_job", args, kwargs))
        return True, False

    def count_jobs(self):
        self.events.append(("count_jobs", (), {}))
        return 3


def test_dual_write_database_mirrors_writes_and_delegates_reads():
    from src.mcf.dual_write import DualWriteDatabase

    primary = _FakeDB()
    secondary = _FakeDB()
    db = DualWriteDatabase(primary, secondary)

    assert db.upsert_job("job") == (True, False)
    assert db.count_jobs() == 3

    assert primary.events[0][0] == "upsert_job"
    assert secondary.events[0][0] == "upsert_job"
    assert primary.events[1][0] == "count_jobs"
    assert len(secondary.events) == 1
