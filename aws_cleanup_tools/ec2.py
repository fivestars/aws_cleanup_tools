#!/usr/bin/env python3
from pprint import pprint

import sys


def get_unused_security_groups(session):
    # The security group are region dependent, no need to search outside the region
    all_sg = {sg['GroupId']: sg for sg in session.ec2.describe_security_groups()}
    name2id = {sg['GroupName']: sg['GroupId'] for sg in all_sg.values()}
    name2id['amazon-elb-sg'] = 0
    name2id.update({k:k for k in all_sg.keys()})
    used_sg = set()

    # remove the ones that are in cloudformation
    for group_id, sg in list(all_sg.items()):
        if [t for t in sg.get('Tags', []) if t['Key'] == 'aws:cloudformation:stack-name']:
            used_sg.add(group_id)

    # check the one used by instances
    for reservations in session.ec2.describe_instances():
        used_sg.update({sg['GroupName'] for sg in reservations['Groups']})
        used_sg.update({sg['GroupId']
                            for i in reservations['Instances']
                            for ni in i['NetworkInterfaces']
                            for sg in ni['Groups']
                            })

    # check the one used by load balancers
    for elb in session.elb.describe_load_balancers():
        used_sg.add(name2id[elb['SourceSecurityGroup']['GroupName']])
        used_sg.update(elb['SecurityGroups'])

    # launch configuration
    for lc in session.asg.describe_launch_configurations():
        used_sg.update(map(name2id.get, lc['SecurityGroups']))

    # Elasticache security groups
    for elcsg in session.elasticache.describe_cache_security_groups():
        used_sg.update(name2id.get(ec2sg['EC2SecurityGroupName']) for ec2sg in elcsg['EC2SecurityGroups'])

    unused = set(all_sg.keys()) - used_sg
    return sorted([
        {
            'id': sg_id,
            'name': all_sg[sg_id]['GroupName'],
        }
        for sg_id in unused
    ], key=lambda e: e['name'])


def get_unused_key_pairs(session):

    # get all key_pairs
    all_kp = [kp['KeyName'] for kp in session.ec2.describe_key_pairs()]
    used_kp = set()

    print(all_kp)

    # Instances
    for reservations in session.ec2.describe_instances():
        used_kp.update({i['KeyName']
                        for i in reservations['Instances']
                        })

    # Launch configuration
    for lc in session.asg.describe_launch_configurations():
        used_kp.add(lc['KeyName'])

    print(used_kp)

    unused = set(all_kp) - used_kp
    return sorted([
        {
            'id': kp
        }
        for kp in unused
    ], key=lambda e: e['id'])


