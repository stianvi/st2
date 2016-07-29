# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import grp
import os
import stat

from git.repo import Repo
import yaml

from st2actions.runners.pythonrunner import Action

MANIFEST_FILE = 'pack.yaml'
PACK_RESERVE_CHARACTER = '.'

PACK_GROUP_CFG_KEY = 'pack_group'
EXCHANGE_URL_KEY = 'exchange_url'


class InitGitRepoAction(Action):
    def run(self, pack_name, abs_repo_base):
        if PACK_RESERVE_CHARACTER in pack_name:
            raise Exception('Pack name "%s" contains reserve character "%s"' %
                            (pack_name, PACK_RESERVE_CHARACTER))

        pack_path = os.path.join(abs_repo_base, pack_name)

        Repo.init(pack_path, mkdir=True)

        meta = {
            'name': pack_name
        }

        with open(os.path.join(pack_path, MANIFEST_FILE), 'w') as manifest_fp:
            yaml.dump(meta, manifest_fp)

        self._apply_pack_permissions(pack_path)

    def _apply_pack_permissions(self, pack_path):
        """
        Will recursively apply permission 770 to pack and its contents.
        """
        # -1 means don't change
        uid = -1
        gid = -1
        pack_group = self.config.get(PACK_GROUP_CFG_KEY, None)
        if pack_group:
            try:
                gid = grp.getgrnam(pack_group).gr_gid
            except KeyError:
                self.logger.warn('Group not found: %s', pack_group)
        # These mask is same as mode = 775
        mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
        os.chmod(pack_path, mode)

        # Yuck! Since os.chmod does not support chmod -R walk manually.
        for root, dirs, files in os.walk(pack_path):
            for d in dirs:
                path = os.path.join(root, d)
                os.chown(path, uid, gid)
                os.chmod(path, mode)
            for f in files:
                path = os.path.join(root, f)
                os.chown(path, uid, gid)
                os.chmod(path, mode)
