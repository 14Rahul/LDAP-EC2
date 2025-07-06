import json
import boto3
import time


def lambda_handler(event, context):
    ldap_access = event.get('ldap_access', [])
    
    for access in ldap_access:
    
        instances = access.get('instances', [])
        tag_key = access.get('key', '')
        tag_value = access.get('value', '')
        permissions = access.get('permissions', [])
        regions = access.get('regions', []) 
        notification_arns = {
            'us-east-2': 'arn:aws:sns:us-east-2:<Account ID>:CloudWatch_Alarms_Topic'
         }
        
        formatted_permissions = []
        
        for perm in permissions:
            ad_user = perm['ad_user']
            m_user = perm['m_user']
            if m_user == 'ALL':
                formatted_permissions.append(f'%{ad_user}@directory.example.com ALL=(ALL) NOPASSWD: ALL')
            else:
                formatted_permissions.append(f'%{ad_user}@directory.example.com ALL=(ALL:ALL) NOPASSWD: /usr/bin/su - {m_user}')
                
        
            
        for r in regions:
            try:
                ssm_client = boto3.client('ssm', region_name=r)
                ec2 = boto3.client('ec2', region_name=r)
                
                if r in notification_arns:
                    notification_arn = notification_arns[r]
        
                if instances:
                   
                    for i in instances:
                        try:
                            ssm_response = ssm_client.send_command(
                                            InstanceIds=[i],
                                            DocumentName="AWS-RunShellScript",
                                            Parameters={'commands': ['sudo cat /etc/sudoers | grep directory.example.com']},
                                            )
                            command_id = ssm_response['Command']['CommandId']
                            time.sleep(2)                               
                            #Remove Permission
                            try:  
                                output = ssm_client.get_command_invocation(
                                    CommandId=command_id,
                                    InstanceId=i,
                                    )
                                sudoers_data = output['StandardOutputContent']
                                sudoers_data_lines = sudoers_data.splitlines()
                                permission_added = False
                                sudoers_permission = []
                                for rmline in sudoers_data_lines:
                                    sudoers_permission.append(rmline.strip())
                                rm_permission = list(set(sudoers_permission).difference(formatted_permissions))
            
                                if rm_permission:
                                    for rm in rm_permission:
                                        print("Removing Permission to Instance" + i)
                                        rm_scape = rm.replace('\\', r'\\').replace('.', r'\.').replace('/', r'\/')
                                        ssm_client.send_command(
                                                    InstanceIds=[ i ],
                                                    DocumentName="AWS-RunShellScript",
                                                    Parameters={'commands': ['sed -i ' +"'/"+rm_scape+"/d'" + ' /etc/sudoers']},
                                                    ServiceRoleArn='arn:aws:iam::<Account ID>:role/Ldap-Run-Command-Service_Role',
                                                    NotificationConfig={
                                                        'NotificationArn': notification_arn,
                                                        'NotificationEvents': [
                                                            'TimedOut','Cancelled','Failed',
                                                        ],
                                                        'NotificationType': 'Command'
                                                    },
                                                    )
                            
                            except Exception as e:
                                print(f"Instance is in stopped state {i}: {e}")  
        
        
                            for p in formatted_permissions:
                                try:  
                                    output = ssm_client.get_command_invocation(
                                        CommandId=command_id,
                                        InstanceId=i,
                                        )
                                    sudoers_data = output['StandardOutputContent']
                                    sudoers_data_lines = sudoers_data.splitlines()
                                    permission_added = False
                                    for line in sudoers_data_lines:
                                        if line.strip() == p:
                                            print("Instance " + i + " Already Conatains Permission")
                                            permission_added = True
                                            break
                                    if not permission_added:
                                        print("Adding Permission to Instance" + i)
                                        ssm_client.send_command(
                                                    InstanceIds=[ i ],
                                                    DocumentName="AWS-RunShellScript",
                                                    Parameters={'commands': ['echo ' +"'"+p+"'" + ' >> /etc/sudoers', 'su_path=$(which su)', 'sed -i "s|/usr/bin/su|${su_path}|g" /etc/sudoers']},
                                                    ServiceRoleArn='arn:aws:iam::<Account ID>:role/Ldap-Run-Command-Service_Role',
                                                    NotificationConfig={
                                                        'NotificationArn': notification_arn,
                                                        'NotificationEvents': [
                                                            'TimedOut','Cancelled','Failed',
                                                        ],
                                                        'NotificationType': 'Command'
                                                    },
                                                    )
                                
                                except Exception as e:
                                    print(f"Instance is in stopped state {i}: {e}")
                        except Exception as e:
                            print(f"Instance is in stopped state {i}: {e}")
                    
        
          
        
                else:
                    ssmresponse = ssm_client.send_command(
                                Targets=[
                                    {
                                        'Key': f'tag:{tag_key}',
                                        'Values': [
                                            tag_value,
                                        ]
                                    },
                                ],
                                DocumentName="AWS-RunShellScript",
                                Parameters={'commands': ['sudo cat /etc/sudoers | grep directory.example.com]}, )
        
                    command_id = ssmresponse['Command']['CommandId']
        
                    response = ec2.describe_instances(
                        Filters=[
                            {
                                'Name': f'tag:{tag_key}',
                                'Values': [tag_value]
                            }
                        ]
                    )
        
                    instance_ids = []
                    #insatnce_state = []
                    for reservation in response['Reservations']:
                        for instance in reservation['Instances']:
                            instance_ids.append(instance['InstanceId'])
                            #insatnce_state.append(instance['State']['Name'])
        
                    time.sleep(5)
        
                    for p in formatted_permissions:
                        for i in instance_ids:
                            try:  
                                output = ssm_client.get_command_invocation(
                                    CommandId=command_id,
                                    InstanceId=i,
                                    )
                                sudoers_data = output['StandardOutputContent']
                                sudoers_data_lines = sudoers_data.splitlines()
                                permission_added = False
                                for line in sudoers_data_lines:
                                    if line.strip() == p:
                                        print("Instance " + i + " Already Conatains Permission")
                                        permission_added = True
                                        break
                                if not permission_added:
                                    print("Adding Permission to Instance" + i)
                                    ssm_client.send_command(
                                                InstanceIds=[ i ],
                                                DocumentName="AWS-RunShellScript",
                                                Parameters={'commands': ['echo ' +"'"+p+"'" + ' >> /etc/sudoers']},
                                                ServiceRoleArn='arn:aws:iam::<Account ID>:role/Ldap-Run-Command-Service_Role',
                                                NotificationConfig={
                                                        'NotificationArn': notification_arn,
                                                        'NotificationEvents': [
                                                            'TimedOut','Cancelled','Failed',
                                                        ],
                                                        'NotificationType': 'Command'
                                                    },
                                                )
                            
                            except Exception as e:
                                print(f"Instance is in stopped state {i}: {e}")
        
                    #Remove Permission
                    for i in instance_ids:
                        try:  
                            output = ssm_client.get_command_invocation(
                                CommandId=command_id,
                                InstanceId=i,
                                )
                            sudoers_data = output['StandardOutputContent']
                            sudoers_data_lines = sudoers_data.splitlines()
                            permission_added = False
                            sudoers_permission = []
                            for rmline in sudoers_data_lines:
                                sudoers_permission.append(rmline.strip())
                            rm_permission = list(set(sudoers_permission).difference(formatted_permissions))
        
                            if rm_permission:
                                for rm in rm_permission:
                                    print("Removing Permission to Instance" + i)
                                    rm_scape = rm.replace('\\', r'\\').replace('.', r'\.').replace('/', r'\/')
                                    ssm_client.send_command(
                                                InstanceIds=[ i ],
                                                DocumentName="AWS-RunShellScript",
                                                Parameters={'commands': ['sed -i ' +"'/"+rm_scape+"/d'" + ' /etc/sudoers']},
                                                ServiceRoleArn='arn:aws:iam::<Account ID>:role/Ldap-Run-Command-Service_Role',
                                                NotificationConfig={
                                                        'NotificationArn': notification_arn,
                                                        'NotificationEvents': [
                                                            'TimedOut','Cancelled','Failed',
                                                        ],
                                                        'NotificationType': 'Command'
                                                    },
                                                )
                        
                        except Exception as e:
                            print(f"Instance is in stopped state {i}: {e}")
            except Exception as e:
                print(f"{e}")
