import os
import sys
import rpm
from filecmp import dircmp
from . import util
from . import mount
from . import Atomic

''' This file will handle both dbus calls and regular calls from Atomic '''

class Diff(Atomic):

    def diff_tty(self):
        '''
        Prints diff information depending on what parameters are passed by the user.
        :return: None
        '''
        diff_dict = self.diff()
        images = self.args.compares

        if not self.args.no_files and not self.args.json:
            self.output_files(images, diff_dict)

        if self.args.rpms and not self.args.json:
            self.output_rpms(images, diff_dict)

        if self.args.json:
            util.output_json(diff_dict)


    def print_release(self, first_release, second_release, _max, two_col):
        '''
        Prints the release information and splits based on the column length
        :return: None
        '''
        step = _max - 2
        r1_split = [first_release.strip()[i:i+step] for i in range(0, len(first_release.rstrip()), step)]
        r2_split = [second_release.strip()[i:i+step] for i in range(0, len(second_release.rstrip()), step)]
        for n in list(range(max(len(r1_split), len(r2_split)))):
            col1 = r1_split[n] if 0 <= n < len(r1_split) else ""
            col2 = r2_split[n] if 0 <= n < len(r2_split) else ""
            util.write_out(two_col.format(col1, col2))

    def diff(self):
        '''
        Allows you to 'diff' the RPMs between two different docker images|containers.
        :return: None
        '''
        diff_dict = dict()
        helpers = DiffHelpers(self.args)
        images = self.args.compares
        # Check to make sure each input is valid
        for image in images:
            self.get_input_id(image)

        first_image = images[0]
        second_image = images[1]
        image_list = helpers.create_image_list(images)
        diff_dict[first_image] = dict()
        diff_dict[second_image] = dict()
        diff_dict["Both"] = dict()

        try:
            # Set up RPM classes and make sure each docker object
            # is RPM-based
            rpm_image_list = []
            if self.args.rpms:
                for image in image_list:
                    rpmimage = RpmDiff(image.chroot, image.name, self.args.names_only)
                    if not rpmimage.is_rpm:
                        helpers._cleanup(image_list)
                        raise ValueError("{0} is not RPM based.".format(rpmimage.name))
                    rpmimage._get_rpm_content()
                    rpm_image_list.append(rpmimage)
            file_diff = DiffFS(image_list[0].chroot, image_list[1].chroot)
            diff_dict[first_image]["first_release"] = (rpm_image_list[0]).release
            diff_dict[second_image]["second_release"] = (rpm_image_list[1]).release

            if not self.args.no_files:
                diff_dict[first_image]["first_only"] = file_diff.left
                diff_dict[second_image]["second_only"] = file_diff.right
                diff_dict["Both"]["files_differ"] = file_diff.common_diff

            if self.args.rpms:
                ip = RpmPrint(rpm_image_list)
                diff_dict[first_image]["first_rpm"] = []
                diff_dict[second_image]["second_rpm"] = []
                if ip.has_diff:
                    for rpm in ip.all_rpms:
                        if rpm in ip.i1.rpms and rpm in ip.i2.rpms:
                            diff_dict[first_image]["first_rpm"].append(rpm)
                            diff_dict[second_image]["second_rpm"].append(rpm)

                        elif rpm in ip.i1.rpms:
                            diff_dict[first_image]["first_rpm"].append(rpm)

                        elif rpm in ip.i2.rpms:
                            diff_dict[second_image]["second_rpm"].append(rpm)

            helpers._cleanup(image_list)

            return diff_dict

        except KeyboardInterrupt:
            util.write_out("Quitting...")
            helpers._cleanup(image_list)


    def output_files(self, images, diff_dict):
        '''
        Outputs the different files between two images using the helper function _print_diff
        :return: None
        '''
        def _print_diff(file_list):
            '''
            Helper function to output diff contents with appropriate formatting
            :return: None
            '''
            for _file in file_list:
                util.write_out("{0}{1}".format(5*" ", _file))

        first_image_only = diff_dict[images[0]]["first_only"]
        second_image_only = diff_dict[images[1]]["second_only"]
        both_images = diff_dict["Both"]["files_differ"]

        if all([len(first_image_only) == 0, len(second_image_only) == 0,
                len(both_images) == 0]):
            util.write_out("\nThere are no file differences between {0} "
                          "and {1}".format(images[0], images[1]))
        if len(first_image_only) > 0:
            util.write_out("\nFiles only in {}:".format(images[0]))
            _print_diff(first_image_only)

        if len(second_image_only) > 0:
            util.write_out("\nFiles only in {}:".format(images[1]))
            _print_diff(second_image_only)

        if len(both_images):
            util.write_out("\nCommon files that are different:")
            _print_diff(both_images)

    def output_rpms(self, images, diff_dict):
        '''
        Outputs the different rpms between two images using the helper function _print_diff
        :return: None
        '''
        def _max_rpm_name_length(all_rpms):
            _max = max([len(x) for x in all_rpms])
            return _max if _max >= 30 else 30
        first_image = images[0]
        second_image = images[1]
        first_image_rpms = diff_dict[first_image]["first_rpm"]
        second_image_rpms = diff_dict[second_image]["second_rpm"]

        all_rpms = sorted(list(set(first_image_rpms) | set(second_image_rpms)))
        _max = _max_rpm_name_length(all_rpms)
        two_col = "{0:" + str(_max) + "} | {1:" \
                       + str(_max) + "}"
        has_diff = False if set(first_image_rpms) == set(second_image_rpms) \
            else True

        # If differences present between the rpms of two containers then display the diff.
        if has_diff:
            util.write_out("")
            util.write_out(two_col.format(first_image, second_image))
            util.write_out(two_col.format("-"*_max, "-"*_max))
            self.print_release(diff_dict[first_image]["first_release"], diff_dict[second_image]["second_release"], _max, two_col)
            util.write_out(two_col.format("-"*_max, "-"*_max))
            for rpm in all_rpms:
                if (rpm in first_image_rpms) and (rpm in second_image_rpms):
                    if self.args.verbose:
                        util.write_out(two_col.format(rpm, rpm))
                elif (rpm in first_image_rpms) and not (rpm in second_image_rpms):
                    util.write_out(two_col.format(rpm, ""))
                elif not (rpm in first_image_rpms) and (rpm in second_image_rpms):
                    util.write_out(two_col.format("", rpm))
        else:
            if self.args.names_only:
                util.write_out("\n{} and {} has the same RPMs.  Versions may differ.  Remove --names-only"
                " to see if there are version differences.".format(first_image, second_image))

            else:
                util.write_out("\n{} and {} have no different RPMs".format(first_image, second_image))


