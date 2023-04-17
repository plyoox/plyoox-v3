docker buildx . -t plyoox/bot --platform linux/arm64
docker tag plyoox/bot plyoox.registry.jetbrains.space/p/plyoox/plyoox/bot
docker push plyoox.registry.jetbrains.space/p/plyoox/plyoox/bot