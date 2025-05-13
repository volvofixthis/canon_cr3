# parse CR3 (and CR2) file format from Canon (@lorenzo2472)
# from https://github.com/lclevy/canon_cr3
# tested with Python 3.6.7
# about ISO Base file format : https://stackoverflow.com/questions/29565068/mp4-file-format-specification
# License is GPLv3 

import sys
from struct import unpack, Struct
from binascii import hexlify, unhexlify
from optparse import OptionParser
from collections import namedtuple, OrderedDict


def getShortBE(d, a):
 return unpack('>H',(d)[a:a+2])[0]

def getShortLE(d, a):
 return unpack('<H',(d)[a:a+2])[0]
 
def getLongBE(d, a):
 return unpack('>L',(d)[a:a+4])[0]

def getLongLE(d, a):
 return unpack('<L',(d)[a:a+4])[0]
 
def getLongLongBE(d, a):
 return unpack('>Q',(d)[a:a+8])[0]

from CRaw3.TiffIfd import TiffIfd
from CRaw3.Jpeg import Jpeg      
from CRaw3.Cr2 import Cr2      
from CRaw3.Crx import Crx
from CRaw3.Ctmd import Ctmd      
   

def getIfd(name, details): # details is dict with 'picture', 'type', 'tag'
  if name in { b'CMT1', b'CMT2', b'CMT3', b'CMT4', b'CMTA' }:
    return cr3[name][1]
  elif name== b'CTMD':   
    if 'picture' in details:
      pic_num = details[ 'picture' ]
    else:
      pic_num = 0   
    ctmd = cr3[b'CTMD'].ctmd_list[ pic_num ]  
    if 'type' in details:
      if details[ 'type' ] in Ctmd.CTMD_TIFF_TYPES:
        for ctmd_record in ctmd.values():
          if ctmd_record.type == details[ 'type' ]:
            for subdir_tag, tiff_subdir in ctmd_record.content.items():
              offset, payload_size, payload_tag, entries = tiff_subdir
              if details[ 'tag' ] == payload_tag:
                return entries[1]
  return None                 
    
#CTMD INDEX, content is in mdat
def ctmd(d, l, depth, base, name):
  _ctmd = Ctmd(d, l, base, name ) #parse index

  return _ctmd

