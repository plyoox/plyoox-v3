# Plyoox v3

## Setup

### Linux
**⚠ Minimum required Python Version is 3.10.**

1. `git clone https://github.com/plyoox/plyoox-v3.git`
2. `cd plyoox-v3`
3. `python3 -m pip install -r requirements.txt`
4. Create a `.env` file and set the following environment variables:
    - `POSTGRES` (postgresql://`USER`:@`SERVER`:`PORT`/`DATABASE`)
    - `TOKEN` (discord bot token)
    - `TEST_GUILD` (discord test guild id)
5. `python3 launcher.py --generate-db`
6. `python3 launcher.py --sync-commands`
