"""The secret scan in hooks/gate.sh, run through the hook under the system grep (v0.318.3).

Until 0.318.3 the scan had no test. Nine of its patterns put `\\s` and `\\x27` inside bracket
expressions; the BSD grep that /usr/bin/grep is on macOS reads a backslash in a bracket as a literal
character, so the class meant for whitespace matched the letter s and the class meant for a single
quote matched x, 2 and 7. Whether a credential was caught depended on which letters it contained
(dogfood harms check 2026-10-11). These tests run the HOOK, not a copy of its patterns, with PATH
cut down to the system directories so `grep` is whatever the machine's own grep is: BSD on a
developer's Mac, GNU on the CI runner.

Every credential-shaped value is BUILT AT RUN TIME from harmless parts. A literal one in this file
would be refused by the hook under test in any session that edits it, and by a host's push scanning.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "gate.sh"

PW = "hunter" + "2" + "hunter" + "2"          # holds the digits and letters the old classes ate
KEY = "ab12" * 6                               # 24 characters
PASSWORD = "pass" + "word"
SCHEMES = {"pg": "post" + "gres", "my": "my" + "sql", "mongo": "mongo" + "db+srv",
           "redis": "red" + "is"}


def _url(scheme: str, userinfo: str, rest: str = "db.internal:5432/prod") -> str:
    return f"{SCHEMES[scheme]}://{userinfo}{rest}"


MUST_REFUSE = {
    "password in double quotes": f'{PASSWORD}: "{PW}"',
    "password in single quotes": f"{PASSWORD} = '{PW}'",
    "password with spaces around the sign": f'{PASSWORD}   =   "{PW}"',
    "api key": f'API_KEY="{KEY}"',
    "secret key in single quotes": f"secret_key: '{KEY}'",
    "bearer token with a hyphen and a dot": "Authorization: " + "Bear" + "er " + "ab-12.cd_34" * 3,
    "private key assignment": "PRIVATE" + '_KEY = "-----BEGIN',
    "database url with a password": _url("pg", f"app:{PW}@"),
    "mysql url with a password": _url("my", f"root:{PW}@", "localhost/shop"),
    "mongodb url with a password": _url("mongo", f"svc:{PW}@", "cluster0.example.net/app"),
    "redis url with a password and no user": _url("redis", f":{PW}@", "cache.internal:6379"),
    "database url with a password parameter": _url("pg", "", f"db.internal/prod?sslmode=require&{PASSWORD}={PW}"),
    "provider token by prefix": "gh" + "p_" + "A1b2" * 9,
    "access key id by prefix": "AK" + "IA" + "ABCD1234" * 2,
}

MUST_PASS = {
    "database url with no password": _url("pg", "", "localhost:5432/devdb_local"),
    "database url with a user and no password": _url("pg", "app@", "db.internal:5432/prod"),
    "the word in prose": f"The {PASSWORD} is discussed in the docs, section two.",
    "password read from the environment": f'{PASSWORD} = os.environ["DB_SECRET_NAME"]',
    "an empty password": f'{PASSWORD}: ""',
    "a short value": f'{PASSWORD}: "abc"',
    "letters the old classes misread": 'label: "sixty-two taxis x 27"',
    "a library name that starts like a token": "pip install sk-learn-extras",
}


def _run(tmp_path, content: str) -> str:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)  # a Mycelium project
    payload = json.dumps({"tool_name": "Write", "permission_mode": "default",
                          "tool_input": {"file_path": "src/config.py", "content": content}})
    env = {"CLAUDE_PROJECT_DIR": str(tmp_path), "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
           "PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)}
    done = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                          env=env, cwd=tmp_path, check=False)
    return done.stdout


@pytest.mark.parametrize("label", sorted(MUST_REFUSE))
def test_a_credential_is_refused_whatever_letters_it_holds(tmp_path, label):
    out = _run(tmp_path, f"# settings\n{MUST_REFUSE[label]}\n")
    assert "G-S1" in out, f"{label}: the scan let it through"
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("label", sorted(MUST_PASS))
def test_control_harmless_text_is_not_called_a_secret(tmp_path, label):
    out = _run(tmp_path, f"# settings\n{MUST_PASS[label]}\n")
    assert "G-S1" not in out, f"{label}: refused as a secret"


def test_the_patterns_use_no_backslash_escape_inside_a_bracket():
    """The defect itself, as a property of the file. The three escapes that BSD grep reads as
    letters inside a bracket (`\\s`, `\\x27`, `\\-`) appear nowhere in the pattern table: whitespace
    and quotes come from the named classes above it, and a hyphen sits last in its bracket."""
    text = HOOK.read_text(encoding="utf-8")
    start = text.index("SECRET_PATTERNS=(")
    block = text[start:text.index("\n  )", start)]
    assert block.count("\n") >= 10, "the pattern table was not found whole"
    for escape in ("\\s", "\\x", "\\-"):
        assert escape not in block, f"{escape} is back in the pattern table"
