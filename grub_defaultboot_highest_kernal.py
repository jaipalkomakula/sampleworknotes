#!/usr/bin/env python

import os
import re

def main():
 kernel= ()
 regex = re.compile('title CentOS.*')
 regex2 = re.compile('default=[0-9]')
 with open('/etc/grub.conf','r') as line:
    for line in line.readlines():
        if regex.match(line):
            kernel = kernel + ((line.split(' ')[2].replace('(', '').replace(')', '').split('-')[1].split('.')[0]),)
        if regex2.match(line):
        	src = line
        	value = int(line.split('=')[1])



 h = (max(kernel))
 index = kernel.index(h)
 target = ( 'default=' + str(index) + '\n' )

 if value == index:
 	exit ()
 else:
 	with open('/etc/grub.conf','r') as f:
 		newline=[]
 		for word in f.readlines():
 			newline.append(word.replace(src,target))
 	with open("/etc/grub.conf","w") as f:
 		for line in newline:
 			f.writelines(line)


if __name__ == "__main__":
   main()
