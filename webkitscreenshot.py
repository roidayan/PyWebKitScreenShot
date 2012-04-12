#!/usr/bin/env python
"""
web page screenshot by webkit
found on github gist @bellbind
Modified by Roi Dayan

command usage:
  python webkitscreenshot.py test.html
  python webkitscreenshot.py -s 200,150 -t 6000 test.html

library usage:
  import webkitscreenshot
  pixbuf = webkitscreenshot.screenshot_vfb('file://test.html')
  pixbuf.save('screenshot.png', 'png')
  image = webkitscreenshot.thumbnail(pixbuf, (200, 150))
  image.save('thumbnail.png')

required libs:
- pygtk: http://www.pygtk.org/
- pywebkitgtk(python-webkit): http://code.google.com/p/pywebkitgtk/

optional libs:
- PIL: http://www.pythonware.com/products/pil/

required tools and resouces:
- Xvfb: if you use virtual framebuffer
- VLGothic: as default truetype font

Changes:
2012-04-12  Not getting document height when choosing size.
              This is to avoid stretching of the image.
2012-04-09  Changed vfb() to class Xvfb
            Handle more exceptions
            Added log prints
            Waiting for defunct Xvfb procs
            Checking if X display is busy from lock files
2012-04-07  Added timeout
            Fixed capturing height of document
            Default is capturing the entire document
            PIL is only used to create thumbnail from capture
            Fixed cmdline font option
            Other changes
"""

import os
import sys
import subprocess
import tempfile


DEFAULT_FONT='VLGothic'


def _ps_xvfb():
    print '-- ps --'
    proc = subprocess.Popen('ps -ef|grep -i xvfb|grep -v grep', shell=True)
    proc.wait()
    print '-- -- --'

def screenshot(url, **args):
    """
    get screenshot
    - url: screenshot url (if local file: file://...)
    - font_size: default font size
    - font_default: default font family
    - font_serif: serif font
    - font_sans_serif: sans-serif font
    - font_monospace: monospace font
    - size: tuple (width, height) as image size. fullscreen if None

    - return: gdk.Pixbuf object
    """
    return _WebKitScreenShot(url, **args).pixbuf

def screenshot_vfb(url, **args):
    """
    runs Xvfb
    get screenshot in Xvfb
    close Xvfb
    - same parameters and results as screenshot()
    - size: (1024, 768) as default
    """
    size = args.pop('size', (1024, 768))
    vfb = Xvfb(display_spec='%dx%dx24' % size)
    if not vfb.display:
        print 'Error creating display'
        return None
    print 'Xvfb: %d %s' % (vfb.proc.pid, vfb.display)
    try:
        return screenshot(url, **args)
    finally:
        print 'Terminate vfb %d' % vfb.proc.pid
        vfb.close()


class _WebKitScreenShot(object):
    """
    make fullscreen webkit window
    then take a screenshot into self.pixbuf
    """
    def __init__(self, url,
                 font_size=14,
                 font_default=DEFAULT_FONT,
                 font_serif=DEFAULT_FONT,
                 font_sans_serif=DEFAULT_FONT,
                 font_monospace=DEFAULT_FONT,
                 size=None,
                 auto_height=True,
                 timeout=3000):
        self.auto_height=auto_height
        self.pixbuf = None
        self.timeout = False
        try:
            import gtk
            import webkit
            import gobject
        except Exception as e:
            print 'Failed import: %s' % str(e)
            return

        self.timeout_tag = gobject.timeout_add(timeout, self._timeout)
        gtk.gdk.threads_init()

        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.move(0, 0)
        if not size:
            size = (gtk.gdk.screen_width(), gtk.gdk.screen_height())
        window.set_default_size(*size)
        webview = webkit.WebView()

        # webkit settings
        settings = webkit.WebSettings()
        settings.set_property('serif-font-family', font_serif)
        settings.set_property('sans-serif-font-family', font_sans_serif)
        settings.set_property('monospace-font-family', font_monospace)
        settings.set_property('default-font-family', font_default)
        settings.set_property('default-font-size', font_size)
        webview.set_settings(settings)

        window.add(webview)

        window.connect('destroy', lambda wid: gtk.main_quit())
        window.connect('delete-event', lambda window, event: gtk.main_quit())
        #webview.connect('notify::load-status', self._load_status_cb)
        webview.connect('load-finished', self._loaded)
        webview.load_uri(url)
        window.show_all()

        self.size = size
        self.window = window
        self.webview = webview
        print 'Window size: %s' % str(window.get_size())
        gtk.main()

    #def _load_status_cb(self, view, spec):
    #    status = view.get_property('load-status')

    def _timeout(self):
        print 'timeout'
        self.timeout = True
        self.webview.stop_loading()
        return False

    def _getHeight(self):
        self.webview.execute_script('oldtitle=document.title;\
             document.title=document.documentElement.offsetHeight;')
        height = self.webview.get_main_frame().get_title()
        self.webview.execute_script('document.title=oldtitle;')
        return int(height)

    def _loaded(self, view, frame):
        import gtk
        import gobject
        if not self.timeout:
            gobject.source_remove(self.timeout_tag)
        width, height = self.size
        if self.auto_height:
            height = min(height, self._getHeight())
        self.pixbuf_size = (width, height)
        print 'Get pixbuf size:%d,%d' % self.pixbuf_size
        if height > 0:
            try:
                # see: http://www.pygtk.org/docs/pygtk/class-gdkpixbuf.html
                pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,
                                        False, 8, width, height)
                pixbuf.get_from_drawable(view.window, view.window.get_colormap(),
                                         0, 0, 0, 0, width, height)
                self.pixbuf = pixbuf
            except Exception as e:
                print 'Failed pixbuf: %s' % str(e)
                #import traceback
                #traceback.print_exc()
                pass
        self.webview.destroy()
        self.window.destroy()
        gtk.main_quit()


