#!/usr/bin/env python3
from aws_cleanup_tools import ec2


resource_finder = {
    'ec2.securitygroup': ec2.get_unused_security_groups,
    'ec2.keypairs': ec2.get_unused_key_pairs,
}


