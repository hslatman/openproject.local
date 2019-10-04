from collections import namedtuple

from dotenv import load_dotenv
from pathlib import Path 

import argparse
import datetime
import json
#import openpyxl
import os
import requests
import xlrd

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

url = os.getenv('OP_HOST')
user = 'apikey'
password = os.getenv('OP_APIKEY')

WorkPackage = namedtuple("WorkPackage", "id subject type status assignee priority start_date finish_date parent author accountable updated_on category version estimated_time progress")
WorkPackageRelation = namedtuple("WorkPackageRelation", "rfrom rto rtype")

def isFloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def post_work_package(payload):

    headers = {'Content-Type': 'application/json'}
    post_work_packages_url = url + '/projects/'+str(project_id)+'/work_packages?notify=false'
    response = requests.post(post_work_packages_url, data=json.dumps(payload), headers=headers, auth=requests.auth.HTTPBasicAuth(user, password))

    return response.status_code, response.text

def process_work_package(users, versions, wp_id, work_package, work_package_relations, old_wp_id_to_new_wp_relation_link):

    assignee = users[work_package.assignee] if work_package.assignee in users.keys() else None
    accountable = users[work_package.accountable] if work_package.accountable in users.keys() else None
    version = versions[work_package.version] if work_package.version in versions.keys() else None

    payload = {
        'subject': work_package.subject,
        'percentageDone': work_package.progress,
        #'estimatedTime': 11,
        '_links': {
            'type': {
                'href': '/api/v3/types/' + str(types[work_package.type]),
            },
            'status': {
                'href': '/api/v3/statuses/' + str(statuses[work_package.status]),
            },
            # 'author': {
            #     'href': '/api/v3/users/' + str(users[v.author]),
            # },
            'priority': {
                'href': '/api/v3/priorities/' + str(priorities[work_package.priority]),
            },
        }
    }

    # if assignee:
    #     payload['_links']['assignee'] = {'href': '/api/v3/users/' + str(assignee)}
    
    # if accountable:
    #     payload['_links']['responsible'] = {'href': '/api/v3/users/' + str(accountable)}

    if version:
        payload['_links']['version'] = {'href': '/api/v3/versions/' + str(version)}

    is_parent_like = wp_id in parents
    if not is_parent_like:
        if work_package.start_date:
            payload['startDate'] = work_package.start_date.strftime("%Y-%m-%d")

        if work_package.finish_date:
            payload['dueDate'] = work_package.finish_date.strftime("%Y-%m-%d")

    if wp_id in work_package_relations.keys():
        relations_for_work_package = work_package_relations[wp_id]
        for relation in relations_for_work_package:
            if relation.rtype == 'child of':
                link = old_wp_id_to_new_wp_relation_link[relation.rto]['href']
                payload['_links']['parent'] = {'href': link}

            # TODO: other types of relations, such as 'Precedes', and 'Follows'?

    return payload


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Import WorkPackages from XLS into OpenProject.')
    parser.add_argument('project', type=str, help='The textual identifier of the project')
    parser.add_argument('file', type=str, help='The XLS file to import')
    args = parser.parse_args()

    #project_filter = 'some-project-name'
    #projects_url = url + '/projects?filters=[{"ancestor": {"operator": "=", "values": ["1"]}"}]'
    #print(project_response.text)

    projects_url = url + '/projects'
    projects_response = requests.get(projects_url, auth=requests.auth.HTTPBasicAuth(user, password))

    body = json.loads(projects_response.text)
    if body['count'] <= 0:
        print('No projects found!')
        exit()
    
    project_identifier = args.project
    project_id = None
    for item in body['_embedded']['elements']:
        if item['identifier'] == project_identifier:
            project_id = item['id']

    if project_id == None:
        print(f"No project found with identifier: {project_identifier}")
        exit()


    get_types_by_project_url = url + '/projects/'+str(project_id)+'/types/'
    get_types_by_project_response = requests.get(get_types_by_project_url, auth=requests.auth.HTTPBasicAuth(user, password))


    types = {}
    body = json.loads(get_types_by_project_response.text)
    for item in body['_embedded']['elements']:
        type_id = item['id']
        type_name = item['name']
        types[type_name] = type_id 


    get_statuses_url = url + '/statuses/'
    get_statuses_response = requests.get(get_statuses_url, auth=requests.auth.HTTPBasicAuth(user, password))
    statuses = {}
    body = json.loads(get_statuses_response.text)
    for item in body['_embedded']['elements']:
        status_id = item['id']
        status_name = item['name']
        statuses[status_name] = status_id 


    get_users_url = url + '/users'
    get_users_response = requests.get(get_users_url, auth=requests.auth.HTTPBasicAuth(user, password))
    users = {}
    body = json.loads(get_users_response.text)
    for item in body['_embedded']['elements']:
        user_id = item['id']
        user_name = item['name']
        users[user_name] = user_id


    get_categories_by_project_url = url + '/projects/'+str(project_id)+'/categories'
    get_categories_by_project_response = requests.get(get_categories_by_project_url, auth=requests.auth.HTTPBasicAuth(user, password))
    categories = {}
    body = json.loads(get_categories_by_project_response.text)
    for item in body['_embedded']['elements']:
        category_id = item['id']
        category_name = item['name']
        categories[category_name] = category_id


    get_versions_by_project_url = url + '/projects/'+str(project_id)+'/versions'
    get_versions_by_project_response = requests.get(get_versions_by_project_url, auth=requests.auth.HTTPBasicAuth(user, password))
    versions = {}
    body = json.loads(get_versions_by_project_response.text)
    for item in body['_embedded']['elements']:
        version_id = item['id']
        version_name = item['name']
        versions[version_name] = version_id


    get_priorities_url = url + '/priorities'
    get_priorities_response = requests.get(get_priorities_url, auth=requests.auth.HTTPBasicAuth(user, password))
    priorities = {}
    body = json.loads(get_priorities_response.text)
    for item in body['_embedded']['elements']:
        priority_id = item['id']
        priority_name = item['name']
        priorities[priority_name] = priority_id


    get_work_packages_by_project_url = url + '/projects/'+str(project_id)+'/work_packages'
    get_work_packages_by_project_response = requests.get(get_work_packages_by_project_url, auth=requests.auth.HTTPBasicAuth(user, password))


    body = json.loads(get_work_packages_by_project_response.text)
    total_work_packages_for_project = body['total']
    print(f'Found {total_work_packages_for_project} (open?) WorkPackages for the project with identifier {project_identifier}')

    # TODO: don't import when existing work packages exist? And/or provide option to override that?
    
    filename = args.file
    wb = xlrd.open_workbook(filename) #openpyxl.load_workbook(filename)
    work_package_sheet = wb.sheet_by_name('Work packages') # NOTE: the default name when exporting a CSF from OpenProject

    columns = [
        '',
        'Type',
        'ID',
        'Subject',
        'Status',
        'Assignee',
        'Priority',
        'Start date',
        'Finish data',
        'Parent',
        'Author',
        'Accountable',
        'Updated on',
        'Category',
        'Version',
        'Estimated time',
        'Progress (%)',
        '',
        'Relation type',
        'Delay',
        'Description',
        'ID',
        'Type',
        'Subject'
    ]

    mapping = {k: v for (k, v) in enumerate(columns)} 

    header = work_package_sheet.row(1)

    work_packages = {}
    work_package_relations = {}
    num_cols = work_package_sheet.ncols
    for row_idx in range(2, work_package_sheet.nrows):

        wp_type = work_package_sheet.cell(row_idx, 1).value
        wp_id = int(work_package_sheet.cell(row_idx, 2).value)
        wp_subject = work_package_sheet.cell(row_idx, 3).value
        wp_status = work_package_sheet.cell(row_idx, 4).value
        wp_assignee = work_package_sheet.cell(row_idx, 5).value
        wp_priority = work_package_sheet.cell(row_idx, 6).value

        wp_start_date = work_package_sheet.cell(row_idx, 7).value
        if isFloat(wp_start_date):
            wp_start_date = xlrd.xldate_as_datetime(wp_start_date, wb.datemode)
        else: 
            wp_start_date = None

        wp_finish_date = work_package_sheet.cell(row_idx, 8).value
        if isFloat(wp_finish_date):
            wp_finish_date = xlrd.xldate_as_datetime(wp_finish_date, wb.datemode)
        else:
            wp_finish_date = None

        wp_parent = work_package_sheet.cell(row_idx, 9).value
        wp_author = work_package_sheet.cell(row_idx, 10).value
        wp_accountable = work_package_sheet.cell(row_idx, 11).value

        wp_updated_on = work_package_sheet.cell(row_idx, 12).value
        if isFloat(wp_updated_on):
            wp_updated_on = xlrd.xldate_as_datetime(wp_updated_on, wb.datemode)
        else:
            wp_updated_on = None

        wp_category = work_package_sheet.cell(row_idx, 13).value
        wp_version = work_package_sheet.cell(row_idx, 14).value
        wp_estimated_time = work_package_sheet.cell(row_idx, 15).value
        wp_progress = int(work_package_sheet.cell(row_idx, 16).value)

        work_package = WorkPackage(wp_id, wp_subject, wp_type, wp_status, wp_assignee, wp_priority, 
                                    wp_start_date, wp_finish_date, wp_parent, wp_author, wp_accountable,
                                    wp_updated_on, wp_category, wp_version, wp_estimated_time, wp_progress)
        work_packages[wp_id] = work_package # Potential doubles, due to relations, will be overridden


        # Do some relation housekeeping
        if wp_id not in work_package_relations.keys():
            work_package_relations[wp_id] = []

        relation_to = work_package_sheet.cell(row_idx, 21).value
        if relation_to != '' and (isFloat(relation_to) or str(relation_to).isnumeric()):
            relation_to = int(relation_to)
        else:
            relation_to = None

        relation_type = work_package_sheet.cell(row_idx, 18).value

        if relation_to != None and relation_type != '':
            wp_relation = WorkPackageRelation(wp_id, relation_to, relation_type)
            work_package_relations[wp_id].append(wp_relation)


    parents = []
    for wp_id, relations in work_package_relations.items():
        for relation in relations:
            if relation.rtype == 'parent of': # NOTE: we're not determining the right hierarchical parent/child yet.
                parents.append(wp_id)

    parents = list(set(parents))

    processed_wp_ids = []
    number_of_imported_work_packages = 0
    old_wp_id_to_new_wp_relation_link = {}

    for wp_id in parents:
        payload = process_work_package(users, versions, wp_id, work_packages[wp_id], work_package_relations, old_wp_id_to_new_wp_relation_link)
        status, response = post_work_package(payload)
        if status != 201:
            print(response)
        else:
            number_of_imported_work_packages += 1
            processed_wp_ids.append(wp_id)
            data = json.loads(response)
            old_wp_id_to_new_wp_relation_link[wp_id] = data['_links']['self']


    for wp_id, work_package in work_packages.items():
        
        if wp_id in processed_wp_ids:
            continue # skip the current wp_id; it was already processed

        payload = process_work_package(users, versions, wp_id, work_package, work_package_relations, old_wp_id_to_new_wp_relation_link)
        status, response = post_work_package(payload)
        if status != 201:
            print(response)
        else:
            number_of_imported_work_packages += 1
            processed_wp_ids.append(wp_id)
    
    number_of_skipped_work_packages = len(work_packages) - number_of_imported_work_packages
    if number_of_skipped_work_packages != 0:
        print(f"Skipped {number_of_skipped_work_packages}!")


    # Date - refers to an ISO 8601 date, e.g. “2014-05-21”
    # DateTime - refers to an ISO 8601 combined date and time, e.g. “2014-05-21T13:37:00Z”
    # Duration - refers to an ISO 8601 duration, e.g. “P1DT18H”
    
    # NOTE: Author is determined by APIKEY! Perhaps we can change it, though...
    # print(str(versions['Version 0.3.0']))
    # payload = {
    #     'subject': 'TEST',
    #     'percentageDone': 81,
    #     'startDate': datetime.datetime.now().strftime("%Y-%m-%d"),
    #     'dueDate': datetime.datetime.now().strftime("%Y-%m-%d"),
    #     #'estimatedTime': 11,
    #     '_links': {
    #         'type': {
    #             'href': '/api/v3/types/' + str(types['Epic']),
    #         },
    #         'status': {
    #             'href': '/api/v3/statuses/' + str(statuses['In progress']),
    #         },
    #         'author': {
    #             'href': '/api/v3/users/' + str(users['OpenProject Admin']),
    #         },
    #         # 'assignee': {
    #         #     'href': '/api/v3/users/' + str(users['OpenProject Admin']),
    #         # },
    #         # 'responsible': {
    #         #     'href': '/api/v3/users/' + str(users['OpenProject Admin']),
    #         # }
    #         'priority': {
    #             'href': '/api/v3/priorities/' + str(priorities['High']),
    #         },
    #         'version': {
    #             'href': '/api/v3/versions/' + str(versions['Version 0.3.0']),
    #         }
    #     }
    # }
    # headers = {'Content-Type': 'application/json'}
    # post_work_packages_url = url + '/projects/'+str(project_id)+'/work_packages?notify=false'
    # response = requests.post(post_work_packages_url, data=json.dumps(payload), headers=headers, auth=requests.auth.HTTPBasicAuth(user, password))

    # print(response)
    # print(response.text)