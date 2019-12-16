#!/usr/bin/env python3

import json
import os

from sync_folder_with_jenkins import StateSync

if __name__ == "__main__":
    state_file="state.json"
    rootDir = "."
    print("StateFile: {}\nRootDir: {}".format(state_file, rootDir))
    syncer = StateSync(state_file)

    for dirName, subdirList, fileList in os.walk(rootDir):
        subdirList.sort()
        for fname in sorted(fileList):
            if fname.endswith(".Jenkinsfile"):
                if dirName != ".":
                    newDirName = dirName
                    if newDirName.startswith("./"):
                        newDirName = newDirName[2:]
                syncer.add_file(os.path.join(dirName, fname))

    print(json.dumps(syncer.diff(), sort_keys=True, indent=2))
    syncer.save_state(debug=True)





