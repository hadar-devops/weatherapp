pipeline {
    agent none

    environment {
        IMAGE_BASE = 'hadar183/weatherapp'
        VERSION = "${BUILD_NUMBER}-${BRANCH_NAME}".replaceAll('/', '-')
        IMAGE_NAME = "${IMAGE_BASE}:${VERSION}"
        TAG = "${VERSION}"
    }

    stages {
        stage('Clone GitLab Repo (Source)') {
            agent { label '' }
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${env.BRANCH_NAME}"]],
                    userRemoteConfigs: [[
                        url: 'http://hadarapp.com/gitlab/new-username/weatherapp.git',
                        credentialsId: 'gitlab-token'
                    ]]
                ])
                stash name: 'workspace', includes: '**'
                echo "Repo cloned and stashed on controller"
            }
        }

        stage('Install Dev Tools') {
            agent { label 'weather' }
            steps {
                unstash 'workspace'
                sh '''
                    echo "Creating virtual environment for DevSecOps tools..."
                    python3 -m venv venv
                    . venv/bin/activate

                    echo "Installing dev dependencies..."
                    venv/bin/pip install -r requirements-dev.txt

                    echo "Installing Trivy..."
                    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b ./trivy-bin
                    chmod +x ./trivy-bin/trivy

                    echo "Installing cosign..."
                    curl -sSL https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64 -o cosign
                    chmod +x cosign
                '''
                stash name: 'workspace-with-tools', includes: '**'
            }
        }

        stage('Dependency Scan') {
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh '''
                    . venv/bin/activate
                    echo "Running safety for dependency vulnerability check..."
                    venv/bin/safety check -r requirements.txt -r requirements-dev.txt > safety_report.txt || true

                    echo "Filtering only CRITICAL vulnerabilities..."
                    grep "CRITICAL" safety_report.txt || echo "No critical vulnerabilities found."

                    if grep -q "CRITICAL" safety_report.txt; then
                        exit 1
                    fi
                '''
            }
        }

        stage('Static Code Analysis - Pylint') {
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh '''
                    test -f app.py || (echo "app.py not found" && exit 1)
                    . venv/bin/activate
                    venv/bin/pylint app.py --score=y > pylint_report.txt || true
                '''
                script {
                    def scoreLine = readFile('pylint_report.txt').readLines().find { it.contains('Your code has been rated at') }
                    if (!scoreLine) error("Could not find pylint score line.")
                    def match = scoreLine =~ /rated at\s+([0-9.]+)\/10/
                    if (!match.find()) error("Failed to extract score.")
                    def score = match[0][1].toFloat()
                    echo "Pylint score: ${score}"
                    if (score < 5.0) {
                        error("Pylint score too low: ${score}")
                    }
                }
            }
        }

        stage('Trivy Scan (Dockerfile + Config)') {
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh '''
                    ./trivy-bin/trivy config . \
                      --severity CRITICAL,HIGH \
                      --exit-code 1
                '''
            }
        }

        stage('Docker Build') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    branch pattern: "feature/.*", comparator: "REGEXP"
                    branch pattern: "release/.*", comparator: "REGEXP"
                    branch pattern: "hotfix/.*", comparator: "REGEXP"
                }
            }
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh 'docker build -t ${IMAGE_NAME} -t ${IMAGE_BASE}:latest .'
            }
        }

        stage('Trivy Scan (Docker Image)') {
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh '''
                    ./trivy-bin/trivy image ${IMAGE_NAME} \
                      --severity CRITICAL,HIGH \
                      --exit-code 0
                '''
            }
        }

        stage('Reachability Test') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    branch pattern: "feature/.*", comparator: "REGEXP"
                    branch pattern: "release/.*", comparator: "REGEXP"
                    branch pattern: "hotfix/.*", comparator: "REGEXP"
                }
            }
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                sh '''
                    docker run -d -p 5000:5000 --name weatherapp-test ${IMAGE_NAME}
                    sleep 5
                    if curl -f http://localhost:5000/; then
                        echo "App is reachable!"
                    else
                        docker logs weatherapp-test
                        docker stop weatherapp-test
                        docker rm weatherapp-test
                        exit 1
                    fi
                    docker stop weatherapp-test
                    docker rm weatherapp-test
                '''
            }
        }

        stage('Push to Docker Hub') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    branch pattern: "release/.*", comparator: "REGEXP"
                    branch pattern: "hotfix/.*", comparator: "REGEXP"
                }
            }
            agent { label 'weather' }
            steps {
                unstash 'workspace-with-tools'
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${IMAGE_NAME}
                        docker push ${IMAGE_BASE}:latest
                    '''
                }
            }
        }

        stage('Sign Docker Image') {
            agent { label 'weather' }
            environment {
                COSIGN_PASSWORD = credentials('cosign-pass')
            }
            steps {
                unstash 'workspace-with-tools'
                withCredentials([file(credentialsId: 'cosign-private-key', variable: 'COSIGN_KEY')]) {
                    sh '''
                        IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ${IMAGE_NAME})
                        ./cosign sign --key "$COSIGN_KEY" --yes "$IMAGE_NAME"
                    '''
                }
            }
        }

        stage('Clone Deployment Repository') {
            when {
                branch 'main'
            }
            agent { label 'weather' }
            steps {
                dir('gitops_dir') {
                    git branch: 'main',
                        url: "http://hadarapp.com/gitlab/new-username/weatherapp-deploy.git",
                        credentialsId: 'gitlab-deploy-argo-token'
                }
            }
        }

        stage('Modify values.yaml with yq') {
            when {
                branch 'main'
            }
            agent { label 'weather' }
            steps {
                dir('gitops_dir') {
                    sh """
                        sudo wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
                        sudo chmod +x /usr/local/bin/yq
                        yq e '.image.tag = strenv(TAG)' -i weatherapp-chart/values.yaml
                        cat weatherapp-chart/values.yaml
                    """
                }
            }
        }

        stage('Push Updated values.yaml') {
            when {
                branch 'main'
            }
            agent { label 'weather' }
            steps {
                dir('gitops_dir') {
                    withCredentials([usernamePassword(
                        credentialsId: 'gitlab-deploy-argo-token',
                        usernameVariable: 'GIT_USER', 
                        passwordVariable: 'GIT_TOKEN')]) {
                        sh """
                            git config user.email "jenkins@yourdomain.com"
                            git config user.name "jenkins"
                            git add weatherapp-chart/values.yaml
                            git commit -m "Update image tag to ${TAG}" || echo "No changes to commit"
                            git push http://${GIT_USER}:${GIT_TOKEN}@hadarapp.com/gitlab/new-username/weatherapp-deploy.git main
                        """
                    }
                }
            }
        }

        stage('Notify Slack') {
            when {
                anyOf {
                    branch 'main'
                    branch pattern: "release/.*", comparator: "REGEXP"
                    branch pattern: "hotfix/.*", comparator: "REGEXP"
                }
            }
            agent { label 'weather' }
            steps {
                script {
                    def msg = (currentBuild.currentResult == 'SUCCESS') ?
                        "Build #${env.BUILD_NUMBER} on *${env.BRANCH_NAME}* succeeded." :
                        "Build #${env.BUILD_NUMBER} on *${env.BRANCH_NAME}* failed."

                    withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_URL')]) {
                        sh """
                            curl -X POST -H 'Content-type: application/json' --data '{
                                "channel": "#weather-app",
                                "username": "jenkins-bot",
                                "text": "${msg}"
                            }' $SLACK_URL
                        """
                    }
                }
            }
        }

        stage('Clean Workspace') {
            agent { label 'weather' }
            steps {
                cleanWs()
            }
        }
    }
}
