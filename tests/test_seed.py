from sqlalchemy import func, select

import seed
from models import CheckRun, Submission, User


def test_seed_creates_demo_data_and_is_idempotent(db):
    user = seed.seed(db, index=False)
    assert user is not None
    assert seed.seed(db, index=False) is None  # second run is a no-op

    assert db.scalar(select(func.count(User.id))) == 1
    assert db.scalar(select(func.count(Submission.id))) == len(seed.SAMPLES)
    run = db.execute(select(CheckRun)).scalar_one()
    verdicts = {r.verdict for r in run.results}
    assert {"SUPPORTED", "CONTRADICTED"} <= verdicts


def test_seeded_user_can_log_in(client, db):
    seed.seed(db, index=False)
    resp = client.post(
        "/api/auth/login", json={"email": seed.DEMO_EMAIL, "password": seed.DEMO_PASSWORD}
    )
    assert resp.status_code == 200
