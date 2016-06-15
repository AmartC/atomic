#!/usr/bin/python -Es

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib # pylint: disable=no-name-in-module
import slip.dbus.service
from slip.dbus import polkit
from Atomic import Atomic
from Atomic.verify import Verify
from Atomic.storage import Storage
#from Atomic.diff import Diff
from Atomic.diffDbus import Diff
from Atomic.top import Top
from Atomic.scan import Scan

class atomic_dbus(slip.dbus.service.Object):
    default_polkit_auth_required = "org.atomic.readwrite"

    class Args():
        def __init__(self):
            self.image = None
            self.recurse = False
            self.debug = False
            self.devices = None
            self.driver = None
            self.graph = None
            self.force = None
            self.import_location = None
            self.export_location = None
            self.compares = []
            self.rootfs = None
            self.json = False
            self.no_files = False
            self.names_only = False
            self.rpms = False
            self.verbose = False
            self.containers = None
            self.optional = None
            self.d = None
            self.n = None

    def __init__(self, *p, **k):
	super(atomic_dbus, self).__init__(*p, **k)
        self.atomic = Atomic()

    """
    The version method takes in an image name and returns its version
    information
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='asb',
                         out_signature='aa{sv}')
    def version(self, images, recurse=False):
        versions = []
        for image in images:
            args = self.Args()
            args.image = image
            args.recurse = recurse
            self.atomic.set_args(args)
            versions.append({"Image": image,
                             "Version": self.atomic.version()})
        return versions

    """
    The verify method takes in an image name and returns whether or not the
    image should be updated
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='asb', out_signature='av')
    def verify(self, images, verbose=False):
        verifications = []
        verify = Verify()
        for image in images:
            args = self.Args()
            args.image = image
            args.verbose = verbose
            verify.set_args(args)
            verifications.append({"Image": image,
                                  "Verification": verify.verify()}) #pylint: disable=no-member
        return verifications

    """
    The storage_reset method deletes all containers and images from a system. Resets storage to its initial configuration.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='', out_signature='')
    def storage_reset(self):
        storage = Storage()
        # No arguments are passed for storage_reset function
        args = self.Args()
        storage.set_args(args)
        storage.reset()

    """
    The storage_import method imports all containers and their associated contents from a filesystem directory.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='ss', out_signature='')
    def storage_import(self, graph="/var/lib/docker", import_location="/var/lib/atomic/migrate"):
        storage = Storage()
        args = self.Args()
        args.graph = graph
        args.import_location = import_location
        storage.set_args(args)
        storage.Import()

    """
    The storage_export method exports all containers and their associated contents into a filesystem directory.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='ssb', out_signature='')
    def storage_export(self, graph="/var/lib/docker", export_location="/var/lib/atomic/migrate", force = False):
        storage = Storage()
        args = self.Args()
        args.graph = graph
        args.export_location = export_location
        args.force = force
        storage.set_args(args)
        storage.Export()

    """
    The storage_modify method modifies the default storage setup.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='asv', out_signature='')
    def storage_modify(self, devices=[], driver = None):
        storage = Storage()
        args = self.Args()
        args.devices = devices
        args.driver = driver
        storage.set_args(args)
        storage.modify()

    """
    The diff method shows differences between two container images, file diff or RPMS.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='ssb',
                         out_signature='a{sas}')
    def diff(self,first,second, rpms=False):
        diff = Diff()
        args = self.Args()
        args.compares.append(first)
        args.compares.append(second)
        args.json = False
        args.no_files = False
        args.names_only = False
        args.rpms = rpms
        args.verbose = True
        diff.set_args(args)
        return diff.diff()

    """
    The top method shows top-like stats about processes running inside containers.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='asiasi',
                         out_signature='')
    def top(self, containers = [], d=1, optional=[], n=1):
        top = Top()
        args = self.Args()
        args.containers = containers
        args.d = d
        args.optional = optional
        args.n = n
        top.set_args(args)
        top.atomic_top()

    """
    The scan method scans an image or container for CVEs.
    """
    @slip.dbus.polkit.require_auth("org.atomic.read")
    @dbus.service.method("org.atomic", in_signature='asasbbasbasb',
                         out_signature='')
    def scan(self, scan_targets=[], scanners=None, _list=False, verbose=False, rootfs=[], all=False, images=False, containers=False ):
        scan = Scan()
        args = self.Args()
        args.scan_targets = scan_targets
        args.scanners = scanners
        args.list = _list
        args.verbose = verbose
        args.rootfs - rootfs
        args.images = images
        args.containers = containers
        scan.set_args(args)
        scan.scan()


if __name__ == "__main__":
        mainloop = GLib.MainLoop()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        system_bus = dbus.SystemBus()
        name = dbus.service.BusName("org.atomic", system_bus)
        object = atomic_dbus(system_bus, "/org/atomic/object")
        slip.dbus.service.set_mainloop(mainloop)
        mainloop.run()
