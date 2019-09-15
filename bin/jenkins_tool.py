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

server = jenkins.Jenkins('http://192.168.58.206:8080', username='admin', password=get_jenkins_password())
user = server.get_whoami()
version = server.get_version()
print('Connected as %s to Jenkins %s' % (user['fullName'], version))

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

def get_description(pipeline):
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

def create_xml(pipeline):
    result = SAMPLE_XML.replace("JENKINS_PIPELINE_DESCRIPTION_GOES_HERE", html.escape(get_description(pipeline)))
    result = result.replace("JENKINS_PIPELINE_SCRIPT_GOES_HERE", html.escape(pipeline))
    return result

def add_file(filename):
    print("Loading {} into Jenkins ...".format(filename))
    with open(filename) as the_file:
        file_content = the_file.read()
    errors = server.check_jenkinsfile_syntax(file_content)
    for error in errors:
        # https://issues.jenkins-ci.org/browse/JENKINS-59378
        # We get this "error" if the syntax is OK but it's a script pipeline job
        # so we ignore it
        if "did not contain the \'pipeline\' step" not in error.get("error", ""):
            print(error)
            sys.exit(1)
    xml = create_xml(file_content)
    job_title = filename.replace(".Jenkinsfile", "")
    if job_title.startswith("./"):
        job_title = job_title[2:]
    server.upsert_job(job_title, xml)

def create_jenkinsfiles_from_folder(rootDir):
    for dirName, subdirList, fileList in os.walk(rootDir):

        for fname in fileList:
            if fname.endswith(".Jenkinsfile"):
                if dirName != ".":
                    newDirName = dirName
                    if newDirName.startswith("./"):
                        newDirName = newDirName[2:]
                    server.create_folder(newDirName, ignore_failures=True)
                add_file(os.path.join(dirName, fname))


create_jenkinsfiles_from_folder(".")
print("Done")

