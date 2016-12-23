# -*- coding: utf-8 -*-/
"""
=========
ipylatex
=========

IPython PyLaTeX bindings for using PyLaTeX in jupyter notebooks.

.. note::

  ``LaTeX`` needs to be installed.

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
from os import chdir, chmod, getcwd, environ, pathsep
from os.path import splitext
from subprocess import call
from shutil import copy
from xml.dom import minidom

from IPython.core.displaypub import publish_display_data
from IPython.core.magic import (Magics, magics_class,
                                line_cell_magic, needs_local_scope)
from IPython.core.magic_arguments import (argument, magic_arguments,
                                          parse_argstring)
from IPython.display import display, FileLinks
from IPython.testing.skipdoctest import skip_doctest

__author__ = "Sebastian Gallenmüller"
__version__ = "0.0.1"

_mimetypes = {'svg' : 'image/svg+xml'}

@magics_class
class IPyLaTeX(Magics):
    """
    A set of magics useful for creating figures with TikZ.
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


    def _run_latex(self, code, direc):
        fle = open(direc + '/tikz.tex', 'w')
        fle.write(code)
        fle.close()

        current_dir = getcwd()
        chdir(direc)

        ret_log = False
        log = None

        # Set the TEXINPUTS environment variable, which allows the tikz code
        # to reference files relative to the notebook (includes, packages, ...)
        env = environ.copy()
        if 'TEXINPUTS' in env:
            env['TEXINPUTS'] = current_dir + pathsep + env['TEXINPUTS']
        else:
            env['TEXINPUTS'] = '.' + pathsep + current_dir + pathsep*2
            # note that the trailing double pathsep will insert the standard
            # search path (otherwise we would lose access to all packages)

        try:
            retcode = call("pdflatex -shell-escape tikz.tex", shell=True,
                           env=env)
            if retcode != 0:
                print("LaTeX terminated with signal", -retcode, file=sys.stderr)
                ret_log = True
        except OSError as ex:
            print("LaTeX execution failed:", ex, file=sys.stderr)
            ret_log = True

        # in case of error return LaTeX log
        if ret_log:
            try:
                fle = open('tikz.log', 'r')
                log = fle.read()
                fle.close()
            except IOError:
                print("No log file generated.", file=sys.stderr)

        chdir(current_dir)

        return log


    def _convert_pdf_to_svg(self, direc):
        current_dir = getcwd()
        chdir(direc)

        try:
            retcode = call("pdf2svg tikz.pdf tikz.svg", shell=True)
            if retcode != 0:
                print("pdf2svg terminated with signal", -retcode, file=sys.stderr)
        except OSError as ex:
            print("pdf2svg execution failed:", ex, file=sys.stderr)

        chdir(current_dir)


    def _convert_pdf_to_png(self, direc):
        self._convert_pdf_to(direc, 'png')


    def _convert_pdf_to_jpg(self, direc):
        self._convert_pdf_to(direc, 'jpg')


    def _convert_pdf_to(self, direc, fformat):
        current_dir = getcwd()
        chdir(direc)

        try:
            retcode = call("convert -density 1200 tikz.pdf -quality 100 \
                            -density 300 -background white -flatten tikz.%s"
                           % fformat, shell=True)
            if retcode != 0:
                print("convert terminated with signal", -retcode, file=sys.stderr)
        except OSError as ex:
            print("convert execution failed:", ex, file=sys.stderr)

        chdir(current_dir)


    def _generate_document(self, doc):
        doc.generate_pdf('%s/tikz' % self.plot_dir, clean_tex=False)

    def _copy_result_files(self, save):
        for path in save:
            _, file_extension = splitext(path)
            if file_extension == '.jpg':
                copy("%s/tikz%s" % (self.plot_dir, file_extension), path)
            if file_extension == '.png':
                copy("%s/tikz%s" % (self.plot_dir, file_extension), path)
            if file_extension == '.tex':
                copy("%s/tikz%s" % (self.plot_dir, file_extension), path)
            if file_extension == '.pdf':
                copy("%s/tikz%s" % (self.plot_dir, file_extension), path)
            if file_extension == '.svg':
                copy("%s/tikz%s" % (self.plot_dir, file_extension), path)



    @skip_doctest
    @magic_arguments()
    @argument(
        '-s', '--size', action='store',
        help='Display size of document in pixel, "width,height". Default is "-s 400,240".'
        )
    @argument(
        '-S', '--save', action='append',
        help='Save a copy or several copies to "filename", \
              e.g., --save /path/save.pdf --save /path/save.tex.'
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

        # arguments 'code' in line are prepended to the cell lines
        if cell is None:
            code = ''
        else:
            code = cell

        # generate plots in a temporary directory
        self.plot_dir = tempfile.mkdtemp(dir=getcwd()).replace('\\', '/')
        chmod(self.plot_dir, 0o777)

        # add plotting function to code
        generator = """
def generate_document(doc):
    doc.generate_pdf('""" + self.plot_dir + """' + '/tikz', clean_tex=False)

"""
        code = generator  + ' '.join(args.code) + code

        # if there is no local namespace then default to an empty dict
        if local_ns is None:
            local_ns = {}


        if args.size is not None:
            size = args.size
        else:
            size = '400,240'

        width, height = size.split(',')

        key = 'PyLaTeX.Tikz'
        display_data = []


        # Execute PyLaTeX code
        ns = {}
        exec code in self.shell.user_ns, ns

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
            self._copy_result_files(args.save)

        for tag, disp_d in display_data:
            self._publish_display_data(source=tag, data=disp_d, metadata={'isolated' : 'true'})

        # file downloads
        strg = './%s' % self.plot_dir.split("/")[-1]
        local_file = FileLinks(strg)
        display(local_file)


__doc__ = __doc__.format(
    TIKZ_DOC = ' '*8 + IPyLaTeX.pylatex.__doc__,
    )


def load_ipython_extension(ipyt):
    """Load the extension in IPython."""
    ipyt.register_magics(IPyLaTeX)
