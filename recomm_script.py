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
 disk_oo_perm = []
 slack_msg= []
 ringsh =('/tmp/Metricly_dsoStatus')
 with open(ringsh,'r') as line:
    for line in line.readlines():
        if 'OOS_PERM' in line:
           if 'Disk:' in line:
               string = line.split()[2].strip('/')
               IP = re.findall(r"^.\d+.\d+.\d+.\d+", string)
               Disk = re.findall(r"\/(\w+\d+)", string)
               IP = IP[0]
               hostname = subprocess.Popen(['host', IP], stdout=subprocess.PIPE).stdout.read()
               host = hostname.split()[4].rstrip('.')
               OOS = line.split()[6]
               recomm_host = host.split('.')[0]
               recomm_disk = Disk[0]
               disk_number = Disk[0].split('disk')[1]
               file = ('/var/tmp/scaldisk/' + recomm_host + '_' +'disk' + disk_number + '_failed_short.txt')
               if os.path.isfile(file):
                  recomm(recomm_host,recomm_disk,ringsh)

 log_cleanup()

def recomm(recomm_host,recomm_disk,ringsh):
    slack_msg= []
    mount_path=('/scality/disk' + recomm_disk.split('disk')[1])
    with open(('/var/tmp/scaldisk/' + recomm_host + '_' + recomm_disk + '_failed_short.txt'),'r') as line:
       for line in line.readlines():
           if 'Serial Number:' in line:
               #print line
               disk_serial_nu = line.split()[2]
           if 'physicaldrive' in line:
               physical_drive = line.split()[1]
           if 'Smart' in line:
               slot = line.split()[4]
           if 'Logical Drive:' in line:
               logical_drive = line.split()[2]

    ''' salt minion - ping test from salt master '''


    cmd = shlex.split('salt' + ' ' + '--out txt ' + '\''+ recomm_host + '\''  + ' ' +  'test.ping')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()

    if 'True' not in process:
        result = stop_alert(recomm_host)
        if result == 0:
           msg=('Salt ping test has been failed .... Unable to continue disk ' + mount_path + ' auto recommission on the host' + recomm_host)
           del slack_msg[:]
           slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
           post_to_slack(slack_msg)
           exit ()
    else:
        msg=('Salt ping test has been passed.... Started recommission process of the host ' + recomm_host + ' - ' + mount_path + '\n')
        del slack_msg[:]
        #slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
        #post_to_slack(slack_msg)


    ''' fetch the serial number '''
    command = ('\'' + 'ssacli ctrl slot=' + slot + ' ' + ' pd '+ physical_drive + ' show detail' + '\'')
    result = salt_command(command,recomm_host)
    for line in result.split('\n'):
        if '             Serial Number:' in line:
            new_disk_serial = line.split()[2]
            if disk_serial_nu == new_disk_serial:
               exit() #Drive replacement not done

    msg =('The host: ' + recomm_host + '.email.comcast.net: ' + recomm_disk + ' has been replaced by vendor and identified by auto recommission process: ' )
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)

    ''' Validate pysical drive looks good '''
    for line in result.split('\n'):
        if '             Status:' in line:
            status = line.split()[1]

    if status != "OK":
       msg =('Replaced physical ' + physical_drive +  ' S/N: ' + new_disk_serial + ' disk health status not OK ')
       del slack_msg[:]
       slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
       post_to_slack(slack_msg)

    ''' Check the server status in the ring '''
    with open(ringsh,'r') as line:
         for i in line.readlines():
             if recomm_host in i:
                state = i.split()[4].split(',')[0]
                if state != 'RUN':
                   msg =('The host ' + recomm_host + ' nodes are not in Run state .. wait until nodes in Run state')
                   del slack_msg[:]
                   slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
                   post_to_slack(slack_msg)
                   exit()


    ''' Run HP commands '''
    file1 = ('/var/tmp/scaldisk/' + recomm_host + '_' + recomm_disk + '_failed_short.txt')
    inpro = ('/var/tmp/scaldisk/' + recomm_host + '_' + recomm_disk + '_recomm_inprocess.txt')
    os.rename(file1,inpro)
    command = ('\'' + 'ssacli ctrl slot=' + slot + ' ' + 'ld ' + logical_drive + ' delete forced' + '\'')
    result = salt_command(command,recomm_host)
    command = ('\'' + 'ssacli ctrl slot=' + slot + ' ' + 'create type=ld drives=' + physical_drive + ' raid=0 forced' + '\'')
    result = salt_command(command,recomm_host)
    command = ('\'' + 'ssacli ctrl slot=' + slot + ' ' + 'show config detail | egrep "physicaldrive|Disk Name" | grep -v port |grep -C 1 '+ physical_drive + ' | head -1' +'\'')
    result = salt_command(command,recomm_host)
    for line in result.split('\n'):
        if '             Disk Name:' in line:
            new_path = line.split()[2]
    command = ('\'' + '/usr/bin/scaldisk replace -d ' + recomm_disk + ' -c' + new_path + ' -y ' + '\'')
    result = salt_command(command,recomm_host)
    msg =( result + '\n')
    msg =('Disk recommision process has been completed on the host : ' + recomm_host + '.email.comcast.net - ' + recomm_disk)
    del slack_msg[:]
    slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
    post_to_slack(slack_msg)

    ''' Validate  device path and size '''
    command = ('\'' + 'df -h ' + ' ' + mount_path + '\'' )
    result = salt_command(command,recomm_host)
    devices = []
    for line in result.split('\n'):
       if mount_path in line:
           devices.append(line.split()[0][:-1])
           devices.append(line.split()[1][:-1])

    if not devices:
       msg = ('Please check disk recommission process again' + '\n' + 'The disk not mounted on:' + mount_path )
       del slack_msg[:]
       slack_msg.append({"type": "section","text": {"type": "mrkdwn","text": msg}})
       post_to_slack(slack_msg)

    file2 = ('/var/tmp/scaldisk/' + recomm_host + '_' + recomm_disk + '_recomm_inprocess.txt')
    remove = ('/var/tmp/scaldisk/' + recomm_host + '_' + recomm_disk + '_recomm_done.txt')
    os.rename(file2,remove)

