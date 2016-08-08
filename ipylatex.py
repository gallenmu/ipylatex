# -*- coding: utf-8 -*-/
"""
=========
ipylatex
=========
 
ipython PyLaTeX bindings for using PyLaTeX in jupyter notebooks.
 
.. note::
 
  ``TikZ`` and ``LaTeX`` need to be installed separately.
 
Usage
=====
 
``%%pylatex``
 
{TIKZ_DOC}
 
"""
 
#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------
from __future__ import print_function 
import sys
import tempfile
from glob import glob
from os import chdir, getcwd, environ, pathsep
from subprocess import call
from shutil import rmtree, copy
from xml.dom import minidom

from IPython.core.displaypub import publish_display_data
from IPython.core.magic import (Magics, magics_class, line_magic,
                                line_cell_magic, needs_local_scope)
from IPython.testing.skipdoctest import skip_doctest
from IPython.core.magic_arguments import (
    argument, magic_arguments, parse_argstring
)
from IPython.utils.py3compat import unicode_to_str

from pylatex import Document, Section, Subsection, Tabular, Math, TikZ, Axis, \
    Plot, Figure, Package, Matrix
from pylatex.utils import italic
import os

from IPython.display import display, FileLink, FileLinks

__author__ = "Sebastian Gallenmüller"
__version__ = "0.0.1"

_mimetypes = {'png' : 'image/png',
              'svg' : 'image/svg+xml',
              'jpg' : 'image/jpeg',
              'jpeg': 'image/jpeg'}
 
