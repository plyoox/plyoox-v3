# Plyoox v3

## Setup

### Linux

1. `git clone https://github.com/plyoox/plyoox-v3.git`
2. `cd plyoox-v3`
3. `python3 -m pip install -r requirements.txt`
4. `cd src`
5. Create a `.env` file and set the following environment variables:
    - `POSTGRES` (postgresql://`USER`:@`SERVER`:`PORT`/`DATABASE`)
    - `TOKEN` (discord bot token)
    - `OWNER_ID` (discord bot owner user id)
    - `TEST_SERVER_ID` (discord test server id)
6. `python3 launcher.py --generate-db`
7. `python3 launcher.py --sync-commands`
