""".env settings are loaded before client.py reads its configuration."""

import os
import subprocess
import sys

# Runs in a fresh interpreter so client.py's import-time settings are read anew.
# load_dotenv is stubbed to set PROXMOX_HOST, standing in for a .env file.
SCRIPT = """
import os
import dotenv

def fake_load_dotenv(*args, **kwargs):
    os.environ["PROXMOX_HOST"] = "from-dotenv"
    return True

dotenv.load_dotenv = fake_load_dotenv

import proxmox_mcp.server
from proxmox_mcp import client
print(client.PROXMOX_HOST)
"""


def test_dotenv_loaded_before_config_is_read():
    env = {k: v for k, v in os.environ.items() if not k.startswith("PROXMOX_")}
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT], env=env, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "from-dotenv"
