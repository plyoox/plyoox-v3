# Plyoox v3

## Setup
**⚠ Minimum required Python Version is 3.10.**

1. `git clone https://github.com/plyoox/plyoox-v3.git`
2. `cd plyoox-v3`
3. `python3 -m pip install -r requirements.txt`
4. Create a `.env` file and set the following environment variables:
    - `POSTGRES_DSN` (postgresql://`USER`:@`SERVER`:`PORT`/`DATABASE`)
    - `DISCORD_TOKEN` (discord bot token)
    - `IMAGER_URL` (url to image generator: see https://gitlab.com/plyoox/imager.git)
    - `LOGGING_WEBHOOK_ID` [optional]
    - `LOGGING_WEBHOOK_TOKEN` [optional]

Generate database: `python3 launcher.py --generate-db`

Run bot: `python3 launcher.py`
