from feedcloud import helpers


def test_password_hash():
    password_str = "some password"
    hash = helpers.hash_password(password_str)
    assert helpers.check_password(password_str, hash)
    assert not helpers.check_password("invalid password", hash)
