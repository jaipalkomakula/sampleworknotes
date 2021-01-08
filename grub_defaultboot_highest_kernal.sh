#!/bin/bash

# Jaipal Komakula
# Write a bash script that changes the grub default boot to the highest kernel (not necessarily the first entry) version. The OS is CentOS 6.x. Manual steps will not be accepted.
# This script works on only Centos 6 based on grub.cfg file.

# Pick the highest Minor Revision version from rpm , generic string for kernel-2.6.32-XXXX.XXX.el6.x86_64 , Only changes Minor revision version.# or else pick highest minor revision version form /etc/grub.conf -  kernel_version=$(grep "kernel /vmlinuz-[1-9].[0-9].[0-9].*" /etc/grub.conf |awk '{print $2}'| cut -d '-' -f 3 |cut -d '.' -f 1 | sort -u | tail -1).

kernel_version=`rpm -qa kernel | sort -u | tail -1 | cut -d '-' -f 3 | cut -d '.' -f 1`

k="0"
l="1"
for c in `grep "kernel /vmlinuz-[1-9].[0-9].[0-9].*" /etc/grub.conf |awk '{print $2}'| cut -d '-' -f 3 |cut -d '.' -f 1`
do
k=$[$k+1]
if [ $kernel_version == $c ]
then
position=$[$k-$l]
fi
done

sed -i "s/default=[0-9]/default=${position}/g" /etc/grub.conf 
