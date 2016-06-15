import sys

import dbus
import dbus.service
import dbus.mainloop.glib
from slip.dbus import polkit


class AtomicDBus (object):
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.dbus_object = self.bus.get_object("org.atomic",
                                               "/org/atomic/object")

    @polkit.enable_proxy
    def version(self, image, recurse):
        ret = self.dbus_object.version(image, recurse,
                                        dbus_interface="org.atomic")
        return ret
    @polkit.enable_proxy
    def verify(self, image):
        ret = self.dbus_object.verify(image, dbus_interface="org.atomic")
        return ret

    @polkit.enable_proxy
    def storage_reset(self):
        self.dbus_object.storage_reset(dbus_interface="org.atomic")

    @polkit.enable_proxy
    def storage_import(self, graph, import_location):
        self.dbus_object.storage_import(graph, import_location, dbus_interface="org.atomic")

    @polkit.enable_proxy
    def storage_export(self, graph, export_location, force):
        self.dbus_object.storage_export(graph, export_location, force, dbus_interface="org.atomic")

    @polkit.enable_proxy
    def storage_modify(self, devices, driver):
        self.dbus_object.storage_import(devices, driver, dbus_interface="org.atomic")

    @polkit.enable_proxy
    def diff(self, first, second, rpms):
        ret = self.dbus_object.diff(first, second, rpms, dbus_interface="org.atomic")
        return ret

    @polkit.enable_proxy
    def top(self, interval, optional, num_iterations):
        self.dbus_object.top([],interval, optional, num_iterations, dbus_interface="org.atomic")

    @polkit.enable_proxy
    def scan(self, scan_targets, scanners, _list, verbose, rootfs, images, containers):
        self.dbus_object.scan([],[], True, False, False, True, False, dbus_interface="org.atomic")

if __name__ == "__main__":
    try:
        dbus_proxy = AtomicDBus()
    except dbus.DBusException as e:
        print e

    if(sys.argv[1] == "version"):
        if sys.argv[2] == "-r":
            try:
                resp = dbus_proxy.version(sys.argv[3:], True)
            except dbus.DBusException as e:
                print e
        else:
            try:
                resp = dbus_proxy.version(sys.argv[2:], False)
            except dbus.DBusException as e:
                print e

        for r in resp:
            for v in r["Version"]:
                print(str(v["Id"]), str(v["Version"]), str(v["Tag"]))

    elif(sys.argv[1] == "verify"):
        try:
            resp = dbus_proxy.verify(sys.argv[2:])

            for r in resp:
                print r
        except dbus.DBusException as e:
            print e

        except ValueError as v:
            print v

    elif(sys.argv[1] == "storage"):
        if(sys.argv[2] == "export"):
            try:
                dbus_proxy.storage_export("/var/lib/Docker", "/var/lib/atomic/migrate", False)

            except dbus.DBusException as e:
                print e

            except ValueError as v:
                print v

        elif(sys.argv[2] == "import"):
            try:
                dbus_proxy.storage_import("/var/lib/Docker", "/var/lib/atomic/migrate")

            except dbus.DBusException as e:
                print e

            except ValueError as v:
                print v

        elif(sys.argv[2] == "reset"):
            try:
                dbus_proxy.storage_reset()

            except dbus.DBusException as e:
                print e

            except ValueError as v:
                print v

    elif(sys.argv[1] == "diff"):
        try:
            resp = dbus_proxy.diff(sys.argv[2], sys.argv[3], True)
            for key in resp.keys():
                print key
                for data in resp[key]:
                    print data

        except dbus.DBusException as e:
            print e

        except ValueError as v:
            print v

    elif(sys.argv[1] == "top"):
        try:
            resp = dbus_proxy.top(1,[],1)

        except dbus.DBusException as e:
            print e

        except ValueError as v:
            print v

    elif(sys.argv[1] == "scan"):
        try:
            resp = dbus_proxy.scan([],[],True, False, False, True, False)
            print resp

        except dbus.DBusException as e:
            print e

        except ValueError as v:
            print v




    #dbus_proxy.storage_export("/var/lib/Docker", "/var/lib/atomic/migrate", False)
