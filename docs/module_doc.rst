API documentation
=================

The most straight-forward way to use the functionality this package provides is simply to use a context manager:

.. autofunction:: dmglib.attachedDiskImage

Apart from the context manager, you may also explicitly use the `DiskImage` class:

.. autoclass:: dmglib.DiskImage
	:members:

Standalone functions
--------------------

.. autofunction:: dmglib.dmg_is_valid
.. autofunction:: dmglib.attached_images
.. autofunction:: dmglib.dmg_already_attached
.. autofunction:: dmglib.dmg_is_encrypted
.. autofunction:: dmglib.dmg_check_keyphrase
.. autofunction:: dmglib.dmg_get_mountpoints
.. autofunction:: dmglib.dmg_detach_already_attached
.. autofunction:: dmglib.dmg_create_blank

Exceptions
----------
.. autoexception:: dmglib.InvalidDiskImage
.. autoexception:: dmglib.InvalidOperation
.. autoexception:: dmglib.ConversionFailed

.. autoexception:: dmglib.AttachingFailed
.. autoexception:: dmglib.DetachingFailed
.. autoexception:: dmglib.AlreadyAttached

.. autoexception:: dmglib.PasswordRequired
.. autoexception:: dmglib.PasswordIncorrect
.. autoexception:: dmglib.LicenseAgreementNeedsAccepting

.. autoexception:: dmglib.CreatingFailed

Enumerations
------------
.. autoclass:: dmglib.DiskFormat
	:members:
	:undoc-members:

.. autoclass:: dmglib.DiskCreateBlankFormat
    :members:
    :undoc-members:

.. autoclass:: dmglib.FsFormat
    :members:
    :undoc-members:
