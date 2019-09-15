Ansible scripts to prepare jenkins

Usage:
- make sure your ansible is >= 2.10, because newer jenkins only talk to this version of ansible
- `nano inventory.ini` # put the right credentials for your jenkins server
- `ansible-playbook -i inventory.ini setup_machine.yml`
- `nano jenkins_password.txt`
- go to Jenkins on http://IP_ADDRESS:8080/ and finish configuring it
- `ansible-playbook -i inventory.ini configure_jenkins.yml`

Yes, there is a nice ansible role at https://github.com/geerlingguy/ansible-role-jenkins , but it does not make jenkins secure by default. Hence we are not using it for now.
If we were, only one ansible playbook would be necessary.

