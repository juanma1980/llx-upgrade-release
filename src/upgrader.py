#!/bin/bash
service plymouth stop
service plymouth-start stop
LLXUP='/sbin/lliurex-up -u -s -n'
KWIN=$(which kwin)
xinit $KWIN $* -- :0 vt1 &
export DISPLAY=:0
sleep 2
hostname lliurex.net
/usr/share/llx-upgrade-release/fakenet.py &
hostname lliurex.net
$LLXUP 
rm /etc/apt/apt.conf 2>/dev/null
echo -n "" > /etc/apt/sources.list
apt clean
repoman-cli -e 0 -y
kdialog --title "Lliurex Release Upgrade" --msgbox "Upgrade ended. Press to reboot"  && systemctl reboot || systemctl reboot
