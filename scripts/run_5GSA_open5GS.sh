sudo ufw disable

### Enable IPv4/IPv6 Forwarding
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1

### Add NAT Rule
sudo iptables -t nat -A POSTROUTING -s 10.45.0.0/16 ! -o ogstun -j MASQUERADE
sudo ip6tables -t nat -A POSTROUTING -s 2001:db8:cafe::/48 ! -o ogstun -j MASQUERADE

# cd to the srsRAN_Project directory
cd /home/espacio5g/srsRAN_Project

sudo gnb -c gnb_b210_20MHz_oneplus_8t.yml cu_cp security --nea_pref_list=nea2,nea1,nea3,nea0
