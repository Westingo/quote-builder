#!/usr/bin/env python3
"""
new_job.py — scaffold a new job folder from jobs/_template/.

    python new_job.py "Town & Country Fence"     # -> jobs/town-country-fence/job.yaml
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "jobs", "_template")


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "job"


def main(name):
    slug = slugify(name)
    dest = os.path.join(HERE, "jobs", slug)
    if os.path.exists(dest):
        print(f"jobs/{slug} already exists")
        return dest
    os.makedirs(dest)
    shutil.copy(os.path.join(TEMPLATE, "job.yaml"), os.path.join(dest, "job.yaml"))
    print(f"created jobs/{slug}/job.yaml — edit it, then: python build.py jobs/{slug}")
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python new_job.py "Customer Name"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
