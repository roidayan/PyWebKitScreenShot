#!/bin/env python

import unittest
import webkitscreenshot
import gc


class TestWebKitScreenShot(unittest.TestCase):
    def setUp(self):
        size = (1024, 768)
        self.vfb = webkitscreenshot.Xvfb(display_spec='%dx%dx24' % size)
        self.assertNotEqual(self.vfb.display, None)

    def tearDown(self):
        self.vfb.close()

    def testMutliScreenShots(self):
        count = 15
        timeout = 3000
        targets = ['http://www.google.com',
                   'http://www.themarker.com',
                   'http://www.ynet.co.il'
                   ]
        for i in range(count):
            idx = i % len(targets)
            target = targets[idx]
            print 'Testing screenshot #%d %s' % (i, target)
            try:
                pixbuf = webkitscreenshot.screenshot(target, timeout=timeout)
            except Exception as e:
                self.fail(str(e))
            else:
                self.assertNotEqual(pixbuf, None)
                del pixbuf
                print len(gc.get_objects())
                gc.collect()
                print len(gc.get_objects())


if __name__ == '__main__':
    unittest.main()