class DiffHelpers(object):
    '''
    Helper class for the diff function
    '''
    def __init__(self, args):
        self.args = args
        self.json_out = {}

    @staticmethod
    def _cleanup(image_list):
        '''
        Class the cleanup def
        :param image_list:
        :return: None
        '''
        for image in image_list:
            image._remove()

    @staticmethod
    def create_image_list(images):
        '''
        Instantiate each image into a class and then into
        image_list
        :param images:
        :return: list of image class instantiations
        '''
        image_list = []
        for image in images:
            try:
                image_list.append(DiffObj(image))
            except mount.SelectionMatchError as e:
                if len(image_list) > 0:
                    DiffHelpers._cleanup(image_list)
                sys.stderr.write("{}\n".format(e))
                sys.exit(1)
        return image_list

class DiffObj(object):
    def __init__(self, docker_name):
        self.dm = mount.DockerMount("/tmp", mnt_mkdir=True)
        self.name = docker_name
        self.root_path = self.dm.mount(self.name)
        self.chroot = os.path.join(self.root_path, "rootfs")

    def _remove(self):
        '''
        Stub to unmount, remove the devmapper device (if needed), and
        remove any temporary containers used
        :return: None
        '''
        self.dm.unmount()


class RpmDiff(object):
    '''
    Class for handing the parsing of images during an
    atomic diff
    '''
    def __init__(self, chroot, name, names_only):
        self.chroot = chroot
        self.name = name
        self.is_rpm = self._is_rpm_based()
        self.rpms = None
        self.release = None
        self.names_only = names_only

    def _get_rpm_content(self):
        '''
        Populates the release and RPM information
        :return: None
        '''
        self.rpms = self._get_rpms(self.chroot)
        self.release = self._populate_rpm_content(self.chroot)

    def _is_rpm_based(self):
        '''
        Determines if the image is based on RPM
        :return: bool True or False
        '''
        if os.path.exists(os.path.join(self.chroot, 'usr/bin/rpm')):
            return True
        else:
            return False

    def _get_rpms(self, chroot_os):
        '''
        Pulls the NVRs of the RPMs in the image
        :param chroot_os:
        :return: sorted list pf RPM NVRs
        '''
        ts = rpm.TransactionSet(chroot_os)
        ts.setVSFlags((rpm._RPMVSF_NOSIGNATURES | rpm._RPMVSF_NODIGESTS))
        image_rpms = []
        enc=sys.getdefaultencoding()
        for hdr in ts.dbMatch():  # No sorting  # pylint: disable=no-member
            name = hdr['name'].decode(enc)
            if name == 'gpg-pubkey':
                continue
            else:
                if not self.names_only:
                    foo = "{0}-{1}-{2}-{3}".format(name,
                                                   hdr['epochnum'],
                                                   hdr['version'].decode(enc),
                                                   hdr['release'])

                else:
                    foo = "{0}".format(name)
                image_rpms.append(foo)
        return sorted(image_rpms)

    @staticmethod
    def _populate_rpm_content(chroot_os):
        '''
        Get the release on the imageTrue
        :param chroot_os:
        :return: string release name
        '''
        etc_release_path = os.path.join(chroot_os,
                                        "etc/redhat-release")
        os_release = open(etc_release_path).read()
        return os_release


