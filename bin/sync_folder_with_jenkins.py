#!/usr/bin/env python3

import html
import sys
import re
import os
import hashlib
import json
import jenkins

def get_jenkins_password():
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ansible", "jenkins_password.txt")
    with open(filename) as the_file:
        return the_file.read().strip()

class StateSync():
    def __init__(self, state_file="state.json"):
        self._state_file = state_file
        self._current_state = {"files": {}}
        self._saved_state = self._load_state()

    def _load_state(self):
        if not os.path.exists(self._state_file):
            return { "files": {} }
        else:
            with open(self._state_file) as the_file:
                return json.load(the_file)

    def _md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def add_file(self, filename):
        self._current_state["files"][filename] = self._md5(filename)

    def diff(self):
        result = {
            "changed": [],
            "deleted": [],
        }

        for filename, hash in self._current_state["files"].items():
            if hash != self._saved_state["files"].get(filename):
                # if the file does not exist in _staved_state, it will return None which is different from hash
                result["changed"].append(filename)

        for filename in self._saved_state["files"].keys():
            if filename not in self._current_state["files"]:
                result["deleted"].append(filename)

        return result

    def save_state(self):
        # print(json.dumps(self._current_state, sort_keys=True, indent=2))
        with open(self._state_file, "w") as the_file:
            json.dump(self._current_state, the_file, indent=2, sort_keys=True)

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
        self.statesync = None
        self.server = None
        self.url = url
        self.username = username
        self.password = password

    def sync_folder_to_jenkins(self, rootDir):
        self.create_list_of_files(rootDir)
        print("Files to sync:")
        print(json.dumps(jenkins_sync._statesync.diff(), sort_keys=True, indent=2))
        diff = self._statesync.diff()
        if len(diff["changed"]) == 0 and len(diff["deleted"]) == 0:
            print("No changes were made. Nothing do do!")
            return
        self.connect()
        self.send_updated_files(diff)
        self.save_state()
        print("Done")

    def create_list_of_files(self, rootDir):
        self._statesync = StateSync(os.path.join(rootDir, "state.json"))
        for dirName, subdirList, fileList in os.walk(rootDir):
            subdirList.sort()
            for fname in sorted(fileList):
                if fname.endswith(".Jenkinsfile"):
                    full_path = os.path.join(dirName, fname)
                    self._statesync.add_file(full_path)

    def send_updated_files(self, diff):
        for filename in diff["changed"]:
            self._add_file(filename)
        for filename in diff["deleted"]:
            print("Deleting [{}]".format(filename))
            if filename.startswith("." + os.sep):
                filename = filename[2:]
            self.server.delete_job(filename.replace(".Jenkinsfile", ""))

    def save_state(self):
        print("Saving state...")
        self._statesync.save_state()

    def connect(self):
        self.server = jenkins.Jenkins(self.url, self.username, self.password)
        user = self.server.get_whoami()
        version = self.server.get_version()
        print('Connected as %s to Jenkins %s' % (user['fullName'], version))

jenkins_sync = JenkinsSync('http://192.168.58.206:8080', username='admin', password=get_jenkins_password())
jenkins_sync.sync_folder_to_jenkins(".")


