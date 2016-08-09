#!/usr/bin/env python3
from aws_cleanup_tools import ec2


resource_finder = {
    'ec2.securitygroup': ec2.get_unused_security_groups,
    'ec2.keypair': ec2.get_unused_key_pairs,
    'ec2.instance': ec2.get_unused_instances,
}