#to parse Canon CR3 ISO Base File format 
def ftyp(b, d, l, depth):
  major_brand = d[:4]
  minor_version = getLongBE(d, 4)
  compatible_brands = []
  for e in range( (l-(4*4))//4 ):
    compatible_brands.append( d[8+e*4:8+e*4+4] )
  
def moov(b, d, l, depth):
    pass

def uuid(b, d, l, depth):
  uuidValue = d[:16]
  return uuidValue  

def stsz(b, d, l, depth):
  S_STSZ = Struct('>BBBBLL') #size==12
  version, f1, f2, f3, size, count = S_STSZ.unpack_from(d, 0) 
  flags = f1<<16 | f2<<8 | f3
  size_list = []
  if size!=0:
    for s in range(count):
      size_list.append( size )  
  else: 
    for s in range(count):
      sample_size = getLongBE(d, 12+s*4)
      size_list.append( sample_size )
  return size_list
  
def co64(b, d, l, depth):
  version = getLongBE(d, 0)
  count = getLongBE(d, 4)
  offset_list = []
  for o in range(count):
    offset_list.append( getLongLongBE(d, 8+o*8) )
  return offset_list
  
S_PRVW = Struct('>LHHHHL')
def prvw(b, d, l, depth):
  NT_PRVW = namedtuple('prvw', 'w h size')
  _, _, w, h, _, jpegSize = S_PRVW.unpack_from(d, 0)
  _prvw = NT_PRVW( w, h, jpegSize)
  return _prvw
  
S_THMB = Struct('>LHHLHH')
def thmb(b, d, l, depth):
  NT_THMB = namedtuple('thmb', 'w h size')
  _, w, h, jpegSize, _, _ = S_THMB.unpack_from(d, 0)
  _thmb = NT_THMB( w, h, jpegSize)
  return _thmb
  
CTBO_LINE_LEN = 20  
def ctbo(b, d, l, depth):
  S_CTBO_LINE = Struct('>LQQ')
  NT_CTBO_LINE = namedtuple('ctbo_line', 'index offset size')
  nbLine = getLongBE( d, 0 )
  offsetList = {}
  for n in range( nbLine ):
    idx, offset, size = S_CTBO_LINE.unpack_from( d, 4 + n*S_CTBO_LINE.size ) 
    _ctbo_line = NT_CTBO_LINE( idx, offset, size )
    offsetList[idx] = _ctbo_line
  return offsetList  
    

def cncv(b, d, l, depth):    
  return d[:]

def cdi1(b, d, l, depth):
  pass

def iad1(b, d, l, depth):
  pass

#offset does start after name, thus +8 when including size (long) and name (4*char)	
def cmp1(b, d, l, depth):    
  S_CMP1 = Struct('>HHHHLLLLBBBBL') 
  NT_CMP1 = namedtuple('cmp1', 'iw ih tw th d p cfa extra wl b35 hsize')
  _, size, version, _, iw, ih, tw, th, _32, _33, _34, b35, hsize = S_CMP1.unpack_from(d, 0)
  bits = int(_32)
  planes = int(_33)>>4
  cfa = int(_33)&0xf
  extra = int(_34)>>4
  wavelets = int(_34)&0xf
  cmp = NT_CMP1(iw, ih, tw, th, bits, planes, cfa, extra, wavelets, b35, hsize)
  return cmp	
  
def craw(b, d, l, depth):
  S_CRAW = Struct('>LL16sHHHHHHLH32sHHHH')
  NT_CRAW = namedtuple('craw', 'w h bits')
  _, _, _, w, h, _, _, _, _, _, _, _, bits, _, _, _ = S_CRAW.unpack_from(d, 0)
  #print(S_CRAW.unpack_from(d, 0))
  _craw = NT_CRAW( w, h, bits)
  #print(_craw)
  return _craw

def cnop(b, d, l, depth):
  return


  
tags = { b'ftyp':ftyp, b'moov':moov, b'uuid':uuid, b'stsz':stsz, b'co64':co64, b'PRVW':prvw, b'CTBO':ctbo, b'THMB':thmb, b'CNCV':cncv,
         b'CDI1':cdi1, b'IAD1':iad1, b'CMP1':cmp1, b'CRAW':craw, b'CNOP':cnop }  

innerOffsets = { b'CRAW': 0x52, b'CCTP':12, b'stsd':8, b'dref':8, b'CDI1':4 }         
         
count = dict()
#keep important values
cr3 = dict()

NAMELEN = 4
SIZELEN = 4
UUID_LEN = 16
#base for this atom (length will be added to this base)
#o = offset inside
#no = next offset after name and length 
def parse(offset, d, base, depth):
  o = 0
  #print('base=0x%x offset=0x%x'% (base, offset))
  while o < len(d):
    l = getLongBE(d, o)
    chunkName = d[o+SIZELEN:o+SIZELEN+NAMELEN]
    no = SIZELEN+NAMELEN #next offset to look for data
    if l==1:
      l = getLongLongBE(d, o+SIZELEN+NAMELEN)
      no = SIZELEN+NAMELEN+8
    dl = min(32, l) #display length
    
    if chunkName not in count: #enumerate atom to create unique ID
      count[ chunkName ] = 1
    else:  
      count[ chunkName ] = count[ chunkName ] +1
    if chunkName == b'trak':  #will keep stsz and co64 per trak
      trakName = 'trak%d' % count[b'trak']
      if trakName not in cr3:
        cr3[ trakName ] = dict()    
      
    if chunkName in tags: #dedicated parsing
      r = tags[chunkName](base, d[o+no:o+no +l-no], l, depth+1) #return results
    elif chunkName in { b'CMT1', b'CMT2', b'CMT3', b'CMT4', b'CMTA' }:
      tiff = TiffIfd( d[o+no:o+no +l-no], l, base+o+no, chunkName, False )
      cr3[ chunkName ] = ( base+o+no, tiff )
    elif chunkName == b'CTMD':
      r = ctmd( d[o+no:o+no +l-no], l, depth+1, base+o+no, chunkName )
      cr3[ chunkName ] = r 
       
    if chunkName in { b'moov', b'trak', b'mdia', b'minf', b'dinf', b'stbl' }: #requires inner parsing, just after the name
      parse( offset+o+no, d[o+no:o+no +l-no], base+o+no, depth+1)
    elif chunkName == b'uuid':  #inner parsing at specific offsets after name
      uuidValue = d[ o+no: o+no +UUID_LEN ] #it depends on uuid values
      if uuidValue == unhexlify('85c0b687820f11e08111f4ce462b6a48') or uuidValue == unhexlify('5766b829bb6a47c5bcfb8b9f2260d06d') or uuidValue == unhexlify('210f1687914911e4811100242131fce4'):
        parse(offset+o+no+UUID_LEN, d[o+no+UUID_LEN:o+no+UUID_LEN +l-no-UUID_LEN], base+o+no+UUID_LEN, depth+1)
      elif uuidValue == unhexlify('eaf42b5e1c984b88b9fbb7dc406e4d16'):
        parse(offset+o+no+UUID_LEN+8, d[o+no+UUID_LEN+8:o+no+UUID_LEN+8 +l-no-8-UUID_LEN], base+o+no+UUID_LEN+8, depth+1)
    elif chunkName in innerOffsets: #it depends on chunkName
      start = o+no+innerOffsets[chunkName]
      end = start +l-no-innerOffsets[chunkName]
      parse( offset+start, d[start:end], start, depth+1 )
      
    #post processing  
    if chunkName == b'stsz' or chunkName == b'co64' or chunkName == b'CRAW' or chunkName == b'CMP1':  #keep these values per trak
      trakName = 'trak%d' % count[b'trak']
      cr3[ trakName ][ chunkName ] = r
    elif chunkName == b'CNCV' or chunkName == b'CTBO':  
      cr3[ chunkName ] = r
    elif chunkName == b'PRVW' or chunkName == b'THMB':
      cr3[ chunkName ] = base+o+no, r  #save chunk offset
    elif chunkName == b'uuid':
      if uuidValue == unhexlify('210f1687914911e4811100242131fce4'):
        cr3[ uuidValue ] = o #save offset    
    o += l  
  return o

  
