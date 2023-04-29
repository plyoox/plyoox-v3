/**
 * JetBrains Space Automation
 * This Kotlin-script file lets you automate build activities
 * For more info, see https://www.jetbrains.com/help/space/automation.html
 */

job("Run API Job") {
    startOn {
        gitPush {
            anyRefMatching {
                +"refs/tags/rc/v*" // all rc tags
                +"refs/tags/release/v*" // all release tags
                +"refs/heads/unstable" // unstable branch
            }
        }
    }

    host("Generating image tag") {
        kotlinScript { api ->
            val ref = api.gitBranch()

            if (ref.matches(Regex("""refs/tags/rc/v\d\.\d\.\d-\d"""))) {
                val currentVersion = ref.replace("refs/tags/rc/v", "").split("-")

                api.parameters["version"] = "${currentVersion[0]}-rc.${currentVersion[1]}"
                api.parameters["channel"] = "release-candidate"
            } else if (ref.matches(Regex("""refs/tags/release/v\d\.\d\.\d"""))) {
                api.parameters["version"] = ref.replace("refs/tags/release/v", "")
                api.parameters["channel"] = "stable"
            } else {
                api.parameters["version"] = "unstable"
                api.parameters["channel"] = "canary"
            }
        }
    }

    host("Run docker build and push") {
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
            tags {
                +"${spaceRepo}:latest"
                +"${spaceRepo}:{{ channel }}"
                +"${spaceRepo}:{{ version }}"
            }
        }
    }

    container("Run deploy script", image = "gradle:7.6-jdk11") {
        resources {
            cpu = 2.cpu
            memory = 2.gb
        }

        kotlinScript { api ->
            api.space().projects.automation.deployments.schedule(
                    project = api.projectIdentifier(),
                    targetIdentifier = TargetIdentifier.Key("api"),
                    version = api.parameters["version"],
            )
        }
    }
}
