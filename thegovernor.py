#!/usr/bin/python
import sys
import subprocess
import glob
import gtk

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
        print("exception while creating watch: %s" % str(ex))

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
                sendnotification("selected governor: %s" % self.selected_governor)
        add_watch(self.governor_paths[0], cb)

        self.menu= self.make_menu()
        self.tray = gtk.StatusIcon()
        self.tray.set_from_stock(gtk.STOCK_ABOUT) 
        self.update_icon()
        self.tray.connect('popup-menu', self.on_popup_menu)
        self.tray.connect('activate', self.on_activate)
    
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
    
    def update_icon(self):
        self.tray.set_from_stock(gtk.STOCK_EXECUTE)
        self.tray.set_tooltip("current governor: %s" % self.selected_governor)
    
    def activate_governor(self, governor):
        if self.selected_governor!=governor:
            print "selecting governor: %s" % governor
            self.selected_governor= governor
            for f in self.governor_paths:
                cmd= "sh -c 'echo %s > %s'" % (governor, f)
                cmdstr= 'gksudo "%s"' % cmd
                print "cmd string: %s" % cmdstr
                subprocess.Popen(cmdstr, shell=True)
            self.update_icon()
    
    def show_menu(self, event_button, event_time):
        self.menu.popup(None, None, gtk.status_icon_position_menu,
                   event_button, event_time, self.tray)
        
if __name__=='__main__':
    app= GovernorTrayiconApp()
    gtk.main()

