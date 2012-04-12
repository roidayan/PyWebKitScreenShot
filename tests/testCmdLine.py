#!/bin/env python

import unittest
import subprocess
import time
import os
import tempfile

def spawn(args):
    print 'cmd: %s' % ' '.join(args)
    devnull = open(os.devnull, 'w')
    p = subprocess.Popen(args, shell=False, stdout=devnull, stderr=devnull)
    t = time.time() + 5
    while (p.poll() == None and t > time.time()):
        time.sleep(1)
    if (t <= time.time()):
        print 'p timeout'
        p.terminate()
    print 'rc: %s' % str(p.returncode)
    return p.returncode


class TestCmdLine(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(os.environ.has_key('CMDPATH'), False)
        self.cmd = [os.environ['CMDPATH'] + '/webkitscreenshot.py']
        self.target = 'www.google.com'

    def testBasic(self):
        rc = spawn(self.cmd)
        self.assertNotEqual(rc, 0)

        rc = spawn(self.cmd + ['-h'])
        self.assertEqual(rc, 0)

    def testOutput(self):
        tmp = tempfile.mktemp()
        rc = spawn(self.cmd + ['-o', tmp, self.target])
        if rc == 0:
            self.assertEqual(os.path.isfile(tmp), True)
        if os.path.isfile(tmp):
            os.remove(tmp)
        self.assertEqual(rc, 0)


if __name__ == '__main__':
    unittest.main()
