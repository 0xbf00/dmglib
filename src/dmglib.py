"""
dmglib is a basic ``hdiutil`` wrapper that simplifies working with dmg images from Python. 

The module can be used to attach and detach disk images, to check a disk image's
validity and to query whether disk images are password protected or have a license
agreement included.
"""
import plistlib
import subprocess
import os
import enum
import sys
from contextlib import contextmanager

NAME = 'dmglib'

HDIUTIL_PATH = '/usr/bin/hdiutil'

class InvalidDiskImage(Exception):
    """The disk image is deemed invalid and therefore cannot be attached."""
    pass


class InvalidOperation(Exception):
    """An invalid operation was performed by the user.

    Examples include trying to detach a dmg that was never attached or
    trying to attach a disk image twice.
    """
    pass


class AttachingFailed(Exception):
    """Attaching failed for unknown reasons."""
    pass


class AlreadyAttached(AttachingFailed):
    """The disk image has already been attached previously."""
    pass


class PasswordRequired(AttachingFailed):
    """No password was required even though one was required."""
    pass


class PasswordIncorrect(AttachingFailed):
    """An incorrect password was supplied for the disk image."""
    pass


class LicenseAgreementNeedsAccepting(AttachingFailed):
    """Error indicating that a license agreement needs accepting."""
    pass


class DetachingFailed(Exception):
    """Error to indicate a volume could not be detached successfully."""
    pass


def _raw_hdituil(args, input: bytes = None) -> (int, bytes):
    """Invokes hdiutil with the supplied arguments and returns return code and stdout contents."""  
    if not os.path.exists(HDIUTIL_PATH):
        raise FileNotFoundError('Unable to find hdituil.')

    completed = subprocess.run([HDIUTIL_PATH] + args, 
        input=input, capture_output=True)

    return (completed.returncode, completed.stdout)


def _hdiutil(args, plist=True, keyphrase=None) -> (bool, dict):
    """Calls the command line 'hdiutil' binary with the supplied parameters.

    Args:
        args: Arguments for the hdiutil command.
        plist: Whether to ask hdiutil to return plist (dictionary) output.
        keyphrase: Optional parameter for encrypted disk images. 
    
    Returns:
        Tuple containing result status as first element and a dictionary
        containing the decoded plist response or `None` if the operation failed.
    """
    # Certain operations do not support plist output...
    if plist and '-plist' not in args:
        args.append('-plist')

    if keyphrase is not None:
        args.append('-stdinpass')

    returncode, output = _raw_hdituil(args, input=keyphrase.encode('utf8') if keyphrase else None)
    if returncode != 0:
        return False, dict()

    if plist:
        return True, plistlib.loads(output)
    else:
        return True, dict()


def _hdiutil_isencrypted(path) -> bool:
    """Checks whether a disk image is encrypted."""
    success, result = _hdiutil(['isencrypted', path])

    return success and result.get('encrypted', False)


def _hdiutil_imageinfo(path, keyphrase=None) -> (bool, dict):
    """Obtains image infos for a disk image.

    Args:
        path: The disk image for which to obtain information.
        keyphrase: Optional parameter for encrypted images.

    Returns:
        Tuple containing result status as first element and a dictionary
        containing the disk image infos obtaining from hdiutil.
    """
    return _hdiutil(['imageinfo', path], keyphrase=keyphrase)


def _hdiutil_attach(path, keyphrase=None) -> (bool, dict):
    """Attaches a disk image.

    The image is mounted using the `-nobrowse` flag so that it is not visible in
    Finder.app.

    Args:
        path: The disk image to attach.
        keyphrase: Optional parameter for encrypted images.

    Returns:
        Tuple containing status code and information on mounted volume,
        if successful.
    """
    return _hdiutil([
        'attach',
        path,
        '-nobrowse' # Do not make the mounted volumes visible in Finder.app
    ], keyphrase=keyphrase)


