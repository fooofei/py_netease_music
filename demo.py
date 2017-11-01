# coding=utf-8
# python2

import os
import sys

curpath = os.path.dirname(os.path.realpath(__file__))

from netease import PlaylistWrapper
from netease import result_show

def sort_playlist(id_1):
  from io_in_out import io_print

  ins = PlaylistWrapper()
  b = ins.sorted_by_tracks_ar(id_1)
  io_print(u'ok' if b else u'fail')


def entry():
  pass


if __name__ == '__main__':
  entry()