class Xvfb(object):
    """
    Xvfb display
    usage:
      vfb = Xvfb()
      import gtk
      ...
      vfb.close()
    """

    def __init__(self, display_spec='1024x768x24', display=99, screen=0):
        """
        run Xvfb and set DISPLAY env
        """
        #if os.environ.get('DISPLAY', None):
        #    return (None, os.environ['DISPLAY'])
        self.fbdir = None
        self.proc = None
        self.display = None
        display = self.find_free_display(display)
        print 'use display: %d' % display
        if display:
            devnull = open(os.devnull, 'w')
            fbdir = tempfile.mkdtemp()
            try:
                proc = subprocess.Popen(
                    ['Xvfb', ':%d' % display,
                     '-screen', `screen`, display_spec,
                     '-fbdir', fbdir,
                     '-nolisten', 'tcp'],
                    shell=False, stdout=devnull, stderr=devnull)
            except Exception as e:
                os.rmdir(fbdir)
                print 'Error: %s' % str(e)
            else:
                self.display = ':%d.%d' % (display, screen)
                os.environ['DISPLAY'] = self.display
                self.fbdir = fbdir
                self.proc = proc
        _ps_xvfb()

    def close(self):
        """
        close Xvfb and unset display
        """
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
            self.proc = None
            os.environ.pop('DISPLAY')
        if self.fbdir:
            os.rmdir(self.fbdir)
            self.fbdir = None

    def find_free_display(self, display=99):
        ret = None
        for i in range(3):
            print 'Try :%d' % display
            lockfile = '/tmp/.X%d-lock' % display
            if os.path.isfile(lockfile):
                try:
                    f = open(lockfile)
                    pid = int(f.readline().strip())
                    f.close()
                except:
                    continue
                else:
                    if os.path.exists('/proc/%d' % pid):
                        print 'X :%d is busy' % display
                        display += 1
                        continue
            ret = display
            break
        return ret


def thumbnail(pixbuf, thumbsize=(200, 150)):
    """
    @return: Image object
    """
    import Image
    size = (pixbuf.get_width(), pixbuf.get_height())
    image = Image.fromstring('RGB', size,
                             pixbuf.get_pixels())
    image.thumbnail(thumbsize, Image.ANTIALIAS)
    return image

def _main():
    thumbsize = 'all'
    thumbfile = 'screenshot.png'
    font = DEFAULT_FONT
    timeout = 3000

    from optparse import OptionParser
    parser = OptionParser()
    parser.usage += ' URL'
    parser.add_option('-s', '--size', dest='size',
                      help='output image size: w,h',
                      default=None)
    parser.add_option('-o', '--output', dest='output',
                      help='output image filename: %s' % thumbfile,
                      default=thumbfile)
    parser.add_option('-f', '--font', dest='font',
                      help='default font: %s' % font,
                      default=font)
    parser.add_option('-t', '--timeout', dest='timeout', type='int',
                      help='default timeout: %s' % timeout,
                      default=timeout)

    opts, args = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(-1)

    thumbfile = opts.output
    timeout = opts.timeout
    thumbsize = opts.size
    font = opts.font

    url = args[0]
    if not url.startswith('http'):
        url = 'file://' + url

    if not thumbsize:
        vfbsize = (1024, 3000)
    else:
        vfbsize = (1024, 768)
        try:
            thumbsize = tuple(map(int, thumbsize.split(',')))
        except:
            thumbsize = ''
        if len(thumbsize) != 2:
            print 'Bad thumbsize'
            sys.exit(-1)

    pixbuf = screenshot_vfb(url, size=vfbsize, auto_height=(not thumbsize),
                            timeout=timeout,
                            font_default=font, font_sans_serif=font,
                            font_serif=font, font_monospace=font)
    if pixbuf:
        if not thumbsize:
            pixbuf.save(thumbfile, 'png')
        else:
            print 'Thumbnail: %s' % str(thumbsize)
            image = thumbnail(pixbuf, thumbsize)
            image.save(thumbfile)
            del image
        del pixbuf
    print 'Done'

if __name__ == '__main__':
    _main()
