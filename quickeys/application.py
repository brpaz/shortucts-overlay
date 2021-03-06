import re
import sys
import signal
import shutil
import os
import logging
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
gi.require_version('AppIndicator3', '0.1')

from quickeys.ui import ShortcutsOverlay
from quickeys import ShortcutsReader
from gi.repository import Gtk, GLib, Gio, Gdk, Wnck, AppIndicator3

logger = logging.getLogger("main")
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

APPLICATION_NAME = "quickeys"
APPLICATION_ID = "net.brunopaz.quickeys"


class Application(Gtk.Application):
    """ Main Application class """

    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, application_id=APPLICATION_ID,
                                          flags=Gio.ApplicationFlags.FLAGS_NONE,
                                          **kwargs)

        logger.info("Initializing")

        self.win = None
        self.app_dir = os.path.dirname(os.path.realpath(__file__)) + '/../'
        self.config_dir = os.path.join(
            GLib.get_user_config_dir(), APPLICATION_NAME)

        self.shortcuts_dir = os.path.join(self.config_dir, "shortcuts")

        self.shortcuts_reader = ShortcutsReader(self.shortcuts_dir)

        # copies the default shortcuts provided by the app into the "user data
        # dir" so he can change them.
        if not os.path.exists(self.shortcuts_dir):
            shutil.copytree(os.path.join(self.app_dir, 'data',
                                         'shortcuts'), self.shortcuts_dir)

    def create_indicator(self):
        """ Creates the indicator icon for the application """

        menu = Gtk.Menu()
        open_configs = Gtk.MenuItem("Open Shortcuts Folder")
        open_configs.connect("activate", self.open_shortcuts_folder)

        toggle_app = Gtk.MenuItem("Show shortcuts")
        toggle_app.connect("activate", self.show_shortcuts_overlay)

        close_item = Gtk.MenuItem("Quit")
        close_item.connect("activate", self.close)

        # Append the menu items
        menu.append(toggle_app)
        menu.append(open_configs)
        menu.append(close_item)

        # show menu
        menu.show_all()

        icon = os.path.join(self.app_dir, 'data', 'icon.png')
        indicator = AppIndicator3.Indicator.new(
            APPLICATION_NAME, icon, AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        indicator.set_menu(menu)

        Gtk.main()

    def do_activate(self):
        self.create_indicator()

    def close(self, widget):
        """ Closes the application. This function is called when clicking Quit in system tray menu. """

        logger.info("Closing Application")

        Gtk.main_quit()

        if self.win is not None:
            self.win.destroy()

        self.quit()

    def show_shortcuts_overlay(self, widget):
        """ Displays the shortcuts window """

        active_application = self.get_active_application()
        logger.info("Active Application is " + active_application)

        shortcuts = self.get_application_shortcuts(active_application)
        system_shortcuts = self.get_system_shortcuts()

        self.win = ShortcutsOverlay(
            self, active_application, shortcuts, system_shortcuts)
        self.win.show_all()

    def open_shortcuts_folder(self, widget):
        """ Open the folder where the shortcuts are located, using the default file manager """
        Gio.app_info_launch_default_for_uri("file://%s" % self.shortcuts_dir)

    def get_active_application(self):
        """ Returns the name of the active application based on the Window properties. """
        active_window_name = None
        screen = Wnck.Screen.get_default()
        screen.force_update()

        pid = screen.get_active_window().get_pid()
        group_name = screen.get_active_window().get_class_group_name()
        with open("/proc/{pid}/comm".format(pid=pid)) as f:
            active_window_name = f.read()

        # Fallback logic for Java Applications
        if "java" in active_window_name.lower():

            if "jetbrains" in group_name:
                return 'Jetbrains'

        if "main" in active_window_name.lower():
            if "Pinta" in group_name:
                return 'Pinta'

        return active_window_name.rstrip().title()

    def get_application_shortcuts(self, application_name):
        """ Returns the shortcuts for the current active application """

        return self.shortcuts_reader.find(application_name)

    def get_system_shortcuts(self):
        """ Returns system level shortcuts """

        return self.shortcuts_reader.find("System")
