# dmglib

`dmglib` is a tiny python wrapper built around the `hdiutil` command line tool on macOS. It is intended to be used to work with the contents of DMG files on macOS.

`dmglib` provides functions for the following tasks:
* Querying the list of currently attached disk images on the system
* Checking whether a target disk image is password-protected
* Checking whether a given password is correct for a target disk image
* Attaching and detaching disk images