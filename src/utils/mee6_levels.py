import json

import asyncio
import aiohttp


BASE = "https://mee6.xyz/api/plugins/levels/leaderboard/"
GUILD_ID = "YOUR_ID"

user_list = []

LEVEL_API_URL = BASE + str(GUILD_ID) + "?page="


async def get_level():
    counter = 0
    fetched_all = False

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(LEVEL_API_URL + str(counter)) as res:
                data = await res.json()
                users = data["players"]
                if not users:
                    break

                counter += 1

                for user in users:
                    if user["level"] == 0:
                        fetched_all = True
                        break

                    user_list.append({"uid": int(user["id"]), "xp": user["xp"]})

            if fetched_all:
                break


async def main():
    await get_level()
    print(len(user_list))

    with open("users.json", "w") as f:
        json.dump(user_list, fp=f)


asyncio.run(main())
