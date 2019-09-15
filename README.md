Jenkis Tools
============

Here are some tools I am preparing for my (not yet approved) Jenkins Talk

The idea is to automate Jenkins as much as possible,
having it's settings/plugins/jobs saved in a small, simple deterministic place.

Currently we have:

- [ansible/setup_machine.yml](ansible/setup_machine.yml) - an ansible script to install jenkins from scratch
- [ansible/configure_jenkins.yml](ansible/configure_jenkins.yml) - an ansible script to install plugins and other settings on an existing jenkins installation
- [bin/sync_folder_with_jenkins.py](bin/sync_folder_with_jenkins.py) - a tool that automatically publishes all Jenkinsfile the on the current folder to jenkins

Whenever one runs `sync_folder_with_jenkins.py`, search for all files with ending `.Jenkinsfile` in the current folder and subfolders and sends them to Jenkins as a Jenkins (scripted or declarative) Pipeline Job. Before the job is saved in Jenkins, we actually use jenkins to lint the job so you can be sure you won't have any syntax errors.

The name of the job is the name of the file, removing the `.Jenkinsfile` extension.
If the file is inside of subfolders, they are also created, so the path in the disk is consistent with what you will get in Jenkins.

After the script is executed, it saves the list of files it uploaded to jenkins and their md5 in a file called `jenkinssync.json`.

Which means whenever you run the script again, it will compare the current state on the disk with the contents of `jenkinssync.json`, adding or updating new files and deleting removed ones. If after a file is removed it's folder in Jenkins is empty, the folder will be removed as well.

AFAIK, some job information like the Job Description can not be saved in a Jenkinsfile.
Well... So here is a little hack: if the Jenkinsfile contains a like starting with `// description: `, whatever comes after that will be the job description.

Author: Marcos Diez <marcos AT unitron DOT com DOT br>
License: GPLv2