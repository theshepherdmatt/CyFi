#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# ============================
#   Colour Code Definitions
# ============================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ============================
#   Variables for Progress Tracking
# ============================
TOTAL_STEPS=15
CURRENT_STEP=0
LOG_FILE="install.log"

rm -f "$LOG_FILE"

# ============================
#   ASCII Art Banner Function
# ============================
banner() {
    echo -e "${MAGENTA}"
    echo "======================================================================================================"
    echo "   CyFi Installer: Volumio-based audio experience with IR remote support (Cyrus build)"
    echo "======================================================================================================"
    echo -e "${NC}"
}

# ============================
#   Log + Progress Functions
# ============================
log_message() {
    local type="$1"
    local message="$2"
    case "$type" in
        "info")    echo -e "${BLUE}[INFO]${NC} $message" ;;
        "success") echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
        "warning") echo -e "${YELLOW}[WARNING]${NC} $message" ;;
        "error")   echo -e "${RED}[ERROR]${NC} $message" >&2 ;;
    esac
}

log_progress() {
    local message="$1"
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo -e "${BLUE}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} $message"
}

# ============================
#  Check Root BEFORE We Call It
# ============================
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_message "error" "Please run as root or via sudo."
        exit 1
    fi
}

# ============================
#   CyFi-Specific Tips
# ============================
TIPS=(
  "Under 'Config', you can switch display modes."
  "Explore different screensaver types in Config!"
  "Brightness can be tweaked for late-night listening."
  "CyFi: Where code meets Hi-Fi."
  "Help & logs: see install.log or run 'journalctl -u cyfi.service'."
)
show_random_tip() {
    local index=$((RANDOM % ${#TIPS[@]}))
    log_message "info" "Tip: ${TIPS[$index]}"
}

# ============================
#   run_command with Minimal Output
# ============================
run_command() {
    local cmd="$1"
    echo "Running: $cmd" >> "$LOG_FILE"
    echo -e "${MAGENTA}Running command...${NC}"
    bash -c "$cmd" >> "$LOG_FILE" 2>&1
    local exit_status=$?
    if [ $exit_status -ne 0 ]; then
        log_message "error" "Command failed: $cmd. Check $LOG_FILE for details."
        exit 1
    fi
    echo -e "${GREEN}Done.${NC}"
}

# ============================
#   Gather User Preferences (IR only)
# ============================
get_user_preferences() {
    enable_gpio_ir
    gather_ir_remote_configuration
}

# ============================
#   Always Set GPIO IR to 27
# ============================
enable_gpio_ir() {
    log_progress "Configuring GPIO IR overlay for GPIO 27 in userconfig.txt..."
    CONFIG_FILE="/boot/userconfig.txt"
    if [ ! -f "$CONFIG_FILE" ]; then
        run_command "touch \"$CONFIG_FILE\""
    fi
    if grep -q "^dtoverlay=gpio-ir" "$CONFIG_FILE"; then
        log_message "info" "GPIO IR overlay already present. Updating to use GPIO 27."
        run_command "sed -i 's/^dtoverlay=gpio-ir.*$/dtoverlay=gpio-ir,gpio_pin=27/' \"$CONFIG_FILE\""
    else
        echo "dtoverlay=gpio-ir,gpio_pin=27" >> "$CONFIG_FILE"
        log_message "success" "GPIO IR overlay added with GPIO 27."
    fi
}

# ============================
#   Full 20 Remote Option List
# ============================
gather_ir_remote_configuration() {
    echo -e "\n${MAGENTA}Select your IR remote configuration:${NC}"
    echo "1) Default Cyrus Remote"
    echo "2) Apple Remote A1156"
    echo "3) Apple Remote A1156 Alternative"
    echo "4) Apple Remote A1294"
    echo "5) Apple Remote A1294 Alternative"
    echo "6) Arcam ir-DAC-II Remote"
    echo "7) Atrix Remote"
    echo "8) Bluesound RC1"
    echo "9) Denon Remote RC-1204"
    echo "10) JustBoom IR Remote"
    echo "11) Marantz RC003PMCD"
    echo "12) Odroid Remote"
    echo "13) Philips CD723"
    echo "14) PDP Gaming Remote Control"
    echo "15) Samsung AA59-00431A"
    echo "16) Samsung_BN59-006XXA"
    echo "17) XBox 360 Remote"
    echo "18) XBox One Remote"
    echo "19) Xiaomi IR for TV box"
    echo "20) Yamaha RAV363"
    
    read -p "Enter your choice (1-20): " choice
    case "$choice" in
        1) remote_folder="Default Cyrus Remote" ;;
        2) remote_folder="Apple Remote A1156" ;;
        3) remote_folder="Apple Remote A1156 Alternative" ;;
        4) remote_folder="Apple Remote A1294" ;;
        5) remote_folder="Apple Remote A1294 Alternative" ;;
        6) remote_folder="Arcam ir-DAC-II Remote" ;;
        7) remote_folder="Atrix Remote" ;;
        8) remote_folder="Bluesound RC1" ;;
        9) remote_folder="Denon Remote RC-1204" ;;
        10) remote_folder="JustBoom IR Remote" ;;
        11) remote_folder="Marantz RC003PMCD" ;;
        12) remote_folder="Odroid Remote" ;;
        13) remote_folder="Philips CD723" ;;
        14) remote_folder="PDP Gaming Remote Control" ;;
        15) remote_folder="Samsung AA59-00431A" ;;
        16) remote_folder="Samsung_BN59-006XXA" ;;
        17) remote_folder="XBox 360 Remote" ;;
        18) remote_folder="XBox One Remote" ;;
        19) remote_folder="Xiaomi IR for TV box" ;;
        20) remote_folder="Yamaha RAV363" ;;
        *) echo "Invalid selection. Exiting."; exit 1 ;;
    esac
    REMOTE_CONFIG_CHOICE=true
    log_message "info" "IR remote selected: $remote_folder"
}

