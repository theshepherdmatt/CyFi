#!/usr/bin/env python3
# src/main.py

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
import time
import threading
import logging
import yaml
import socket
import subprocess
import os
import glob
import sys
from PIL import Image, ImageSequence

from display.screens.clock import Clock
from hardware.shutdown_system import shutdown_system
from display.screens.original_screen import OriginalScreen
from display.screens.modern_screen import ModernScreen
from display.screens.minimal_screen import MinimalScreen
from display.screens.system_info_screen import SystemInfoScreen
from display.screensavers.snake_screensaver import SnakeScreensaver
from display.screensavers.geo_screensaver import GeoScreensaver
from display.screensavers.bouncing_text_screensaver import BouncingTextScreensaver
from display.display_manager import DisplayManager
from managers.menu_manager import MenuManager
from managers.mode_manager import ModeManager
from managers.manager_factory import ManagerFactory
from network.volumio_listener import VolumioListener

def load_config(config_path='/config.yaml'):
    abs_path = os.path.abspath(config_path)
    print(f"Attempting to load config from: {abs_path}")
    print(f"Does the file exist? {os.path.isfile(config_path)}")
    config = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logging.debug(f"Configuration loaded from {config_path}.")
        except yaml.YAMLError as e:
            logging.error(f"Error loading config file {config_path}: {e}")
    else:
        logging.warning(f"Config file {config_path} not found. Using default configuration.")
    return config

FIRST_RUN_FLAG = '/data/cyfi_first_run_done'

def has_seen_ready():
    return os.path.exists(FIRST_RUN_FLAG)

def set_has_seen_ready():
    try:
        os.makedirs(os.path.dirname(FIRST_RUN_FLAG), exist_ok=True)
        with open(FIRST_RUN_FLAG, 'w') as f:
            f.write("shown")
    except Exception as e:
        print(f"Could not create first-run flag file: {e}")

def is_first_run():
    netconfigured = os.path.exists('/data/configuration/netconfigured')
    network_configs = glob.glob('/data/configuration/system_controller/network/*.json')
    return not (netconfigured and network_configs)

