import os
import tempfile
import json
import time
import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    # Use a temporary sqlite DB for tests
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["PLEBX_DB_PATH"] = path
    # Ensure writeback disabled for tests
    os.environ["ENABLE_WRITEBACK"] = "false"

    # Import app after env is set
    from agent_api.app import app

    with TestClient(app) as c:
        yield c


def test_seed_and_feed(client):
    r = client.post('/admin/seed?mode=ipfs&limit=20')
    assert r.status_code == 200
    body = r.json()
    assert body.get('ok') is True
    assert body.get('seeded', 0) > 0

    r2 = client.get('/feed?mode=db&limit=10')
    assert r2.status_code == 200
    fb = r2.json()
    assert fb.get('ok') is True
    assert isinstance(fb.get('posts'), list)
    assert len(fb.get('posts')) > 0


def test_follow_counts_and_feed_mode(client):
    # Ensure sample users exist from seed
    # Make sample-1 follow sample-0
    follow = client.post('/user/sample-0/follow', headers={"X-User": "sample-1"})
    assert follow.status_code == 200
    j = follow.json()
    assert j.get('ok') is True

    # Following list for sample-1 contains sample-0
    r = client.get('/user/sample-1/following')
    assert r.status_code == 200
    data = r.json()
    assert 'sample-0' in data.get('following', [])

    # Counts for sample-0 show at least 1 follower
    r2 = client.get('/user/sample-0/counts')
    assert r2.status_code == 200
    c = r2.json()
    assert c['counts']['followers'] >= 1

    # Follows feed for sample-1 returns posts from sample-0 (mode=follows)
    r3 = client.get('/feed?mode=follows&viewer=sample-1&limit=10')
    assert r3.status_code == 200
    f = r3.json()
    assert f.get('ok') is True
    assert isinstance(f.get('posts'), list)


def test_publish_dryrun_persists_reply(client):
    # Post a dry-run reply as sample-1 to sample-0
    payload = {"user": "sample-1", "content": "pytest reply test", "reply_to": "sample-0", "dry_run": True}
    r = client.post('/post', json=payload, headers={"X-User": "sample-1"})
    assert r.status_code == 200
    body = r.json()
    assert body.get('ok') is True
    assert body.get('dry_run') is True
    assert 'created' in body

    created = body['created']
    # Fetch thread for sample-0 and assert created id present
    r2 = client.get('/post/sample-0?mode=db&depth=2&page=1&per_page=50')
    assert r2.status_code == 200
    t = r2.json()
    found = False
    for node in t.get('thread', []):
        if node.get('id') == created.get('id'):
            found = True
            break
    assert found, "Created reply should appear in sample-0 thread"
