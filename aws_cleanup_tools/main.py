#!/usr/bin/env python3
import argparse

import tabulate
from boto3_wrapper.boto_session import SessionWrapper as BotoSession
from aws_cleanup_tools.orphan_finder import resource_finder


def check_result(unused, used):
    unused_id = {i['id'] for i in unused}
    used_id = {i['id'] for i in used}

    assert not unused_id.intersection(used_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Show the diff between a stack and it's resources")
    parser.add_argument('-p', '--aws-profile', default='default',
                        help='The aws profile name (use the default one if not found)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='show only the id instead of the humain output')
    parser.add_argument('-v', '--invert-match', action='store_true',
                        help='show the resources that are being used instead of the one we can clean')
    parser.add_argument('resource_type', nargs='?', default=None, choices=resource_finder.keys(),
                        help='specify a resource type to check the usage of, printing the ones that are not used')

    args = parser.parse_args()

    boto_session = BotoSession(profile_name=args.aws_profile)

    fct = resource_finder[args.resource_type]
    unused, used = fct(boto_session)
    unused, used = list(unused), list(used)
    check_result(unused, used)

    to_show = unused if not args.invert_match else used

    if args.quiet:
        for e in to_show:
            print(e['id'])
    else:
        print(tabulate.tabulate(to_show))
