#!/usr/bin/env python3

import html
import sys
import re
import os
import hashlib
import json
import jenkins


class StateSync():
    def __init__(self, state_file):
        self._state_file = state_file
        self._current_state = {"files": {}}
        self._saved_state = self._load_state()

    def _load_state(self):
        if not os.path.exists(self._state_file):
            return {"files": {}}
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

    def save_state(self, debug=False):
        if debug:
            print(json.dumps(self._current_state, sort_keys=True, indent=2))
        with open(self._state_file, "w") as the_file:
            json.dump(self._current_state, the_file, indent=2, sort_keys=True)


class JenkinsSync():
    def __init__(self, url, username=None, password=None):
        self.statesync = None
        self.server = None
        self.url = url
        self.username = username
        self.password = password

    def sync_folder_to_jenkins(self, rootDir):
        self._create_list_of_files(rootDir)
        print("Files to sync:")
        diff = self._statesync.diff()
        self._dump_diff(diff)
        if len(diff["changed"]) == 0 and len(diff["deleted"]) == 0:
            print("No changes were made. Nothing do do!")
            return
        self._connect()
        self._send_updated_files(diff)
        self._save_state()
        print("Done")

    @staticmethod
    def _get_setting_from_jenkinsfile(the_regex, pipeline):
        # not supported by jenkinsfiles
        # so we hack and make sure the setting exists as a comment
        # exists somewhere in the jenkinsfile
        m = re.search(the_regex, pipeline, re.MULTILINE)
        if m is None:
            return ""

        groups = m.groups()
        if len(groups) == 0:
            return ""
        return groups[0].strip()

    @staticmethod
    def _get_description(pipeline):
        return JenkinsSync._get_setting_from_jenkinsfile(r"^//\s*description:\s*(.+)", pipeline)

    @staticmethod
    def _get_authtoken(pipeline):
        authtoken = JenkinsSync._get_setting_from_jenkinsfile(r"^//\s*authToken:\s*(.+)", pipeline)
        if authtoken is None or authtoken == "":
            return ""
        return "<authToken>{}</authToken>".format(authtoken)

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
  JENKINS_PIPELINE_AUTHTOKEN_GOES_HERE
  <disabled>false</disabled>
