"""Use Docker's maintained profile plus Playwright's documented userns rules."""
import hashlib
import json
import urllib.request
from pathlib import Path

SOURCE = "https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json"


def prepare(profile):
    assert profile["defaultAction"] == "SCMP_ACT_ERRNO"
    profile["syscalls"].append({"names": ["clone", "setns", "unshare"], "action": "SCMP_ACT_ALLOW", "args": []})
    return profile


if __name__ == "__main__":
    raw = urllib.request.urlopen(SOURCE, timeout=40).read()
    Path(__file__).with_name("seccomp-source.json").write_text(json.dumps({"url": SOURCE, "sha256": hashlib.sha256(raw).hexdigest()}))
    Path(__file__).with_name("seccomp_profile.json").write_text(json.dumps(prepare(json.loads(raw))))