@magics_class
class IPyLaTeX(Magics):
    """A set of magics useful for creating figures with TikZ.
    """
    def __init__(self, shell):
        """
        Parameters
        ----------
        shell : IPython shell
 
        """
        super(IPyLaTeX, self).__init__(shell)
 
        # Allow publish_display_data to be overridden for
        # testing purposes.
        self._publish_display_data = publish_display_data

    plot_dir = ''
 
    def _fix_gnuplot_svg_size(self, image, size=None):
        """
        GnuPlot SVGs do not have height/width attributes.  Set
        these to be the same as the viewBox, so that the browser
        scales the image correctly.
 
        Parameters
        ----------
        image : str
            SVG data.
        size : tuple of int
            Image width, height.
 
        """
        (svg,) = minidom.parseString(image).getElementsByTagName('svg')
        viewbox = svg.getAttribute('viewBox').split(' ')
 
        if size is not None:
            width, height = size
        else:
            width, height = viewbox[2:]
 
        svg.setAttribute('width', '%dpx' % width)
        svg.setAttribute('height', '%dpx' % height)
        return svg.toxml()


    def _run_latex(self, code, dir):
        f = open(dir + '/tikz.tex', 'w')
        f.write(code)
        f.close()

        current_dir = getcwd()
        chdir(dir)

        ret_log = False
        log = None

        # Set the TEXINPUTS environment variable, which allows the tikz code
        # to refence files relative to the notebook (includes, packages, ...)
        env = environ.copy()
        if 'TEXINPUTS' in env:
            env['TEXINPUTS'] =  current_dir + pathsep + env['TEXINPUTS']
        else:
            env['TEXINPUTS'] =  '.' + pathsep + current_dir + pathsep*2
            # note that the trailing double pathsep will insert the standard
            # search path (otherwise we would lose access to all packages)

        try:
            retcode = call("pdflatex -shell-escape tikz.tex", shell=True,
                           env=env)
            if retcode != 0:
                print("LaTeX terminated with signal", -retcode, file=sys.stderr)
                ret_log = True
        except OSError as e:
            print("LaTeX execution failed:", e, file=sys.stderr)
            ret_log = True

        # in case of error return LaTeX log
        if ret_log:
            try:
                f = open('tikz.log', 'r')
                log = f.read()
                f.close()
            except IOError:
                print("No log file generated.", file=sys.stderr)

        chdir(current_dir)

        return log


    def _convert_pdf_to_svg(self, dir):
        current_dir = getcwd()
        chdir(dir)
        
        try:
            retcode = call("pdf2svg tikz.pdf tikz.svg", shell=True)
            if retcode != 0:
                print("pdf2svg terminated with signal", -retcode, file=sys.stderr)
        except OSError as e:
            print("pdf2svg execution failed:", e, file=sys.stderr)
        
        chdir(current_dir)


    def _convert_pdf_to_png(self, dir):
        current_dir = getcwd()
        chdir(dir)
        
        try:
            retcode = call("convert -density 1200 tikz.pdf -quality 100 -density 300 -background white -flatten tikz.png", shell=True)
            if retcode != 0:
                print("convert terminated with signal", -retcode, file=sys.stderr)
        except OSError as e:
            print("convert execution failed:", e, file=sys.stderr)
 
        chdir(current_dir)
        
 
    def _convert_pdf_to_jpg(self, dir):
        current_dir = getcwd()
        chdir(dir)
        
        try:
            retcode = call("convert -density 1200 tikz.pdf -quality 100 -density 300 -background white -flatten tikz.jpg", shell=True)
            if retcode != 0:
                print("convert terminated with signal", -retcode, file=sys.stderr)
        except OSError as e:
            print("convert execution failed:", e, file=sys.stderr)
 
        chdir(current_dir)
    
    def _generate_document(self, doc):
        doc.generate_pdf('%s/tikz' % self.plot_dir, clean_tex=False)
 
    @skip_doctest
    @magic_arguments()
    @argument(
        '-s', '--size', action='store',
        help='Pixel size of plots, "width,height". Default is "-s 400,240".'
        )
    @argument(
        '-l', '--library', action='store',
        help='TikZ libraries to load, separated by comma, e.g., -l matrix,arrows.'
        )
    @argument(
        '-S', '--save', action='store',
        help='Save a copy to "filename".'
        )
 
    @needs_local_scope
    @argument(
        'code',
        nargs='*',
        )
    @line_cell_magic
    def pylatex(self, line, cell=None, local_ns=None):
        '''
        '''
        args = parse_argstring(self.pylatex, line)

        # debug log
        f = open('debug.log', 'w')
 
        # arguments 'code' in line are prepended to the cell lines
        if cell is None:
            code = ''
            return_output = True
        else:
            code = cell
            return_output = False
 
        code = ' '.join(args.code) + code
        f.write(code)
        f.write('\n')

        # if there is no local namespace then default to an empty dict
        if local_ns is None:
            local_ns = {}
 
        # generate plots in a temporary directory
        self.plot_dir = tempfile.mkdtemp(dir=getcwd()).replace('\\', '/')
        os.chmod(self.plot_dir , 0o777)
        f.write(self.plot_dir)
        #print(plot_dir, file=sys.stderr)
        
        if args.size is not None:
            size = args.size
        else:
            size = '400,240'
 
        width, height = size.split(',')
 
        if args.library is not None:
            tikz_library = args.library.split(',')
        else:
            tikz_library = None
 
        add_params = ""
        
        key = 'PyLaTeX.Tikz'
        display_data = []

        # Execute PyLaTeX code
        exec(code)

        self._convert_pdf_to_svg(self.plot_dir)
        self._convert_pdf_to_jpg(self.plot_dir)
        self._convert_pdf_to_png(self.plot_dir)

        image_filename = "%s/tikz.svg" % (self.plot_dir)
        
        # Publish image
        try:
            image = open(image_filename, 'rb').read()
            plot_mime_type = _mimetypes.get('svg', 'image/svg')
            width, height = [int(s) for s in size.split(',')]
            image = self._fix_gnuplot_svg_size(image, size=(width, height))
            display_data.append((key, {plot_mime_type: image}))
 
        except IOError:
            print("No image generated.", file=sys.stderr)
        
        # Copy output file if requested
        if args.save is not None:
            copy(image_filename, args.save)
        
        for tag, disp_d in display_data:
            self._publish_display_data(source=tag, data=disp_d, metadata={'isolated' : 'true'})

        # file downloads
        st = './%s' % self.plot_dir.split("/")[-1]
        local_file = FileLinks(st)
        display(local_file)

        f.close()
 
 
__doc__ = __doc__.format(
    TIKZ_DOC = ' '*8 + IPyLaTeX.pylatex.__doc__,
    )
 
 
def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(IPyLaTeX)