def _hdiutil_detach(dev_node, force=False) -> bool:
    """Detaches a disk image.

    Args:
        dev_node: Filesystem path to attached volume, e.g. `/dev/disk1s1`.
        force: Whether to ignore open files on the attached volume.

    Returns:
        Status code indicating success.
    """
    success, _ = _hdiutil(['detach', dev_node] + (['-force'] if force else []), plist=False)
    return success


def _hdiutil_info() -> (bool, dict):
    """Obtains state information about volumes attached on the system."""
    return _hdiutil(['info'])


def attached_images() -> list:
    """Obtain a list of paths to disk images that are currently attached."""
    success, infos = _hdiutil_info()

    return [ image['image-path'] 
        for image in infos.get('images', []) 
        if 'image-path' in image ]


def dmg_already_attached(path: str) -> bool:
    """Checks whether the disk image at the supplied path has already been attached.

    Querying the system for further information about already attached images fails
    with a resource exhaustion error message.
    """
    return os.path.realpath(path) in attached_images()


def dmg_is_encrypted(path: str) -> bool:
    """Checks whether DMG at the supplied path is password protected."""
    return _hdiutil_isencrypted(path)


def dmg_check_keyphrase(path: str, keyphrase: str) -> bool:
    """Checks the keyphrase for the disk image at the supplied path.

    Note:
        This function assumes the DiskImage is encrypted and raises
        an exception if it is not.

    Args:
        path: path to disk image for which to check the keyphrase
        keyphrase: keyphrase to check 

    Raises:
        InvalidOperation: the disk image was not encrypted.
    """
    if not dmg_is_encrypted(path):
        raise InvalidOperation('DiskImage is not encrypted')

    success, _ = _hdiutil_imageinfo(path, keyphrase=keyphrase)
    return success


def dmg_is_valid(path: str) -> bool:
    """Checks the validity of the supplied disk image.

    A disk image is valid according to this logic, if it is either not encrypted
    and valid according to hdiutil, or encrypted according to hdiutil.
    """
    if dmg_is_encrypted(path):
        return True

    success, _ = _hdiutil_imageinfo(path)
    return success


class MountedVolume:
    def __init__(self, mount_point, volume_kind):
        self.mount_point = mount_point
        self.volume_kind = volume_kind


class DMGState(enum.Enum):
    DETACHED = 1
    ATTACHED = 2


class DMGStatus:
    def __init__(self):
        self.status = DMGState.DETACHED
        self.mount_points = []
        self.root_dev_entry = None

    def is_attached(self) -> bool:
        return self.status == DMGState.ATTACHED

    def record_attached(self, paths, root_dev_entry):
        self.status = DMGState.ATTACHED
        self.mount_points = paths
        self.root_dev_entry = root_dev_entry

    def record_detached(self):
        self.status = DMGState.DETACHED
        self.mount_points = []