# ============================
#   IR Remote Configuration Application
# ============================
apply_ir_remote_configuration() {
    log_progress "Applying IR remote configuration for: $remote_folder"
    if [ "$remote_folder" = "Default Cyrus Remote" ]; then
        log_message "info" "Default Cyrus Remote selected – configuration already present, no changes made."
        return
    else
        SOURCE_DIR="/home/volumio/CyFi/lirc/configurations/${remote_folder}/"
        if [ ! -d "$SOURCE_DIR" ]; then
            log_message "error" "Directory '$SOURCE_DIR' does not exist."
            exit 1
        fi
    fi
    DEST_DIR="/etc/lirc/"

    # Only copy files for custom (non-default) remotes
    if [ "$remote_folder" != "Default Cyrus Remote" ]; then
        if [ -f "${SOURCE_DIR}lircd.conf" ]; then
            run_command "cp \"${SOURCE_DIR}lircd.conf\" \"${DEST_DIR}lircd.conf\""
            log_message "success" "Copied lircd.conf from $remote_folder."
        else
            log_message "error" "File '${SOURCE_DIR}lircd.conf' not found."
            exit 1
        fi

        if [ -f "${SOURCE_DIR}lircrc" ]; then
            run_command "cp \"${SOURCE_DIR}lircrc\" \"${DEST_DIR}lircrc\""
            log_message "success" "Copied lircrc from $remote_folder."
        else
            log_message "error" "File '${SOURCE_DIR}lircrc' not found."
            exit 1
        fi

        run_command "systemctl restart lircd"
        run_command "systemctl restart ir_listener.service"
        log_message "success" "IR services restarted."
        echo -e "\nIR remote configuration applied. Please reboot later for changes to take effect."
    fi
}


# ============================
#   System Dependencies
# ============================
install_system_dependencies() {
    log_progress "Installing system-level dependencies, this might take a while..."
    run_command "apt-get update"
    run_command "apt-get install -y \
            python3.7 \
            python3.7-dev \
            python3-pip \
            libjpeg-dev \
            zlib1g-dev \
            libfreetype6-dev \
            i2c-tools \
            python3-smbus \
            libgirepository1.0-dev \
            pkg-config \
            libcairo2-dev \
            libffi-dev \
            build-essential \
            libxml2-dev \
            libxslt1-dev \
            libssl-dev \
            lirc \
            lsof"
    log_message "success" "System-level dependencies installed."
    show_random_tip
}

