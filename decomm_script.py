i#!/usr/bin/env python

import subprocess
import time
import sys
import os
import io
import re
import requests
import json
import shlex
import datetime

def main():
 host_list = []
 disk_oo = []
 slack_msg= []
 ringsh =('/tmp/Metricly_dsoStatus')
 with open(ringsh,'r') as line:
    for line in line.readlines():
        #if 'OOS_TEMP' in line or 'OOS_SYS' in line:
        if 'OOS_TEMP' in line:
            if 'Disk:' in line:
                string = line.split()[2].strip('/')
                IP = re.findall(r"^.\d+.\d+.\d+.\d+", string)
                Disk = re.findall(r"\/(\w+\d+)", string)
                IP = IP[0]
                hostname = subprocess.Popen(['host', IP], stdout=subprocess.PIPE).stdout.read()
                host = hostname.split()[4].rstrip('.')
                OOS = line.split()[6]
                host_list.append(host)
                disk_oo.append(Disk)

 if len(host_list) == 0:
    exit()

 decomm(host_list,disk_oo)

def decomm(host_list,disk_oo):
    slack_msg= []
    host = {}
    host_dict = {}
    decomm_host = ''
    for item in host_list:
        if item in host:
            host[item] = host.get(item)+1
        else:
            host[item] = 1

    for host_name,times in host.items():
        if times >= 2:
            msg=('Multiple disks are under OOS_TEMP or OOS_SYS on the host: '+ host_name + '\n')
            slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
            result = stop_alert(host_name)
            if result == 0:
               post_to_slack(slack_msg)
            continue
        elif times <= 1:
            decomm_host = host_name
        else:
            exit()

    for key,value in zip(host_list,disk_oo):
        if key not in host_dict:
            host_dict[key]=[value]
        else:
             host_dict[key].append(value)

    if not decomm_host:
       #print("no decomm host - exit")
       exit()

    disk_number = host_dict[decomm_host][0][0].strip('disk')
    disk = host_dict[decomm_host][0][0]
    decomm_host = decomm_host.split('.')[0]
    mount_path=('/scality/disk' + disk_number)
    server_drive_file =('/var/tmp/scaldisk/' + decomm_host  + '_all_Controllers_info.txt')
    server_failed_drive =('/var/tmp/scaldisk/' + decomm_host + '_' +'disk' + disk_number + '_failed_detail.txt')
    info =('/var/tmp/scaldisk/' + decomm_host + '_' +'disk' + disk_number + '_failed_short.txt')

    msg =('The host: ' + decomm_host + '.email.comcast.net - disk error flag identified by auto decommission process: ' + disk)
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)

    ''' salt minion - ping test from salt master '''


    cmd = shlex.split('salt' + ' ' + '--out=txt ' + '\''+ decomm_host + '\''  + ' ' +  'test.ping')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()

    if 'True' not in process:
        result = stop_alert(host_name)
        if result == 0:
           msg=('Salt ping test has been failed .... Unable to continue disk ' + mount_path + ' decommission on the host' + decomm_host)
           del slack_msg[:]
           slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
           post_to_slack(slack_msg)
           exit ()
    else:
        msg=('Salt ping test has been passed.... Started decommission process of the host ' + decomm_host + ' - ' + mount_path + '\n')
        del slack_msg[:]
        slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
        post_to_slack(slack_msg)

    ''' Get device path and size '''
    command = ('\'' + 'df -h ' + ' ' + mount_path + '\'' )
    result = salt_command(command,decomm_host)
    devices = []
    for line in result.split('\n'):
       if mount_path in line:
           devices.append(line.split()[0][:-1])
           devices.append(line.split()[1][:-1])

    if not devices:
       #command = ('\'' + 'bizioctl' + ' -N disk' + disk_number  + ' -c get_mflags -a 0xefffff bizobj://RES-DOV:0' + '\'')
       command = ('\'' + 'bizioctl' + ' -N disk' + disk_number  + ' -c set_mflags -a 0x2 bizobj://RES-DOV:0' + '\'')
       salt_command(command,decomm_host)
       msg=('The host ' + decomm_host + ' - ' + disk + ' flag has been set as OOS_PERM' + '\n' +'The mount point: ' + mount_path + ' is already  unmounted' + '\n' + 'Please enter drive failed information by manually on the file: ' + info )
       del slack_msg[:]
       slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
       post_to_slack(slack_msg)
       exit ()


    ''' Get lsscsi info '''
    command = ('\'' + 'lsscsi'+ '\'')
    result = salt_command(command,decomm_host)
    lsscsi =[]
    for line in result.split('\n'):
       if devices[0] in line:
          lsscsi.append(line.split()[0])


    if os.path.exists(server_drive_file):
       os.remove(server_drive_file)

    ''' Get server HP - controller info '''

    command = ('\'' + 'dmidecode -t system' + '\'')
    result = salt_command(command,decomm_host)
    for line in result.split('\n'):
        if '	Product Name:' in line:
           hp = line
        if '	Serial Number:' in line:
           serial = line


    for i in range(1, 3):
        command = ('\'' + 'ssacli ctrl slot=' + str(i) + ' ' + 'show config detail'+ '\'')
        result = salt_command(command,decomm_host)
        f=open(server_drive_file, "a+")
        f.write(result)
        f.close()

    drive_failed = open(server_drive_file,'r')
    lines = drive_failed.readlines()
    reg = ('             Mount Points: ' + mount_path + ' ' + devices[1] + ' TB Partition Number 1\n')
    try:
        line_start=lines.index(reg)-23
        line_end=lines.index(reg)+36

        for line in lines[line_start:line_end]:
            f=open(server_failed_drive, "a+")
            f.write(line,)
            f.close()

        drive_failed.close()
    except ValueError:
        command = ('\'' + 'bizioctl' + ' -N disk' + disk_number  + ' -c set_mflags -a 0x2 bizobj://RES-DOV:0' + '\'')
        salt_command(command,decomm_host)
        time.sleep(30)
        command = ('\'' + 'umount -lf' + ' ' + mount_path +'\'')
        salt_command(command,decomm_host)
        msg=('The host ' + decomm_host + ' - ' + disk + ' flag has been set as OOS_PERM' + '\n' +'The mount point: ' + mount_path + ' is unmounted' + '\n' + 'Please enter drive failed information by manually on the file: ' + info )
        del slack_msg[:]
        slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
        post_to_slack(slack_msg)
        exit ()

    ''' disk decomm commands '''

    command = ('\'' + 'bizioctl' + ' -N disk' + disk_number  + ' -c set_mflags -a 0x2 bizobj://RES-DOV:0' + '\'')
    salt_command(command,decomm_host)
    msg=('The host ' + decomm_host + ' -  ' + disk + ' flag has been set as OOS_PERM' + '\n')
    del slack_msg[:]
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)
    time.sleep(30)

    ''' disk OS config changes '''

    command = ('\'' + 'umount -lf' + ' ' + mount_path +'\'')
    salt_command(command,decomm_host)
    msg=('Mount point ' + mount_path + ' is unmounted'+ '\n')
    del slack_msg[:]
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)

    command = ('\'' + 'echo \"1\" > ' + '/sys/class/scsi_device/' + lsscsi[0].strip('.')[1:-1] + '/device/delete' + '\'')
    result = salt_command(command,decomm_host)

    #command = ('\'' + 'echo \"scsi remove-single-device ' + lsscsi[0].strip('.')[1:-1].replace(':',' ') + '\"  > ' +  '/proc/scsi/scsi' + '\'')
    #result = salt_command(command,decomm_host)
    msg=('The host: ' + decomm_host + '.email.comcast.net - ' + disk + ' has been decomissioned'+ '\n')
    del slack_msg[:]
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)

    f=open(info,"a+")
    f.write('The host name: ' + decomm_host + '.email.comcast.net' + os.linesep)
    f.write(hp.strip() + os.linesep)
    f.write(serial.strip() + os.linesep)
    with open(server_failed_drive,'r') as line:
         for i in line:
             if 'Array' in i:
                f.write(i.strip() + os.linesep)
             if 'Logical Drive: ' in i:
                f.write(i.strip() + os.linesep)
             if 'Disk Name:' in i:
                f.write(i.strip() + os.linesep)
             if 'Number:' in i:
                f.write(i.strip() + os.linesep)
             if 'physicaldrive ' in i:
                f.write(i.strip() + os.linesep)
                bay = int(i.split()[1].split(':')[-1])
                gen = str(hp.split()[4])
                s = get_slot(bay,gen)
                f.write('Smart array Slot Number: ' + str(s) + os.linesep)
             if 'TB' in i:
                f.write(i.strip() + os.linesep)
             if 'Model:' in i:
                f.write(i.strip() + os.linesep)

    f.close()
    cmd = shlex.split('cat' + ' ' + info)
    msg = subprocess.Popen(cmd,stdout=subprocess.PIPE).communicate()[0]
    del slack_msg[:]
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)
    webhook_url = 'https://hooks.slack.com/services/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'
    slack_data = json.dumps({'text': '\n','blocks': slack_msg,'username': 'Scality Alert','icon_emoji': ':scality:'})
    proxies = {
    'http': 'http://resappdprx.email.xxx.net:3128',
    'https': 'http://resappdprx.email.xxx.net:3128'
     }
    response = requests.post(
        webhook_url, data=slack_data, proxies=proxies,
        headers={'Content-Type': 'application/json'}
    )



