#!/usr/local/sbin/charm-env python3

# Copyright 2020 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import sys

# Load modules from $CHARM_DIR/lib
sys.path.append('lib')

from charms.layer import basic
basic.bootstrap_charm_deps()
basic.init_config_states()

import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv
from charms.layer.magpie_tools import check_nodes, safe_status, Iperf, Lldp

IPERF_BASE_PORT = 5001

def listen(*args):
    action_config = hookenv.action_get()
    cidr = action_config.get('network-cidr')
    listner_count = action_config.get('listner-count') or 1
    magpie = reactive.relations.endpoint_from_flag('magpie.joined')
    iperf = Iperf()
    for port in range(IPERF_BASE_PORT, IPERF_BASE_PORT + int(listner_count)):
        iperf.listen(cidr=cidr, port=port)
    magpie.set_iperf_server_ready()
    reactive.set_state('iperf.listening')

def advertise(*args):
    magpie = reactive.relations.endpoint_from_flag('magpie.joined')
    magpie.advertise_addresses()

def run_iperf(*args):
    action_config = hookenv.action_get()
    config = hookenv.config()
    cidr = action_config.get('network-cidr')
    units = action_config.get('units', '').split()
    magpie = reactive.relations.endpoint_from_flag('magpie.joined')
    push_gateway = config['push-gateway']
    if push_gateway:
        push_gateway = 'http://{}:9091'.format(push_gateway)
    nodes = {ip: name
             for name, ip in magpie.get_nodes(cidr=cidr)
             if not units or name in units}
    iperf = Iperf()
    results = iperf.batch_hostcheck(
        nodes,
        action_config.get('total-run-time'),
        action_config.get('iperf-batch-time'),
        [int(i) for i in action_config.get('concurrency-progression').split()],
        push_gateway=push_gateway,
        tag=action_config.get('tag'))
    hookenv.action_set({
        "output": json.dumps(results)})
#
# Actions to function mapping, to allow for illegal python action names that
# can map to a python function.
ACTIONS = {
    "listen": listen,
    "advertise": advertise,
    "run-iperf": run_iperf,
}


def main(args):
    action_name = os.path.basename(args[0])
    action = ACTIONS[action_name]
    action(args)

#    action_name = os.path.basename(args[0])
#    try:
#        action = ACTIONS[action_name]
#    except KeyError:
#        return "Action %s undefined" % action_name
#    else:
#        try:
#            action(args)
#        except Exception as e:
#            hookenv.action_fail(str(e))


if __name__ == "__main__":
    sys.exit(main(sys.argv))