upgrade_pip() {
    log_progress "Upgrading pip, setuptools, and wheel..."
    run_command "python3.7 -m pip install --upgrade pip setuptools wheel"
    log_message "success" "pip, setuptools, and wheel upgraded."
    show_random_tip
}

install_python_dependencies() {
    log_progress "Installing Python dependencies, please wait..."
    run_command "python3.7 -m pip install --upgrade --ignore-installed pycairo"
    run_command "python3.7 -m pip install --upgrade --ignore-installed -r /home/volumio/CyFi/requirements.txt"
    log_message "success" "Python dependencies installed."
    show_random_tip
}

enable_i2c_spi() {
    log_progress "Enabling I2C and SPI in config.txt..."
    CONFIG_FILE="/boot/userconfig.txt"
    if [ ! -f "$CONFIG_FILE" ]; then
        run_command "touch \"$CONFIG_FILE\""
    fi
    # SPI
    if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
        echo "dtparam=spi=on" >> "$CONFIG_FILE"
        log_message "success" "SPI enabled in userconfig.txt."
    else
        log_message "info" "SPI is already enabled."
    fi
    # I2C
    if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
        echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
        log_message "success" "I2C enabled in userconfig.txt."
    else
        log_message "info" "I2C is already enabled."
    fi
    log_progress "Loading I2C and SPI kernel modules..."
    run_command "modprobe i2c-dev"
    run_command "modprobe spi-bcm2835"
    if [ -e /dev/i2c-1 ]; then
        log_message "success" "/dev/i2c-1 is present."
    else
        log_message "warning" "/dev/i2c-1 not found; trying modprobe i2c-bcm2708..."
        run_command "modprobe i2c-bcm2708"
        sleep 1
        if [ -e /dev/i2c-1 ]; then
            log_message "success" "/dev/i2c-1 was successfully initialized."
        else
            log_message "error" "Could not initialize /dev/i2c-1. Check config and wiring."
            exit 1
        fi
    fi
    show_random_tip
}

# ============================
#   Samba Setup
# ============================
setup_samba() {
    log_progress "Configuring Samba for CyFi..."
    SMB_CONF="/etc/samba/smb.conf"
    if [ ! -f "$SMB_CONF.bak" ]; then
        run_command "cp $SMB_CONF $SMB_CONF.bak"
        log_message "info" "Backup of $SMB_CONF created."
    fi
    if ! grep -q "\[CyFi\]" "$SMB_CONF"; then
        cat <<EOF >> "$SMB_CONF"

[CyFi]
   path = /home/volumio/CyFi
   writable = yes
   browseable = yes
   guest ok = yes
   force user = volumio
   create mask = 0777
   directory mask = 0777
   public = yes
EOF
        log_message "success" "Samba config for CyFi appended."
    else
        log_message "info" "CyFi section already in smb.conf."
    fi
    run_command "systemctl restart smbd"
    log_message "success" "Samba restarted."
    run_command "chown -R volumio:volumio /home/volumio/CyFi"
    run_command "chmod -R 777 /home/volumio/CyFi"
    log_message "success" "Permissions set for /home/volumio/CyFi."
    show_random_tip
}

# ============================
#   Main CyFi Service
# ============================
setup_main_service() {
    log_progress "Setting up Main CyFi Service..."
    SERVICE_FILE="/etc/systemd/system/cyfi.service"
    LOCAL_SERVICE="/home/volumio/CyFi/service/cyfi.service"
    if [[ -f "$LOCAL_SERVICE" ]]; then
        run_command "cp \"$LOCAL_SERVICE\" \"$SERVICE_FILE\""
        run_command "systemctl daemon-reload"
        run_command "systemctl enable cyfi.service"
        run_command "systemctl start cyfi.service"
        log_message "success" "cyfi.service installed and started."
    else
        log_message "error" "cyfi.service not found in /home/volumio/CyFi/service."
        exit 1
    fi
    show_random_tip
}

