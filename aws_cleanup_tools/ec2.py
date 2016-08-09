#!/usr/bin/env python3
from itertools import chain
from pprint import pprint

import sys


def tags_get(tags, name, default=None):
    for tag in tags or []:
        if tag['Key'] == name:
            return tag['Value']
    return default


def get_unused_security_groups(session):
    # The security group are region dependent, no need to search outside the region
    all_sg = {sg['GroupId']: sg for sg in session.ec2.describe_security_groups()}
    name2id = {sg['GroupName']: sg['GroupId'] for sg in all_sg.values()}
    name2id['amazon-elb-sg'] = 0
    name2id.update({k: k for k in all_sg.keys()})
    used_sg = set()

    # remove the ones that are in cloudformation
    for group_id, sg in list(all_sg.items()):
        if not tags_get(sg.get('Tags', []), 'aws:cloudformation:stack-name'):
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


def get_unused_instances(session):
    # An unused instance is very vague, so we just are getting
    all_instances = list(chain(*[r['Instances'] for r in session.ec2.describe_instances()]))
    all_id = [i['InstanceId'] for i in all_instances]
    used_ec2 = set()

    # Instance in stack are used
    for i in all_instances:
        if [t for t in i.get('Tags', []) if t['Key'] == 'aws:cloudformation:stack-name']:
            used_ec2.add(i['InstanceId'])

    # Instance in a asg is used
    for i in session.asg.describe_auto_scaling_instances():
        used_ec2.add(i['InstanceId'])

    # From what's left, remove instance that are stopped
    stopped_instance = {i['InstanceId'] for i in all_instances if i['State']['Name'] in ['stopped']}

    # We also want to clean instances that have no names
    unnamed_instances = {i['InstanceId'] for i in all_instances if not tags_get(i.get('Tags'), 'Name')}

    # Maybe we can add more instance (more than 30days old ones for examples)

    all_unused = stopped_instance.union(unnamed_instances) - used_ec2
    return sorted([
                      {
                          'id': i['InstanceId'],
                          'name': tags_get(i.get('Tags'), 'Name', '<no name>')
                      }
                      for i in all_instances if i['InstanceId'] in all_unused
                      ], key=lambda e: e['name'])


def get_unused_images(session):
    # We only look for available images
    all_ami = [i for i in session.ec2.describe_images(Owners=['self']) if i['State'] == 'available']
    all_ami_id = {i['ImageId'] for i in all_ami}
    used_images = set()

    # instance ami
    all_instances = list(chain(*[r['Instances'] for r in session.ec2.describe_instances()]))
    for i in all_instances:
        used_images.add(i['ImageId'])

    # launch configuration
    for lc in session.asg.describe_launch_configurations():
        used_images.add(lc['ImageId'])

    unused_images = all_ami_id - used_images
    print(unused_images)

    # cloud formation ?
    return sorted([
                      {
                          'id': i['ImageId'],
                          'name': i['Name'],
                          'date': i['CreationDate'],
                      }
                      for i in all_ami if i['ImageId'] in unused_images
                      ], key=lambda e: (e['date']))