def stop_alert(host_name):
    lock_file  =('/var/tmp/scaldisk/' + host_name  + '_slack_alert_lock.txt')
    f=open(lock_file, "a+")
    f.write(('Alerted at: ' + str(datetime.datetime.now())))
    line_count = sum(1 for line in open(lock_file))
    if line_count >=3:
	# "alerted more then 3 time - stop alertingr"
	return 1
    else:
	# 'send alert to slack'
        return 0
    if line_count >=20:
	# 'Remove file'
        os.remove(lock_file)

def salt_command(command,recomm_host):
    cmd = shlex.split('salt' + ' ' + '\''+ recomm_host + '\''  + ' ' +  'cmd.run' + ' ' + command)
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    return (result)

def post_to_slack(message):
    #webhook_url = 
    webhook_url = 'https://hooks.slack.com/services/'
    slack_data = json.dumps({'text': 'disks are under oos \n','blocks': message,'username': 'Scality Alert','icon_emoji': ':scality:'})
    proxies = {
    'http': 'http://resappdprx.email.xxx.net:3128',
    'https': 'http://resappdprx.email.xxx.net:3128'
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

def log_cleanup():
    days = 9
    path =('/var/tmp/scaldisk/')
    time_in_secs = time.time() - (days * 24 * 60 * 60 )
    for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
            full_path = os.path.join(root, file)
            stat = os.stat(full_path)
            if stat.st_mtime <= time_in_secs:
               if os.path.exists(full_path):
                  os.remove(full_path)

if __name__ == "__main__":
   main()
