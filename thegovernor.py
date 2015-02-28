#!/usr/bin/python
# thegovernor - Switch CPU governor from notification area
# Copyright (C) 2015 Johannes Kroll
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import sys
import subprocess
import glob
import gtk
import gobject

def sendnotification(message):
    subprocess.Popen(['notify-send', message])

def add_watch(path, callback):
    # create an inotify CLOSE_WRITE watch for path for use with gtk+ main loop
    try:
        import inotifyx
        import gobject
        fd= inotifyx.init()
        wd= inotifyx.add_watch(fd, path, inotifyx.IN_CLOSE_WRITE)
        def handle_watch(source, condition):
            inotifyx.get_events(fd)
            callback(path)
            sys.stdout.flush()
            return True
        gobject.io_add_watch(fd, gobject.IO_IN, handle_watch)
    except Exception as ex:
        sendnotification("exception while creating watch: %s" % str(ex))

class GovernorTrayiconApp:
    def __init__(self):
        self.governor_paths= glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor")
        
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors") as f:
            self.available_governors= f.readline().split()
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
            self.selected_governor= f.readline().strip()
            
        # create watch for scaling_governor sysfs file for cpu0 so we get notified of changes
        def cb(path):
            with open(path) as f:
                governor= f.readline().strip()
                index= self.available_governors.index(governor)
            if governor!=self.selected_governor:
                self.governor_items[index].activate()
                self.update_icon()
                sendnotification("'%s' governor activated" % self.selected_governor)
        add_watch(self.governor_paths[0], cb)

        self.menu= self.make_menu()
        self.tray= gtk.StatusIcon()
        self.tray.set_visible(True)
        self.tray.connect('popup-menu', self.on_popup_menu)
        self.tray.connect('activate', self.on_activate)
        
        self.icon_freq= 0
        self.update_icon()
        def cb(): 
            self.update_icon()
            return True
        gobject.timeout_add(1000, cb)
    
    def set_dynicon(self, text):
        window= gtk.OffscreenWindow()
        label= gtk.Label()
        label.set_justify(gtk.JUSTIFY_CENTER)
        label.set_markup(text)
        eb= gtk.EventBox()
        eb.add(label)
        #~ eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('green')) # xxxx no effect?
        window.add(eb)
        def draw_complete_event(window, event, statusIcon=self.tray):
            statusIcon.set_from_pixbuf(window.get_pixbuf())
        window.connect("damage-event", draw_complete_event)
        window.show_all()
    
    def make_menu(self):
        menu= gtk.Menu()
        item= None
        self.governor_items= []
        for governor in self.available_governors:
            item= gtk.RadioMenuItem(item, governor)
            item.connect('activate', lambda widget: self.activate_governor(widget.get_label()))
            if(governor == self.selected_governor):
                item.activate()
            item.show()
            menu.append(item)
            self.governor_items.append(item)
        item= gtk.SeparatorMenuItem()
        item.show()
        menu.append(item)
        quit= gtk.MenuItem("Quit")
        quit.show()
        quit.connect('activate', gtk.main_quit)
        menu.append(quit)
        return menu

    def on_popup_menu(self, icon, event_button, event_time):
        self.show_menu(event_button, event_time)
    
    def on_activate(self, status_icon):
        #~ self.show_menu(1, 0)
        pass
    
    def get_max_freq(self):
        max= 0
        for path in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"):
            with open(path) as f:
                khz= int(f.readline().strip())
                if khz>max: max= khz
        return max
    
    def update_icon(self):
        maxfreq= self.get_max_freq()
        if maxfreq != self.icon_freq:
            self.set_dynicon("<small>%3.1f\nGhz</small>" % (float(self.get_max_freq())/1000000) )
            self.icon_freq= maxfreq
        self.tray.set_tooltip("active governor: %s\n%d cores @ %3.1f GHz max" % 
            (self.selected_governor, len(self.governor_paths), float(maxfreq)/1000000))
    
    def activate_governor(self, governor):
        if self.selected_governor!=governor:
            print "selecting governor: %s" % governor
            self.selected_governor= governor
            cmdstr= 'gksudo "bash -c \'echo %s | tee %s\'"' % (governor, ' '.join(self.governor_paths))
            subprocess.Popen(cmdstr, shell=True)
            self.update_icon()
    
    def show_menu(self, event_button, event_time):
        self.menu.popup(None, None, gtk.status_icon_position_menu,
                   event_button, event_time, self.tray)
        
if __name__=='__main__':
    app= GovernorTrayiconApp()
    gtk.main()