class DiskImage:
    """Class representing macOS Disk Images (.dmg) files.
    """

    def __init__(self, path, keyphrase=None):
        """Initialize a disk image object. Note: Simply constructing the object
        does not attach the DMG. Use the :py:meth:`DiskImage.attach` method for that.

        Args:
            path: The path to the disk image
            keyphrase: Optional argument for password protected images

        Raises:
            AlreadyAttached: The disk image is already attached on the system.
            InvalidDiskImage: The disk image is not a valid disk image.
            PasswordRequired: A password is required but none was provided.
            PasswordIncorrect: A incorrect password was supplied.
        """
        # The hdiutil fails when the target path has already been mounted / attached.
        if dmg_already_attached(path):
            raise AlreadyAttached()

        if not dmg_is_valid(path):
            raise InvalidDiskImage()

        if dmg_is_encrypted(path) and keyphrase is None:
            raise PasswordRequired()

        if dmg_is_encrypted(path) and not dmg_check_keyphrase(path, keyphrase):
            raise PasswordIncorrect()

        self.path       = path
        self.keyphrase  = keyphrase
        _, self.imginfo = _hdiutil_imageinfo(path, keyphrase=keyphrase)
        self.status     = DMGStatus()


    def _lookup_property(self, property_name, default_value):
        return self.imginfo\
            .get('Properties', dict())\
            .get(property_name, default_value)


    def has_license_agreement(self) -> bool:
        """Checks whether the disk image has an attached license agreement.

        DMGs with license agreements cannot be attached using this package.
        """
        return self._lookup_property('Software License Agreement', False)


    def attach(self):
        """Attaches a disk image.

        Returns:
            List of mount points.

        Raises:
            InvalidOperation: This disk image has already been attached.
            LicenseAgreementNeedsAccepting: The image cannot be automatically 
                mounted due to a license agreement.
            AttachingFailed: Could not attach the disk image or no volumes on
                mounted disk.
        """
        if self.status.is_attached():
            raise InvalidOperation()

        if self.has_license_agreement():
            raise LicenseAgreementNeedsAccepting()

        success, result = _hdiutil_attach(self.path, keyphrase=self.keyphrase)
        if not success:
            raise AttachingFailed('Attaching failed for unknown reasons.')

        mounted_volumes = [ MountedVolume(mount_point=entity['mount-point'], 
                                          volume_kind=entity['volume-kind'])
            for entity in result.get('system-entities', []) 
            if 'mount-point' in entity and 'volume-kind' in entity ]

        if len(mounted_volumes) == 0:
            raise AttachingFailed('Attaching the disk image mounted no volumes.')

        # The root dev entry is the smallest '/dev/disk...' entry when sorted
        # lexicographically. (/dev/disk2 < /dev/disk3 < /dev/disk3s1)
        # In the case of disk images containing APFS volumes, we need to detach this disk _after_
        # detaching the main volumes. This is a bug in Apple's code -- for all other types of volumes,
        # detaching the volume automatically detaches the entire disk image.
        root_dev_entry = sorted(entity['dev-entry']
            for entity in result.get('system-entities', [])
            if 'dev-entry' in entity)[0]

        self.status.record_attached(mounted_volumes, root_dev_entry)
        return [ volume.mount_point for volume in self.status.mount_points ]


    def detach(self, force=True):
        """Detaches a disk image.
    
        Args:
            force: ignore open files on mounted volumes. See `man 1 hdiutil`.

        Raises:
            InvalidOperation: The disk image was not attached on the system.
            DetachingFailed: Detaching failed for unknown reasons.
        """
        if not self.status.is_attached():
            raise InvalidOperation()

        # Detaching any mount point of an attached image automatically unmounts
        # all associated volumes.
        # ... unless one of these volumes is an APFS volume. In that case,
        # it needs to be detached separately. Additionally, the root dev entry
        # also needs to be detached explicitly.

        # First detach all APFS volumes, otherwise detaching other volumes appears to
        # succeeds but really fails with an error code (!)
        for volume in self.status.mount_points:
            if volume.volume_kind == 'apfs':
                success = _hdiutil_detach(volume.mount_point, force=force)
                if not success:
                    raise DetachingFailed()

        # Finally, detach the root dev entry.
        success = _hdiutil_detach(self.status.root_dev_entry, force=force)
        if not success:
            raise DetachingFailed()

        self.status.record_detached()


@contextmanager
def attachedDiskImage(path: str, keyphrase=None):
    """Context manager to work with a disk image.

    The context manager returns the list of mount points of the attached volumes.
    There is always at least one mount point available, otherwise attaching fails.
    The caller needs to catch exceptions (see documentation for the :class:`DiskImage`
    class), or call the appropriate methods beforehand (:meth:`dmg_is_encrypted`, ...).

    Example::
    
        with dmg.attachedDiskImage('path/to/disk_image.dmg',
                                   keyphrase='sample') as mount_points:
            print(mount_points)
    """
    dmg = DiskImage(path, keyphrase=keyphrase)
    try:
        yield dmg.attach()
    finally:
        if dmg.status.is_attached():
            dmg.detach()
