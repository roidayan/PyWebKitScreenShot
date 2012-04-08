#!/usr/bin/env python
"""
web page screenshot by webkit
found on github gist @bellbind
Modified by Roi Dayan

command usage:
  python webkitscreenshot.py test.html
  python webkitscreenshot.py -s 200x150 -t 6000 test.html

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
2012-04-07  Added timeout
            Fixed capturing height of document
            Default is capturing the entire document
            PIL is only used to create thumbnail from capture
            Fixed cmdline font option
            Other changes
"""


DEFAULT_FONT='VLGothic'


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
    get screenshot in Xvfb
    - same parameters and results as screenshot()
    - size: (1024, 768) as default
    """
    size = args.pop('size', (1024, 768))
    proc, display = vfb(display_spec='%dx%dx24' % size)
    if not display:
        print 'Error creating display'
        return None
    print proc, display
    try:
        return screenshot(url, **args)
    finally:
        if proc:
            proc.terminate()


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
                 timeout=3000):
        self.pixbuf = None
        self.timeout = False
        try:
            import gtk
            import webkit
            import gobject
        except Exception as e:
            print 'Failed import: %s' % str(e)
            return

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

        self.timeout_tag = gobject.timeout_add(timeout, self._timeout)
        
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
        try:
            width, height = self.size
            height = min(height, self._getHeight())
            print 'Get pixbuf size:%d,%d' % (width, height)
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
        gtk.main_quit()

def vfb(display_spec='1024x768x24', server=0, screen=0, auto_screen=True):
    """
    run Xvfb and set DISPLAY env
    
    usage:
      proc, display = xvf()
      import gtk
      ...
      if proc:
          proc.terminate()
    """
    import subprocess
    import os
    #if os.environ.get('DISPLAY', None):
    #    return (None, os.environ['DISPLAY'])
    retries = 3
    while True:
        try:
            devnull = open('/dev/null', 'w')
            proc = subprocess.Popen(
                ['Xvfb', ':%d' % server,
                 '-screen', `screen`, display_spec],
                shell=False, stdout=devnull, stderr=devnull)
            os.environ['DISPLAY'] = ':%d.%d' % (server, screen)
            return (proc, os.environ['DISPLAY'])
        except Exception as e:
            print 'Error: %s' % str(e)
            #import traceback
            #traceback.print_exc()
            if not auto_screen:
                break
            screen += 1
            retries -= 1
            if retries <= 0:
                break
    return (None, '')

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
        import sys
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
    pixbuf = screenshot_vfb(url, size=vfbsize, timeout=timeout,
                           font_default=font, font_sans_serif=font,
                           font_serif=font, font_monospace=font)
    if pixbuf:
        if not thumbsize:
            pixbuf.save(thumbfile, 'png')
        else:
            thumbsize = tuple(map(int, thumbsize.split(',')))
            if len(thumbsize ) < 2:
                print 'Error size'
            else:
                print 'Thumbnail: %s' % str(thumbsize)
                image = thumbnail(pixbuf, thumbsize)
                image.save(thumbfile)
                del image
        del pixbuf
    print 'Done'

if __name__ == '__main__':
    _main()