class RpmPrint(object):
    '''
    Class to handle the output of atomic diff
    '''
    def __init__(self, image_list):
        def _max_rpm_name_length(all_rpms):
            _max = max([len(x) for x in all_rpms])
            return _max if _max >= 30 else 30

        self.image_list = image_list
        self.i1, self.i2 = self.image_list
        self.all_rpms = sorted(list(set(self.i1.rpms) | set(self.i2.rpms)))
        self._max = _max_rpm_name_length(self.all_rpms)
        self.two_col = "{0:" + str(self._max) + "} | {1:" \
                       + str(self._max) + "}"
        self.has_diff = False if set(self.i1.rpms) == set(self.i2.rpms) \
            else True

    def _rpm_json(self):
        '''
        Pretty prints the output in json format
        :return: None
        '''
        def _form_image_json(image, exclusive, common):
            return {
                "release": image.release,
                "all_rpms": image.rpms,
                "exclusive_rpms": exclusive,
                "common_rpms": common
            }
        l1_diff = sorted(list(set(self.i1.rpms) - set(self.i2.rpms)))
        l2_diff = sorted(list(set(self.i2.rpms) - set(self.i1.rpms)))
        common = sorted(list(set(self.i1.rpms).intersection(self.i2.rpms)))
        json_out = {}
        json_out[self.i1.name] = _form_image_json(self.i1, l1_diff, common)
        json_out[self.i2.name] = _form_image_json(self.i2, l2_diff, common)
        return json_out


class DiffFS(object):
    '''
    Primary class for doing a diff on two docker objects
    '''
    def __init__(self, chroot_left, chroot_right):
        self.compare = dircmp(chroot_left, chroot_right)
        self.left = []
        self.right = []
        self.common_diff = []
        self.chroot_left = chroot_left
        self.chroot_right = chroot_right
        self.delta(self.compare)

    def _get_only(self, _chroot):
        '''
        Simple function to return the right diff using the chroot path
        as a key
        :param _chroot:
        :return: list of diffs for the chroot path
        '''
        return self.left if _chroot == self.chroot_left else self.right

    @staticmethod
    def _walk(walkdir):
        '''
        Walks the filesystem at the given walkdir
        :param walkdir:
        :return: list of files found
        '''
        file_list = []
        walk = os.walk(walkdir)
        for x in walk:
            (_dir, dir_names, files) = x
            if len(dir_names) < 1 and len(files) > 0:
                for _file in files:
                    file_list.append(os.path.join(_dir, _file).encode('utf-8'))
            elif len(dir_names) < 1 and len(files) < 1:
                file_list.append(_dir.encode('utf-8'))
        return file_list

    def delta(self, compare_obj):
        '''
        Primary function for performing the recursive diff
        :param compare_obj:  a dircomp object
        :return: None
        '''
        # Removing the fs path /tmp/<docker_obj>/rootfs
        _left_path = compare_obj.left.replace(self.chroot_left, '')
        _right_path = compare_obj.right.replace(self.chroot_right, '')

        # Add list of common files but files appear different
        for common in compare_obj.diff_files:
            self.common_diff.append(os.path.join(_left_path, common))

        # Add the diffs from left
        for left in compare_obj.left_only:
            fq_left = os.path.join(_left_path, left)
            self.left.append(fq_left)
            if os.path.isdir(fq_left):
                walk = self._walk(fq_left)
                self.left += walk

        # Add the diffs from right
        for right in compare_obj.right_only:
            fq_right = os.path.join(_right_path, right)
            self.right.append(os.path.join(_right_path, right))
            if os.path.isdir(fq_right):
                walk = self._walk(fq_right)
                self.right += walk

        # Follow all common subdirs
        for _dir in compare_obj.subdirs.values():
            self.delta(_dir)
