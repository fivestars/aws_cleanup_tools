#!/usr/bin/env python3
from pprint import pprint

import sys


def get_unused_security_groups(session):
    all_sg = {sg['GroupId']: sg for sg in session.ec2.describe_security_groups()}
    sgname2id = {sg['GroupName']: sg['GroupId'] for sg in all_sg.values()}
    sgname2id['amazon-elb-sg'] = 0
    used_sg = set()

    # remove the ones that are in cloudformation
    for group_id, sg in list(all_sg.items()):
        if [t for t in sg.get('Tags', []) if t['Key'] == 'aws:cloudformation:stack-name']:
            used_sg.add(group_id)

    # check the one used by instances
    instance_sg = set()
    for reservations in session.ec2.describe_instances():
        used_sg.update({sg['GroupName'] for sg in reservations['Groups']})
        used_sg.update({sg['GroupId']
                            for i in reservations['Instances']
                            for ni in i['NetworkInterfaces']
                            for sg in ni['Groups']
                            })

    # check the one used by load balancers
    for elb in session.elb.describe_load_balancers():
        used_sg.add(sgname2id[elb['SourceSecurityGroup']['GroupName']])
        used_sg.update(elb['SecurityGroups'])

    # launch configuration
    # for lc in session.asg.describe_launch_configurations():
    #     print(lc['SecurityGroups'])

    unused = set(all_sg.keys()) - used_sg
    return [
        {
            'id': sg_id,
            'name': all_sg[sg_id]['GroupName'],
        }
        for sg_id in sorted(unused)
    ]