</flow-definition>
    """
        result = SAMPLE_XML.replace("JENKINS_PIPELINE_DESCRIPTION_GOES_HERE", html.escape(JenkinsSync._get_description(pipeline)))
        result = SAMPLE_XML.replace("JENKINS_PIPELINE_AUTHTOKEN_GOES_HERE", JenkinsSync._get_authtoken(pipeline))
        result = result.replace("JENKINS_PIPELINE_SCRIPT_GOES_HERE", html.escape(pipeline))
        return result

    def _send_to_jenkins(self, filename):
        print("Sending {} to Jenkins ...".format(filename))
        with open(filename) as the_file:
            file_content = the_file.read()
        self._check_for_syntax_errors(file_content)
        xml = self._create_xml(file_content)
        self._make_sure_folder_exists_in_jenkins(filename)
        self._send_to_jenkins_helper(filename, xml)

    def _send_to_jenkins_helper(self, filename, xml):
        job_title = filename.replace(".Jenkinsfile", "")
        if job_title.startswith("." + os.sep):
            job_title = job_title[2:]
        self.server.upsert_job(job_title, xml)

    def _make_sure_folder_exists_in_jenkins(self, filename):
        if filename.startswith("." + os.sep):
            filename = filename[2:]
        filename_array = filename.split(os.sep)
        del filename_array[-1] # delete the file name itself

        full_folder_path = ""
        for folder in filename_array:
            full_folder_path =os.path.join(full_folder_path, folder)
            print("Attempting to create folder [{}]".format(full_folder_path))
            self.server.create_folder(full_folder_path, ignore_failures=True)


    def _check_for_syntax_errors(self, file_content):
        errors = self.server.check_jenkinsfile_syntax(file_content)
        for error in errors:
            # https://issues.jenkins-ci.org/browse/JENKINS-59378
            # We get this "error" if the syntax is OK but it's a script pipeline job
            # so we ignore it
            if "did not contain the \'pipeline\' step" not in error.get("error", ""):
                print(error)
                sys.exit(1)

    def _dump_diff(self, diff):
        print(json.dumps(diff, sort_keys=True, indent=2))

    def _create_list_of_files(self, rootDir):
        self._statesync = StateSync(os.path.join(rootDir, "jenkinssync.json"))
        for dirName, subdirList, fileList in os.walk(rootDir):
            subdirList.sort()
            for fname in sorted(fileList):
                if fname.endswith(".Jenkinsfile"):
                    full_path = os.path.join(dirName, fname)
                    self._statesync.add_file(full_path)

    def _send_updated_files(self, diff):
        for filename in diff["changed"]:
            self._send_to_jenkins(filename)
        for filename in diff["deleted"]:
            print("Deleting job [{}]".format(filename))
            if filename.startswith("." + os.sep):
                filename = filename[2:]
            try:
                self.server.delete_job(filename.replace(".Jenkinsfile", ""))
            except jenkins.NotFoundException:
                # somebody already deleted the job. great!
                pass
        self._delete_empty_folders_we_might_have_created(diff)

    def _delete_empty_folders_we_might_have_created(self, diff):
        folders_to_delete = self._get_folders_to_erase(diff)
        jenkins_folders = self._get_jenkins_folder_structure(self.server.get_jobs())
        # print(json.dumps(jekins_folders, sort_keys=2, indent=2))
        # print(folders_to_delete)
        for folder_to_delete in folders_to_delete:
            self._delete_empty_folders_we_might_have_created_helper(jenkins_folders, folder_to_delete)


    def _get_jenkins_folder_structure(self, job_list):
        result = {}
        for a_job in job_list:
            result[a_job["name"]] = a_job
            if "jobs" in a_job:
                a_job["jobs"] = self._get_jenkins_folder_structure(a_job["jobs"])
        return result

    def _delete_empty_folders_we_might_have_created_helper(self, jenkins_folders, folder_to_delete):
        original_jenkins_folders = {"jobs": jenkins_folders}

        folder_array = folder_to_delete.split(os.sep)
        # print(folder_array)

        while len(folder_array) > 0:
            jenkins_folders = original_jenkins_folders
            previous_jenkins_folders = jenkins_folders
            for a_folder in folder_array:
                # print(a_folder)
                previous_jenkins_folders = jenkins_folders
                if a_folder not in jenkins_folders["jobs"]:
                    # the folder has already been deleted in some previou execution of this program, which crashed
                    break
                jenkins_folders = jenkins_folders["jobs"][a_folder]

            # print(jenkins_folders)
            jenkins_path_to_delete = os.sep.join(folder_array) #.join(os.sep)
            if isinstance(jenkins_folders.get("jobs"), dict) and \
                            len(jenkins_folders.get("jobs")) == 0 \
                and jenkins_folders.get("_class") == 'com.cloudbees.hudson.plugins.folder.Folder':

                print("Deleting folder [{}]".format(jenkins_path_to_delete))
                self.server.delete_job(jenkins_path_to_delete)
                del previous_jenkins_folders["jobs"][jenkins_folders["name"]]
            else:
                print("Folder [{}] is not empty. It won't be deleted.".format(jenkins_path_to_delete))
            del folder_array[-1]




        pass

    def _get_folders_to_erase(self, diff):
        folders = []
        for filename in diff["deleted"]:
            pos = filename.rfind(os.sep)
            if pos < 0:
                continue
            begin = 0
            if filename.startswith("." + os.sep):
                begin = 2
            folders.append(filename[begin:pos])
        folders = set(folders)  # remove duplicates
        return folders

    def _save_state(self):
        print("Saving state...")
        self._statesync.save_state()

    def _connect(self):
        self.server = jenkins.Jenkins(self.url, self.username, self.password)
        user = self.server.get_whoami()
        version = self.server.get_version()
        print('Connected as %s to Jenkins %s' % (user['fullName'], version))


def get_jenkins_password():
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ansible", "jenkins_password.txt")
    with open(filename) as the_file:
        return the_file.read().strip()

if __name__ == "__main__":
    jenkins_sync = JenkinsSync('http://192.168.58.208:8080', username='admin', password=get_jenkins_password())
    jenkins_sync.sync_folder_to_jenkins(".")
