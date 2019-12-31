import os
import sys
import shutil
import hashlib
import tempfile
import unittest
from functools import wraps
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False

import rpmfile

def download(url, rpmname):
    def _downloader(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            args = list(args)
            rpmpath = os.path.join(args[0].tempdir, rpmname)
            args.append(rpmpath)
            download = urlopen(url)
            with open(rpmpath, 'wb') as target_file:
                target_file.write(download.read())
            download.close()
            return func(*args, **kwds)
        return wrapper
    return _downloader

class TempDirTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.prevdir = os.getcwd()
        cls.tempdir = tempfile.mkdtemp()
        os.chdir(cls.tempdir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)
        os.chdir(cls.prevdir)

    @unittest.skipUnless(HAS_LZMA, 'Need lzma module')
    @download('https://download.clearlinux.org/releases/10540/clear/x86_64/os/Packages/sudo-setuid-1.8.17p1-34.x86_64.rpm', 'sudo.rpm')
    def test_lzma_sudo(self, rpmpath):
        with rpmfile.open(rpmpath) as rpm:

            # Inspect the RPM headers
            self.assertIn('name', rpm.headers.keys())
            self.assertEqual(rpm.headers.get('arch', 'noarch'), b'x86_64')

            members = list(rpm.getmembers())
            self.assertEqual(len(members), 1)

            fd = rpm.extractfile('./usr/bin/sudo')

            calculated = hashlib.md5(fd.read()).hexdigest()
            self.assertEqual(calculated, 'a208f3d9170ecfa69a0f4ccc78d2f8f6')


    @download('https://download.fedoraproject.org/pub/fedora/linux/releases/30/Everything/source/tree/Packages/r/rpm-4.14.2.1-4.fc30.1.src.rpm', 'sample.rpm')
    def test_autoclose(self, rpmpath):
        """Test that RPMFile.open context manager properly closes rpm file"""

        rpm_ref = None
        with rpmfile.open(rpmpath) as rpm:
            rpm_ref = rpm

            # Inspect the RPM headers
            self.assertIn('name', rpm.headers.keys())
            self.assertEqual(rpm.headers.get('arch', 'noarch'), b'x86_64')

            members = list(rpm.getmembers())
            self.assertEqual(len(members), 13)

        # Test that RPMFile owned file descriptor and that underlying file is really closed
        self.assertTrue(rpm_ref._fileobj.closed)
        self.assertTrue(rpm_ref._ownes_fd)
