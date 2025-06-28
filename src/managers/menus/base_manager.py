# src/managers/base_manager.py
from abc import ABC, abstractmethod
import logging
import threading

class SingletonMeta(type):
    """
    A thread-safe implementation of Singleton.
    """
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class BaseManager(ABC):
    def __init__(self, display_manager, volumio_listener, mode_manager):
        self.display_manager = display_manager
        self.volumio_listener = volumio_listener
        self.mode_manager = mode_manager
        self.is_active = False
        self.on_mode_change_callbacks = []

        # Initialize logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)  # Set to INFO or adjust as needed

    @abstractmethod
    def start_mode(self):
        pass

    @abstractmethod
    def stop_mode(self):
        pass

    def add_on_mode_change_callback(self, callback):
        if callable(callback):
            self.on_mode_change_callbacks.append(callback)
            self.logger.debug(f"Added mode change callback: {callback}")
        else:
            self.logger.warning(f"Attempted to add a non-callable callback: {callback}")

    def notify_mode_change(self, mode):
        self.logger.debug(f"Notifying mode change to: {mode}")
        for callback in self.on_mode_change_callbacks:
            try:
                callback(mode)
                self.logger.debug(f"Successfully executed callback: {callback}")
            except Exception as e:
                self.logger.error(f"Error in callback {callback}: {e}")

    def clear_display(self):
        self.display_manager.clear_screen()
        self.logger.info("Cleared the display screen.")

    def back(self):
        """Default back action - delegate to ModeManager."""
        self.logger.debug("BaseManager: Delegating back action to ModeManager.")
        if self.mode_manager:
            self.mode_manager.back()


class BaseMenu(BaseManager):
    """Base class for menu screens with automatic 'Back' handling.

    Input handlers for IR remotes or rotary encoders should call the child
    menu's ``scroll_selection()`` and ``select_item()`` methods. Those methods
    can delegate to :meth:`handle_menu_select` to trigger ``mode_manager.back``
    when the "Back" entry is chosen.
    """

    back_label = "Back"

    # Example usage:
    # class InputMenu(BaseMenu):
    #     def __init__(self, mode_manager):
    #         items = ["CD", "Tuner", "Aux"]
    #         super().__init__(None, None, mode_manager)
    #         self.menu_items = self.ensure_back_item(items)
    #
    #     def select_item(self):
    #         if self.handle_menu_select(self.current_selection_index, self.menu_items):
    #             return
    #         # handle other selections here

    def ensure_back_item(self, items):
        """Append a Back entry to the list of items if not already present."""
        if not items:
            return [self.back_label]

        last = items[-1]
        if isinstance(last, dict):
            if last.get("action") != "back":
                items.append({"title": self.back_label, "action": "back"})
        elif last != self.back_label:
            items.append(self.back_label)
        return items

    def handle_menu_select(self, index, items=None):
        """Return True if the index corresponds to the Back entry."""
        item_list = items if items is not None else getattr(self, "current_menu_items", [])

        if not item_list or index >= len(item_list):
            return False

        selected = item_list[index]

        is_back = False
        if isinstance(selected, dict):
            is_back = selected.get("action") == "back"
        else:
            is_back = selected == self.back_label

        if is_back:
            self.stop_mode()
            super().back()
            return True

        return False
