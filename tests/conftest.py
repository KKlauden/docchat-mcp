"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def minimal_pack(tmp_path: Path) -> Path:
    """Create a minimal knowledge pack with 1 feed + _shared + _overview."""
    # docchat.yaml
    (tmp_path / "docchat.yaml").write_text("name: test-api\ndimensions: []\n")

    # _shared/INDEX.yaml
    shared_dir = tmp_path / "_shared"
    shared_dir.mkdir()
    (shared_dir / "INDEX.yaml").write_text(
        "topics:\n"
        "  - path: auth/overview.md\n"
        "    keywords: [authentication, auth, token, OAuth]\n"
        "  - path: error_codes.md\n"
        '    keywords: [error, "错误码", status code]\n'
    )
    (shared_dir / "error_codes.md").write_text(
        "# Error Codes\n\n- 400: Bad Request\n- 401: Unauthorized\n"
    )
    auth_dir = shared_dir / "auth"
    auth_dir.mkdir()
    (auth_dir / "overview.md").write_text(
        "# Authentication\n\nUse OAuth 2.0 for authentication.\n"
    )

    # _overview/
    overview_dir = tmp_path / "_overview"
    overview_dir.mkdir()
    (overview_dir / "INDEX.md").write_text(
        "# API Overview\n\nThis API has 1 endpoint.\n"
    )

    # feeds/get-users/
    feed_dir = tmp_path / "feeds" / "get-users"
    feed_dir.mkdir(parents=True)
    (feed_dir / "META.yaml").write_text(
        "name: get-users\n"
        "feed_name: Get Users\n"
        "description: Returns a list of users\n"
        "triggers:\n"
        "  keywords:\n"
        "    - user list, get users, all users\n"
        "    - 用户列表, 获取用户\n"
        "  scenarios:\n"
        "    - Get a list of all users\n"
        "fields:\n"
        "  - userId\n"
        "  - userName\n"
        "  - email\n"
        "endpoint: GET /api/users\n"
    )
    (feed_dir / "GUIDE.md").write_text(
        "# Get Users Guide\n\nCall GET /api/users to retrieve users.\n"
    )
    (feed_dir / "FAQ.md").write_text(
        "# Get Users FAQ\n\n## Q: Why is the response empty?\n\n"
        "**Check:** Verify your auth token.\n"
        "**Cause:** Expired token.\n"
        "**Resolution:** Refresh the token.\n"
    )

    # feeds/get-posts/
    posts_dir = tmp_path / "feeds" / "get-posts"
    posts_dir.mkdir(parents=True)
    (posts_dir / "META.yaml").write_text(
        "name: get-posts\n"
        "feed_name: Get Posts\n"
        "description: Returns a list of posts\n"
        "triggers:\n"
        "  keywords:\n"
        "    - post list, get posts, blog posts\n"
        "    - 文章列表, 获取文章\n"
        "fields:\n"
        "  - postId\n"
        "  - title\n"
        "  - body\n"
        "endpoint: GET /api/posts\n"
    )
    (posts_dir / "GUIDE.md").write_text(
        "# Get Posts Guide\n\nCall GET /api/posts to retrieve posts.\n"
    )

    return tmp_path
