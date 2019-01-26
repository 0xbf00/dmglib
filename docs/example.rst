Example
=======

The following example program attempts to mount the supplied disk image and iterates over the files in the root directory of all its mount points. Note that error handling has largely been ignored to keep the example as simple as possible::

    import dmglib
    import sys
    import os


    def main():
        if len(sys.argv) <= 1:
            print("Usage: program dmgpath")
            return

        dmgpath = sys.argv[1]
        dmg = dmglib.DiskImage(dmgpath)

        if dmg.has_license_agreement():
            print("Cannot attach disk image.")
            return

        for mount_point in dmg.attach():
            for entry in os.listdir(mount_point):
                print('{} -- {}'.format(mount_point, entry))

        dmg.detach()


    if __name__ == '__main__':
        main()