def is_network_online(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except Exception:
        return False

def show_gif_loop(gif_path, stop_condition, display_manager, logger):
    try:
        image = Image.open(gif_path)
        if not getattr(image, "is_animated", False):
            logger.warning(f"GIF '{gif_path}' is not animated.")
            return
    except Exception as e:
        logger.error(f"Failed to load GIF '{gif_path}': {e}")
        return
    logger.info(f"Displaying GIF: {gif_path}")
    required_size = display_manager.oled.size
    while not stop_condition():
        for frame in ImageSequence.Iterator(image):
            if stop_condition():
                return
            background = Image.new(display_manager.oled.mode, required_size)
            frame_converted = frame.convert(display_manager.oled.mode)
            background.paste(frame_converted, (0,0))
            display_manager.oled.display(background)
            frame_duration = frame.info.get('duration', 100) / 1000.0
            time.sleep(frame_duration)

def cyfi_command_server(mode_manager, volumio_listener, display_manager, ready_stop_event):
    sock_path = "/tmp/cyfi.sock"
    try:
        os.remove(sock_path)
    except OSError:
        pass

    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.bind(sock_path)
    server_socket.listen(1)
    print(f"CyFi command server listening on {sock_path}")

    select_mapping = {
        "menu": lambda: mode_manager.menu_manager.select_item(),
        "tidal": lambda: mode_manager.tidal_manager.select_item(),
        "qobuz": lambda: mode_manager.qobuz_manager.select_item(),
        "spotify": lambda: mode_manager.spotify_manager.select_item(),
        "library": lambda: mode_manager.library_manager.select_item(),
        "radiomanager": lambda: mode_manager.radio_manager.select_item(),
        "motherearthradio": lambda: mode_manager.motherearth_manager.select_item(),
        "radioparadise": lambda: mode_manager.radioparadise_manager.select_item(),
        "playlists": lambda: mode_manager.playlist_manager.select_item(),
        "configmenu": lambda: mode_manager.config_menu.select_item(),
        "remotemenu": lambda: mode_manager.remote_menu.select_item(),
        "displaymenu": lambda: mode_manager.display_menu.select_item(),
        "clockmenu": lambda: mode_manager.clock_menu.select_item(),
        "systemupdate": lambda: mode_manager.system_update_menu.select_item(),
        "screensavermenu": lambda: mode_manager.screensaver_menu.select_item(),
        "systeminfo": lambda: mode_manager.system_info_screen.select_item(),
    }

    scroll_mapping = {
        "scroll_up": {
            "tidal": lambda: mode_manager.tidal_manager.scroll_selection(-1),
            "qobuz": lambda: mode_manager.qobuz_manager.scroll_selection(-1),
            "spotify": lambda: mode_manager.spotify_manager.scroll_selection(-1),
            "library": lambda: mode_manager.library_manager.scroll_selection(-1),
            "radiomanager": lambda: mode_manager.radio_manager.scroll_selection(-1),
            "motherearthradio": lambda: mode_manager.motherearth_manager.scroll_selection(-1),
            "radioparadise": lambda: mode_manager.radioparadise_manager.scroll_selection(-1),
            "playlists": lambda: mode_manager.playlist_manager.scroll_selection(-1),
            "configmenu": lambda: mode_manager.config_menu.scroll_selection(-1),
            "remotemenu": lambda: mode_manager.remote_menu.scroll_selection(-1),
            "displaymenu": lambda: mode_manager.display_menu.scroll_selection(-1),
            "clockmenu": lambda: mode_manager.clock_menu.scroll_selection(-1),
            "systemupdate": lambda: mode_manager.system_update_menu.scroll_selection(-1),
            "screensavermenu": lambda: mode_manager.screensaver_menu.scroll_selection(-1),
            "systeminfo": lambda: mode_manager.system_info_screen.scroll_selection(-1),
        },
        "scroll_down": {
            "tidal": lambda: mode_manager.tidal_manager.scroll_selection(1),
            "qobuz": lambda: mode_manager.qobuz_manager.scroll_selection(1),
            "spotify": lambda: mode_manager.spotify_manager.scroll_selection(1),
            "library": lambda: mode_manager.library_manager.scroll_selection(1),
            "radiomanager": lambda: mode_manager.radio_manager.scroll_selection(1),
            "motherearthradio": lambda: mode_manager.motherearth_manager.scroll_selection(1),
            "radioparadise": lambda: mode_manager.radioparadise_manager.scroll_selection(1),
            "playlists": lambda: mode_manager.playlist_manager.scroll_selection(1),
            "configmenu": lambda: mode_manager.config_menu.scroll_selection(1),
            "remotemenu": lambda: mode_manager.remote_menu.scroll_selection(1),
            "displaymenu": lambda: mode_manager.display_menu.scroll_selection(1),
            "clockmenu": lambda: mode_manager.clock_menu.scroll_selection(1),
            "systemupdate": lambda: mode_manager.system_update_menu.scroll_selection(1),
            "screensavermenu": lambda: mode_manager.screensaver_menu.scroll_selection(1),
            "systeminfo": lambda: mode_manager.system_info_screen.scroll_selection(1),
        }
    }

    while True:
        try:
            conn, _ = server_socket.accept()
            with conn:
                data = conn.recv(1024)
                if not data:
                    continue
                command = data.decode("utf-8").strip()
                print(f"Command received: {command}")
                current_mode = mode_manager.get_mode()
                print(f"Current mode: {current_mode}")  # DEBUG: see the mode

                # Exit ready GIF if any "menu/select/toggle/ok" arrives during boot
                if not ready_stop_event.is_set() and command in ["menu", "select", "ok", "toggle"]:
                    print("Exiting ready GIF due to remote control command.")
                    ready_stop_event.set()
                    continue

                if command == "home":
                    mode_manager.trigger("to_clock")
                elif command == "shutdown":
                    shutdown_system(display_manager, None, mode_manager)
                elif command == "menu":
                    if current_mode == "clock":
                        mode_manager.trigger("to_menu")
                elif command == "toggle":
                    mode_manager.toggle_play_pause()
                elif command == "repeat":
                    print("Repeat command received. (Implement as needed)")
                elif command == "select":
                    if current_mode in select_mapping:
                        print(f"Selecting item in mode: {current_mode}")  # DEBUG
                        select_mapping[current_mode]()
                    else:
                        print(f"No select mapping for mode: {current_mode}")

                # **Replace the scroll command handlers with this debug and forced scroll:**

                elif command == "scroll_left":
                    print(f"Scroll left command received in mode: {current_mode}")  # DEBUG
                    mode_manager.menu_manager.scroll_selection(-1)
                    print("Called menu_manager.scroll_selection(-1) [LEFT]")

                elif command == "scroll_right":
                    print(f"Scroll right command received in mode: {current_mode}")  # DEBUG
                    mode_manager.menu_manager.scroll_selection(1)
                    print("Called menu_manager.scroll_selection(1) [RIGHT]")
                    
                    
                elif command == "scroll_up":
                    print(f"Scroll up command received in mode: {current_mode}")  # DEBUG
                    # General-purpose scroll (menu or submenus)
                    if current_mode in scroll_mapping["scroll_up"]:
                        scroll_mapping["scroll_up"][current_mode]()
                        print(f"Called scroll_selection(-1) for {current_mode}")
                    else:
                        print("No scroll_up mapping for this mode.")

                elif command == "scroll_down":
                    print(f"Scroll down command received in mode: {current_mode}")  # DEBUG
                    if current_mode in scroll_mapping["scroll_down"]:
                        scroll_mapping["scroll_down"][current_mode]()
                        print(f"Called scroll_selection(1) for {current_mode}")
                    else:
                        print("No scroll_down mapping for this mode.")


                elif command == "volume_plus":
                    volumio_listener.increase_volume()
                elif command == "volume_minus":
                    volumio_listener.decrease_volume()
                elif command == "back":
                    mode_manager.trigger("back")
                else:
                    print(f"No mapping for command: {command}")
        except Exception as e:
            print(f"Error in command server: {e}")

def main():
    # --- Logging ---
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("CyFiMain")

    # --- Config ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, '..', 'config.yaml')
    config = load_config(config_path)
    display_config = config.get('display', {})

    # --- DisplayManager ---
    display_manager = DisplayManager(display_config)

    # --- First Run: Show Network Setup GIFs ---
    if is_first_run():
        connecting_gif = display_config.get('connecting_path', 'connecting.gif')
        connected_gif = display_config.get('connected_path', 'connected.gif')
        logger.info("First run detected. Showing 'connecting' GIF until network is up.")
        show_gif_loop(
            connecting_gif,
            lambda: is_network_online(),
            display_manager,
            logger
        )
        logger.info("Network connected! Showing 'connected' GIF for 2 seconds.")
        show_gif_loop(
            connected_gif,
            lambda: True,
            display_manager,
            logger
        )
        time.sleep(2)
        
    # --- Determine which ready GIF to show first ---
    if not has_seen_ready():
        first_ready_path = display_config.get('ready_new_path', 'ready_new.gif')
        logger.info("Showing 'ready_new.gif' for new user.")
        is_first_time_user = True
    else:
        first_ready_path = display_config.get('ready_gif_path', 'ready.gif')
        logger.info("Showing 'ready.gif' for returning user.")
        is_first_time_user = False

    # --- Startup Logo ---
    logger.info("Displaying startup logo...")
    display_manager.show_logo(duration=12)
    logger.info("Startup logo display complete.")
    display_manager.clear_screen()
    logger.info("Screen cleared after logo display.")

    # --- Readiness GIF Threads/Events ---
    volumio_ready_event = threading.Event()
    min_loading_event = threading.Event()
    ready_stop_event = threading.Event()
    MIN_LOADING_DURATION = 6  # seconds

    # --- VolumioListener ---
    volumio_cfg = config.get('volumio', {})
    volumio_host = volumio_cfg.get('host', 'localhost')
    volumio_port = volumio_cfg.get('port', 3000)
    volumio_listener = VolumioListener(host=volumio_host, port=volumio_port)

    # On Volumio state change: set events, also handle ready_stop_event if playing
    def on_state_changed(sender, state):
        logger.info(f"Volumio state changed: {state}")
        if state.get('status') == 'play' and not ready_stop_event.is_set():
            logger.info("Detected playback start! Exiting ready screen.")
            ready_stop_event.set()
        if state.get('status') in ['play', 'stop', 'pause', 'unknown']:
            logger.info("Volumio is considered ready now.")
            volumio_ready_event.set()

    volumio_listener.state_changed.connect(on_state_changed)

    # --- Command server must start early so IR remote works for GIF loop exit ---
    class DummyModeManager:
        def get_mode(self):
            return None
        def trigger(self, event):
            pass

    dummy_mode_manager = DummyModeManager()
    threading.Thread(
        target=cyfi_command_server,
        args=(dummy_mode_manager, volumio_listener, display_manager, ready_stop_event),
        daemon=True
    ).start()
    print("CyFi command server thread started.")

    # Loading GIF thread
    def show_loading():
        loading_gif_path = display_config.get('loading_gif_path', 'loading.gif')
        try:
            image = Image.open(loading_gif_path)
            if not getattr(image, "is_animated", False):
                logger.warning(f"Loading GIF '{loading_gif_path}' is not animated.")
                return
        except IOError:
            logger.error(f"Failed to load loading GIF '{loading_gif_path}'.")
            return
        logger.info("Displaying loading GIF during startup.")
        display_manager.clear_screen()
        time.sleep(0.1)
        while not (volumio_ready_event.is_set() and min_loading_event.is_set()):
            for frame in ImageSequence.Iterator(image):
                if volumio_ready_event.is_set() and min_loading_event.is_set():
                    logger.info("Volumio ready & min load done, stopping loading GIF.")
                    return
                display_manager.oled.display(frame.convert(display_manager.oled.mode))
                frame_duration = frame.info.get('duration', 100) / 1000.0
                time.sleep(frame_duration)
        logger.info("Exiting loading GIF display thread.")

    threading.Thread(target=show_loading, daemon=True).start()

    # Minimum loading duration
    def set_min_loading_event():
        time.sleep(MIN_LOADING_DURATION)
        min_loading_event.set()
        logger.info("Minimum loading duration has elapsed.")

    threading.Thread(target=set_min_loading_event, daemon=True).start()

    # --- Wait for both loading events then run Ready GIF ---
    logger.info("Waiting for Volumio readiness & min load time.")
    volumio_ready_event.wait()
    min_loading_event.wait()
    logger.info("Volumio is ready & min loading time passed, proceeding to ready GIF.")

    show_gif_loop(first_ready_path, lambda: True, display_manager, logger)

    # Now show "looping ready" GIF until remote/IR event or playback/other ready_stop_event
    def show_ready_gif_until_event(stop_event, gif_path):
        try:
            image = Image.open(gif_path)
            if not getattr(image, "is_animated", False):
                display_manager.oled.display(image.convert(display_manager.oled.mode))
                return
            while not stop_event.is_set():
                for frame in ImageSequence.Iterator(image):
                    if stop_event.is_set():
                        return
                    display_manager.oled.display(frame.convert(display_manager.oled.mode))
                    frame_duration = frame.info.get('duration', 100) / 1000.0
                    time.sleep(frame_duration)
        except Exception as e:
            logger.error(f"Failed to loop GIF {gif_path}: {e}")

    ready_loop_path = display_config.get('ready_loop_path', 'ready_loop.gif')
    threading.Thread(
        target=show_ready_gif_until_event,
        args=(ready_stop_event, ready_loop_path),
        daemon=True
    ).start()
    ready_stop_event.wait()
    logger.info("Ready GIF exited, continuing to UI startup.")

    if is_first_time_user:
        set_has_seen_ready()

    # --- Now the main UI, ModeManager, screens, etc ---
    clock_config = config.get('clock', {})
    clock = Clock(display_manager, clock_config, volumio_listener)
    clock.logger = logging.getLogger("Clock")
    clock.logger.setLevel(logging.INFO)

    mode_manager = ModeManager(
        display_manager=display_manager,
        clock=clock,
        volumio_listener=volumio_listener,
        preference_file_path="../preference.json",
        config=config
    )

    manager_factory = ManagerFactory(
        display_manager=display_manager,
        volumio_listener=volumio_listener,
        mode_manager=mode_manager,
        config=config
    )
    manager_factory.setup_mode_manager()
    volumio_listener.mode_manager = mode_manager

    current_state = volumio_listener.get_current_state()
    if current_state and current_state.get("status") == "play":
        mode_manager.process_state_change(volumio_listener, current_state)
    else:
        mode_manager.trigger("to_menu")
    logger.info("Startup mode determined from current Volumio state.")

    # Restart the command server with real mode_manager (optional, but safe)
    threading.Thread(
        target=cyfi_command_server,
        args=(mode_manager, volumio_listener, display_manager, ready_stop_event),
        daemon=True
    ).start()

    # --- Main loop ---
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down CyFi via KeyboardInterrupt.")
    finally:
        try:
            volumio_listener.stop_listener()
        except Exception:
            pass
        clock.stop()
        display_manager.clear_screen()
        logger.info("CyFi shut down gracefully.")

if __name__ == "__main__":
    main()
