Jenkis Tools
============

Here are some tools I am preparing for my (not yet approved) Jenkins Talk

The idea is to automate jenkins as much as possible,
having it's settings saved in a small, simple deterministic place.

currently we have

- [ansible/setup_machine.yml](ansible/setup_machine.yml) - an ansible script to install jenkins from scratch
- [ansible/configure_jenkins.yml](ansible/configure_jenkins.yml) - an ansible script to install plugins and other settings on an existing jenkins installation
- [bin/sync_folder_with_jenkins.py](bin/sync_folder_with_jenkins.py) - a tool that automatically publishes all Jenkinsfile the on the current folder to jenkins

The idea for the user to clone this git repository, be able to edit all his/her Jenkinsfiles in the [jobs](jobs) folder, call `sync_folder_with_jenkins.py` and nothing else.


Author: Marcos Diez <marcos AT unitron DOT com DOT br>
License: GPLv2