def get_slot(bay,gen):
    if gen == 'Gen8':
       if bay in range(1,13):
       	   return 1
       else:
	   exit()

    if gen == 'Gen9':
       if bay in range(1,26):
          return 1
       elif bay in range(65,68):
            return 1
       elif bay in range(31,54):
            return 2
       elif bay in range(59,64):
            return 2
       else:
           exit ()

    if gen == 'Gen10':
       if bay in range(1,26):
          return 1
       elif bay in range(31,56):
          return 2
       else:
           exit ()



def stop_alert(host_name):
    lock_file  =('/var/tmp/scaldisk/' + host_name  + '_slack_alert_lock.txt')
    f=open(lock_file, "a+")
    f.write(('Alerted at: ' + str(datetime.datetime.now())))
    f.write('\n')
    line_count = sum(1 for line in open(lock_file))
    if line_count >=3:
	#print 'alerted more then 3 time - stop alerting'
	return 1
    else:
	# 'send alert to slack'
        return 0
    #if line_count >=20:
	#print 'remove file'
        #os.remove(lock_file)
    f.close()

def salt_command(command,decomm_host):
    cmd = shlex.split('salt' + ' ' + '\''+ decomm_host + '\''  + ' ' +  'cmd.run' + ' ' + command)
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return (result)

def post_to_slack(message):
    webhook_url = 'https://hooks.slack.com/services/'
    #webhook_url = 'https://hooks.slack.com/services/'
    slack_data = json.dumps({'text': '\n','blocks': message,'username': 'Scality Alert','icon_emoji': ':scality:'})
    proxies = {
    'http': 'http://resappdprx.email.comcast.net:3128',
    'https': 'http://resappdprx.email.comcast.net:3128'
     }
    slack_data = json.dumps({'blocks': message,'username': 'Scality Alert','icon_emoji': ':scality:'})
    response = requests.post(
        webhook_url, data=slack_data, proxies=proxies,
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )

if __name__ == "__main__":
   main()