# ============================
#   MPD Configuration
# ============================
configure_mpd() {
    log_progress "Configuring MPD for FIFO..."
    MPD_CONF_FILE="/volumio/app/plugins/music_service/mpd/mpd.conf.tmpl"
    FIFO_OUTPUT="
audio_output {
    type            \"fifo\"
    name            \"my_fifo\"
    path            \"/tmp/cava.fifo\"
    format          \"44100:16:2\"
}"
    if grep -q "/tmp/cava.fifo" "$MPD_CONF_FILE"; then
        log_message "info" "FIFO output config already in MPD conf."
    else
        echo "$FIFO_OUTPUT" | tee -a "$MPD_CONF_FILE" >> "$LOG_FILE"
        log_message "success" "Added FIFO output to MPD conf."
    fi
    run_command "systemctl restart mpd"
    log_message "success" "MPD restarted with updated FIFO config."
    show_random_tip
}

# ============================
#   CAVA Installation
# ============================
check_cava_installed() {
    if command -v cava >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

install_cava_from_fork() {
    log_progress "Installing CAVA from the fork..."
    CAVA_REPO="https://github.com/theshepherdmatt/cava.git"
    CAVA_INSTALL_DIR="/home/volumio/cava"
    if check_cava_installed; then
        log_message "info" "CAVA already installed. Skipping."
        return
    fi
    log_message "info" "Installing build dependencies for CAVA..."
    run_command "apt-get install -y \
        libfftw3-dev \
        libasound2-dev \
        libncursesw5-dev \
        libpulse-dev \
        libtool \
        automake \
        autoconf \
        gcc \
        make \
        pkg-config \
        libiniparser-dev"
    if [[ ! -d "$CAVA_INSTALL_DIR" ]]; then
        run_command "git clone $CAVA_REPO $CAVA_INSTALL_DIR"
    else
        run_command "cd $CAVA_INSTALL_DIR && git pull"
    fi
    run_command "cd $CAVA_INSTALL_DIR && ./autogen.sh"
    run_command "cd $CAVA_INSTALL_DIR && ./configure"
    run_command "cd $CAVA_INSTALL_DIR && make"
    run_command "cd $CAVA_INSTALL_DIR && make install"
    log_message "success" "CAVA installed from fork."
    show_random_tip
}

setup_cava_service() {
    log_progress "Setting up CAVA service..."
    CAVA_SERVICE_FILE="/etc/systemd/system/cava.service"
    LOCAL_CAVA_SERVICE="/home/volumio/CyFi/service/cava.service"
    if [[ -f "$LOCAL_CAVA_SERVICE" ]]; then
        run_command "cp \"$LOCAL_CAVA_SERVICE\" \"$CAVA_SERVICE_FILE\""
        run_command "systemctl daemon-reload"
        run_command "systemctl enable cava.service"
        log_message "success" "CAVA service installed."
    else
        log_message "error" "cava.service not found in /home/volumio/CyFi/service."
    fi
    show_random_tip
}

# ============================
#   IR Controller
# ============================
install_lircrc() {
    log_progress "Installing LIRC configuration (lircrc) from repository..."
    LOCAL_LIRCRC="/home/volumio/CyFi/lirc/lircrc"
    DESTINATION="/etc/lirc/lircrc"
    if [ -f "$LOCAL_LIRCRC" ]; then
        run_command "cp \"$LOCAL_LIRCRC\" \"$DESTINATION\""
        log_message "success" "LIRC configuration (lircrc) copied to $DESTINATION."
    else
        log_message "error" "Local lircrc not found at $LOCAL_LIRCRC. Please ensure it is present."
        exit 1
    fi
}

install_lirc_configs() {
    log_progress "Installing LIRC configuration files..."
    LOCAL_LIRCRC="/home/volumio/CyFi/lirc/lircrc"
    LOCAL_LIRCD_CONF="/home/volumio/CyFi/lirc/lircd.conf"
    DEST_LIRCRC="/etc/lirc/lircrc"
    DEST_LIRCD_CONF="/etc/lirc/lircd.conf"
    if [ -f "$LOCAL_LIRCRC" ]; then
        run_command "cp \"$LOCAL_LIRCRC\" \"$DEST_LIRCRC\""
        log_message "success" "Copied lircrc to $DEST_LIRCRC."
    else
        log_message "error" "lircrc file not found at $LOCAL_LIRCRC."
        exit 1
    fi
    if [ -f "$LOCAL_LIRCD_CONF" ]; then
        run_command "cp \"$LOCAL_LIRCD_CONF\" \"$DEST_LIRCD_CONF\""
        log_message "success" "Copied lircd.conf to $DEST_LIRCD_CONF."
    else
        log_message "error" "lircd.conf file not found at $LOCAL_LIRCD_CONF."
        exit 1
    fi
    show_random_tip
}

setup_ir_listener_service() {
    log_progress "Setting up IR Listener service..."
    IR_SERVICE_FILE="/etc/systemd/system/ir_listener.service"
    LOCAL_IR_SERVICE="/home/volumio/CyFi/service/ir_listener.service"
    if [ -f "$LOCAL_IR_SERVICE" ]; then
        run_command "cp \"$LOCAL_IR_SERVICE\" \"$IR_SERVICE_FILE\""
        run_command "systemctl daemon-reload"
        run_command "systemctl enable ir_listener.service"
        run_command "systemctl start ir_listener.service"
        log_message "success" "ir_listener.service installed and started."
    else
        log_message "error" "ir_listener.service not found in /home/volumio/CyFi/service."
        exit 1
    fi
    show_random_tip
}

update_lirc_options() {
    log_progress "Updating LIRC options: setting driver to default..."
    sed -i 's|^driver\s*=.*|driver          = default|' /etc/lirc/lirc_options.conf
    log_message "success" "LIRC options updated: driver set to default."
    show_random_tip
}

# ============================
#   Permissions
# ============================
set_permissions() {
    log_progress "Setting ownership & permissions for /home/volumio/CyFi..."
    run_command "chown -R volumio:volumio /home/volumio/CyFi"
    run_command "chmod -R 755 /home/volumio/CyFi"
    log_message "success" "Ownership/permissions set."
}

# ============================
#   Set Up run_update Wrapper
# ============================
setup_run_update_wrapper() {
    log_progress "Compiling and installing run_update setuid wrapper..."
    if [ -f "/home/volumio/CyFi/scripts/run_update.c" ]; then
        run_command "gcc -o /home/volumio/CyFi/scripts/run_update /home/volumio/CyFi/scripts/run_update.c"
        run_command "chown root:root /home/volumio/CyFi/scripts/run_update"
        run_command "chmod 4755 /home/volumio/CyFi/scripts/run_update"
        log_message "success" "run_update setuid wrapper compiled and installed."
    else
        log_message "warning" "run_update.c not found in /home/volumio/CyFi/scripts. Skipping setuid wrapper installation."
    fi
    show_random_tip
}

# ============================
#   Main CyFi Installation
# ============================
main() {
    check_root
    banner
    log_message "info" "Starting CyFi Installer..."
    
    # Gather all interactive answers at the very top
    get_user_preferences

    install_system_dependencies
    enable_i2c_spi
    upgrade_pip
    install_python_dependencies
    setup_main_service
    configure_mpd
    install_cava_from_fork
    setup_cava_service
    setup_samba
    install_lircrc
    install_lirc_configs
    setup_ir_listener_service
    update_lirc_options

    # Apply IR remote configuration
    if [ "$REMOTE_CONFIG_CHOICE" = true ]; then
        apply_ir_remote_configuration
    fi

    set_permissions
    setup_run_update_wrapper

    log_message "success" "CyFi installation complete! A reboot is required."

    while true; do
        read -rp "Reboot now? (y/n) " answer
        case $answer in
            [Yy]* )
                log_message "info" "Rebooting system now. See you on the other side!"
                reboot
                exit 0
                ;;
            [Nn]* )
                log_message "info" "Installation finished. Please reboot manually later."
                break
                ;;
            * ) log_message "warning" "Please answer y or n." ;;
        esac
    done
}

main
