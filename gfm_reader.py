#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
#
# gfm_reader.py -- GitHub-Flavored Markdown reader for Pelican
#

import sys
import os
import ctypes
import time
import re

import pelican.readers
import pelican.utils

_LIBDIR = '/home/buildslave/slave/tools/lib'
_LIBDIR = '/Users/gstein/src/asf/infra-site/build-cmark/lib'
if sys.platform == 'darwin':
  _LIBCMARK = 'libcmark-gfm.dylib'
  _LIBEXT = 'libcmark-gfmextensions.dylib'
elif sys.platform == 'windows':
  _LIBCMARK = 'cmark-gfm.dll'
  _LIBEXT = 'cmark-gfmextensions.dll'
else:
  _LIBCMARK = 'libcmark-gfm.so'
  _LIBEXT = 'libcmark-gfmextensions.so'
try:
  cmark = ctypes.CDLL(os.path.join(_LIBDIR, _LIBCMARK))
  cmark_ext = ctypes.CDLL(os.path.join(_LIBDIR, _LIBEXT))
except OSError:
  raise ImportError('%s not found. see build-mark.sh and gfm_reader.py'
                    % _LIBCMARK)

# Options for the GFM rendering call
### this could be moved into SETTINGS or somesuch, but meh. not needed now.
OPTS = 0

# The GFM extensions that we want to use
EXTENSIONS = (
  'autolink',
  'table',
  'strikethrough',
  'tagfilter',
  )


class GFMReader(pelican.readers.BaseReader):
  """GFM-flavored Reader for the Pelican system.

  Pelican looks for all subclasses of BaseReader, and automatically
  registers them for the file extensions listed below. Thus, nothing
  further is required by users of this Reader.
  """

  # NOTE: the builtin MarkdownReader must be disabled. Otherwise, it will be
  #       non-deterministic which Reader will be used for these files.
  file_extensions = ['md', 'markdown', 'mkd', 'mdown']

  # Metadata is specified as a single, colon-separated line, such as:
  #
  # Title: this is the title
  #
  # Note: name starts in column 0, no whitespace before colon, will be
  #       made lower-case, and value will be stripped
  #
  RE_METADATA = re.compile('^([A-za-z]+): (.*)$')

  def read(self, source_path):
    "Parse content and metadata of GFM source files."

    # Prepare the "slug", which is the target file name. It will be the
    # same as the source file, minus the leading ".../content/(articles|pages)"
    # and with the extension removed (Pelican will add .html)
    relpath = os.path.relpath(source_path, self.settings['PATH'])
    parts = relpath.split(os.sep)
    parts[-1] = os.path.splitext(parts[-1])[0]  # split off ext, keep base
    slug = os.sep.join(parts[1:])

    metadata = {
      'slug': slug,
      }

    # Fetch the source content, with a few appropriate tweaks
    with pelican.utils.pelican_open(source_path) as text:

      # Extract the metadata from the header of the text
      lines = text.splitlines()
      for i in range(len(lines)):
        line = lines[i]
        match = GFMReader.RE_METADATA.match(line)
        if match:
          name = match.group(1).strip().lower()
          if name != 'slug':
            value = match.group(2).strip()
            metadata[name] = value
            #if name != 'title':
            #  print 'META:', name, value
        elif not line.strip():
          # blank line
          continue
        else:
          # reached actual content
          break

      # Reassemble content, minus the metadata
      text = '\n'.join(lines[i:])

      # Render the markdown into HTML
      if sys.version_info >= (3, 0):
        text = text.encode('utf-8')
        content = render(text).decode('utf-8')
      else:
        content = render(text)

    return content, metadata


def render(text):
  "Use cmark-gfm to render the Markdown into an HTML fragment."

  parser = F_cmark_parser_new(OPTS)
  assert parser
  for name in EXTENSIONS:
    ext = F_cmark_find_syntax_extension(name)
    assert ext
    rv = F_cmark_parser_attach_syntax_extension(parser, ext)
    assert rv
  exts = F_cmark_parser_get_syntax_extensions(parser)

  F_cmark_parser_feed(parser, text, len(text))
  doc = F_cmark_parser_finish(parser)
  assert doc

  output = F_cmark_render_html(doc, OPTS, exts)

  F_cmark_parser_free(parser)
  F_cmark_node_free(doc)

  return output


# Use ctypes to access the functions in libcmark-gfm

F_cmark_parser_new = cmark.cmark_parser_new
F_cmark_parser_new.restype = ctypes.c_void_p
F_cmark_parser_new.argtypes = (ctypes.c_int,)

F_cmark_parser_feed = cmark.cmark_parser_feed
F_cmark_parser_feed.restype = None
F_cmark_parser_feed.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t)

F_cmark_parser_finish = cmark.cmark_parser_finish
F_cmark_parser_finish.restype = ctypes.c_void_p
F_cmark_parser_finish.argtypes = (ctypes.c_void_p,)

F_cmark_parser_attach_syntax_extension = cmark.cmark_parser_attach_syntax_extension
F_cmark_parser_attach_syntax_extension.restype = ctypes.c_int
F_cmark_parser_attach_syntax_extension.argtypes = (ctypes.c_void_p, ctypes.c_void_p)

F_cmark_parser_get_syntax_extensions = cmark.cmark_parser_get_syntax_extensions
F_cmark_parser_get_syntax_extensions.restype = ctypes.c_void_p
F_cmark_parser_get_syntax_extensions.argtypes = (ctypes.c_void_p,)

F_cmark_parser_free = cmark.cmark_parser_free
F_cmark_parser_free.restype = None
F_cmark_parser_free.argtypes = (ctypes.c_void_p,)

F_cmark_node_free = cmark.cmark_node_free
F_cmark_node_free.restype = None
F_cmark_node_free.argtypes = (ctypes.c_void_p,)

F_cmark_find_syntax_extension = cmark.cmark_find_syntax_extension
F_cmark_find_syntax_extension.restype = ctypes.c_void_p
F_cmark_find_syntax_extension.argtypes = (ctypes.c_char_p,)

F_cmark_render_html = cmark.cmark_render_html
F_cmark_render_html.restype = ctypes.c_char_p
F_cmark_render_html.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)


# Set up the libcmark-gfm library and its extensions
F_register = cmark_ext.core_extensions_ensure_registered
F_register.restype = None
F_register.argtypes = ( )
F_register()

### technically, maybe install an atexit() to release the plugins
