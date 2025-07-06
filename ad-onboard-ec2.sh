#!/bin/bash

# Update the instance
sudo apt-get update
sudo apt-get -y upgrade

# Install required packages
sudo apt-get -y install sssd realmd samba-common packagekit adcli
export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get -y -qq install krb5-user

# Configure Kerberos: disable reverse DNS and set the default realm
sudo sed -i 's/default_realm = .*/default_realm = directory.example.com/' /etc/krb5.conf
sudo sed -i '/default_realm /a \\ \\ \\ \\ \\ \\ \\ \\ rdns = false' /etc/krb5.conf

# Join the instance to the Active Directory domain
echo "<AdminPassword>" | realm join -U <AdminUser> directory.example.com --verbose

# Restrict SSH access to specific AD groups
realm deny --all
realm permit --groups <Group1> <Group2>

# Enable automatic home directory creation for AD users
sudo pam-auth-update --enable mkhomedir
