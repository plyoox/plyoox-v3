/**
* JetBrains Space Automation
* This Kotlin-script file lets you automate build activities
* For more info, see https://www.jetbrains.com/help/space/automation.html
*/

job("Build and push Docker") {
    host("Build artifacts and a Docker image") {
        dockerBuildPush {
            file = "Dockerfile"
            labels["vendor"] = "Plyoox"
            args["HTTP_PROXY"] = "http://10.20.30.1:123"

            val spaceRepo = "plyoox.registry.jetbrains.space/p/plyoox/plyoox/bot"
            // image tags for 'docker push'
            tags {
                +"$spaceRepo:latest"
            }
        }
    }
}