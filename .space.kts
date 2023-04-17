/**
* JetBrains Space Automation
* This Kotlin-script file lets you automate build activities
* For more info, see https://www.jetbrains.com/help/space/automation.html
*/

job("Build and push Docker") {
    host("Build artifacts and a Docker image") {
        requirements {
            os {
                type = OSType.Linux
                arch = "aarch64"
            }
        }

        dockerBuildPush {
            file = "Dockerfile"
            labels["vendor"] = "Plyoox"

            val spaceRepo = "plyoox.registry.jetbrains.space/p/plyoox/plyoox/bot"
            // image tags for 'docker push'
            tags {
                +"$spaceRepo:latest"
                +"$spaceRepo:arm"
            }
        }
    }
}