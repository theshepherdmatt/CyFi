#!/bin/bash

# 1) Wait a bit to ensure CyFi can fully stop before overwriting
sleep 2

# 2) Stop CyFi
sudo systemctl stop cyfi

# 3) Copy preference.json to a safe location (if it exists)
if [ -f /home/volumio/CyFi/src/preference.json ]; then
    echo "Backing up preference.json..."
    cp /home/volumio/CyFi/src/preference.json /tmp/preference.json.bak
fi

# 4) Clone fresh code
rm -rf /home/volumio/CyFi_new
git clone https://github.com/theshepherdmatt/CyFi.git /home/volumio/CyFi_new

# 5) Rename old folder & put the new one in place
mv /home/volumio/CyFi /home/volumio/CyFi_old 2>/dev/null
mv /home/volumio/CyFi_new /home/volumio/CyFi

# 6) Restore preference.json if we backed it up
if [ -f /tmp/preference.json.bak ]; then
    echo "Restoring preference.json..."
    cp /tmp/preference.json.bak /home/volumio/CyFi/src/preference.json
    rm /tmp/preference.json.bak

    # Fix ownership so 'volumio' can still write to it
    chown volumio:volumio /home/volumio/CyFi/src/preference.json
    chmod 664 /home/volumio/CyFi/src/preference.json
fi

# 7) Remove old folder (optional: only if you don’t need a backup)
rm -rf /home/volumio/CyFi_old

# 8) Reboot the system
echo "Rebooting the system..."
sudo reboot
