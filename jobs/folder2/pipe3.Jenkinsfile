node {
  def the_user_id="unknown";
  wrap([$class: 'BuildUser']) {
    try {
      the_user_id = "${BUILD_USER_ID}"
    } catch (MissingPropertyException err) {
      the_user_id = params.github_user;
    }
  }

  stage('Validate Parameters') {
      print("-----------------------------------")
      print("Build ID: ${currentBuild.id}")
      sh 'date'
      sh 'pwd'
      sh "echo BUILD_USER_ID=${the_user_id}"
      currentBuild.displayName="#${currentBuild.id}/${the_user_id}"
  }
}