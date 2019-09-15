#!/usr/bin/env python3

import jenkins
import html
import sys
import re
import os

def get_jenkins_password():
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ansible", "jenkins_password.txt")
    with open(filename) as the_file:
        return the_file.read().strip()

class JenkinsSync():

    @staticmethod
    def _get_description(pipeline):
        # not supported by jenkinsfiles
        # so we hack and make sure a // description: THE_DESCRIPTION
        # exists somewhere in the jenkinsfile
        m = re.search(r"^//\s*description:\s*(.+)", pipeline, re.MULTILINE)
        if m is None:
            return ""

        groups = m.groups()
        if len(groups) == 0:
            return ""
        return groups[0]

    @staticmethod
    def _create_xml(pipeline):

        SAMPLE_XML = """
<flow-definition plugin="workflow-job">
  <description>JENKINS_PIPELINE_DESCRIPTION_GOES_HERE</description>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>JENKINS_PIPELINE_SCRIPT_GOES_HERE</script>
    <sandbox>false</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
    """

        result = SAMPLE_XML.replace("JENKINS_PIPELINE_DESCRIPTION_GOES_HERE", html.escape(JenkinsSync._get_description(pipeline)))
        result = result.replace("JENKINS_PIPELINE_SCRIPT_GOES_HERE", html.escape(pipeline))
        return result

    def _add_file(self, filename):
        print("Loading {} into Jenkins ...".format(filename))
        with open(filename) as the_file:
            file_content = the_file.read()
        errors = self.server.check_jenkinsfile_syntax(file_content)
        for error in errors:
            # https://issues.jenkins-ci.org/browse/JENKINS-59378
            # We get this "error" if the syntax is OK but it's a script pipeline job
            # so we ignore it
            if "did not contain the \'pipeline\' step" not in error.get("error", ""):
                print(error)
                sys.exit(1)
        xml = self._create_xml(file_content)
        job_title = filename.replace(".Jenkinsfile", "")
        if job_title.startswith("./"):
            job_title = job_title[2:]
        self.server.upsert_job(job_title, xml)

    def __init__(self, url, username=None, password=None):
        self.server = jenkins.Jenkins(url, username, password)


    def create_jenkinsfiles_from_folder(self, rootDir):
        for dirName, subdirList, fileList in os.walk(rootDir):
            for fname in fileList:
                if fname.endswith(".Jenkinsfile"):
                    if dirName != ".":
                        newDirName = dirName
                        if newDirName.startswith("./"):
                            newDirName = newDirName[2:]
                        self.server.create_folder(newDirName, ignore_failures=True)
                    self._add_file(os.path.join(dirName, fname))

    def banner(self):
        user = self.server.get_whoami()
        version = self.server.get_version()
        print('Connected as %s to Jenkins %s' % (user['fullName'], version))

jenkins_sync = JenkinsSync('http://192.168.58.206:8080', username='admin', password=get_jenkins_password())
jenkins_sync.banner()
jenkins_sync.create_jenkinsfiles_from_folder(".")
print("Done")

