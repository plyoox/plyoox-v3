# Plyoox v3

## Setup
**⚠ Minimum required Python Version is 3.12.**

1. `git clone https://github.com/plyoox/plyoox-v3.git`
2. `cd plyoox-v3`
3. `python3 -m pip install -r requirements.txt`
4. Create a `.env` file and set the following environment variables:
    - `POSTGRES_DSN` (postgresql://`USER`:@`SERVER`:`PORT`/`DATABASE`)
    - `DISCORD_TOKEN` (discord bot token)
    - `LOGGING_WEBHOOK_ID` [optional]
    - `LOGGING_WEBHOOK_TOKEN` [optional]

Generate database: `python3 launcher.py --generate-db`

Run bot: `python3 launcher.py`


### Generating gRPC files: 
Run in src/rpc
```shell
 python -m grpc_tools.protoc -I./proto --python_out=./generated --pyi_out=./generated --grpc_python_out=./generated ./proto/twitch.proto
```