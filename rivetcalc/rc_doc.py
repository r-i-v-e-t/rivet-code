
#!
import codecs
import datetime
import sys
import os
import shutil
import codecs
from numpy import *
import numpy.linalg as LA
from sympy import *
from sympy import var as varsym
from sympy import printing
from sympy.core.alphabets import greeks
import once.config as cfg
import rivet.rivet_doc
from once.calcheck import ModCheck
from once.calpdf import *
from rivet.rivet_unit import *
try:
    from PIL import Image as PImage
    from PIL import ImageOps as PImageOps
except:
    pass

__version__ = "0.9.0"
__author__ = 'rholland'


class ExecRST(object):
    """Write PDF file.
    ::

        Arguments:
            odict (ordered dict) : model dictionary
        
        Files written:
            _cfilepdf   : PDF calc file name  
            _rstfile    : reST file name     
            _texfile    : tex file name
            _auxfile    : auxiliary file name 
            _outfile    : out file name 
            _texmak2    : fls file name 
            _texmak3    : latexmk file name
    
        Operation keys, number of parameters and associated tags:
            _r + line number - 7 - [r] run 
            _i + line number - 6 - [i] insert
            _v + line number - 4 - [v] value            
            _e + line number - 7 - [e] equation
            _t + line number - 9 - [t] table
            _s + line number - 3 - [s] sectionsm,kl
            _~ + line number - 1 - blank line
            _x + line number - 2 - pass-through text
            _y + line number - 2 - value heading
            _lt              - 2 - license text [licensetext]
            _#              - 1 - control line
    
    
            [r]    p0   |   p1     |   p2    |   p3   |    p4   |   p5    
                  'os'     command     arg1      arg2      arg3     arg4 
                  'py'     script      arg1      arg2      arg3     arg4     
                 
            [i]    p0   |   p1     |  p2      |   p4      |   p5         
                  'fg'     figure     caption    size       location
                  'tx'     text     
                  'md'     model
                  'fn'     function   var name   reference 
                  'rd'     file       var name   vector or table
                  'wr'     file       var name
                        
            [v]   p0  |  p1   |    p2    |    p3              
                  var    expr   statemnt    descrip 
    
            [e]   p0  |  p1    |    p2   |    p3      |  p4   |  p5   |  p6       
                 var     expr    statemnt    descrip     dec1    dec2     units 
            
            [t]   p0 |  p1  |  p2  |  p3  |  p4    |   p5   | p6   | p7  | p8
                  var  expr  state1  desc   range1   range2   dec1   un1   un2
            
            [s]   p0          | p1         |        p2    |   p3           
                  left string    calc number     sect num   toc flag
    """


    def __init__(self, odict1):
        """Initialize parameters for UTF calc.
        ::

         Arguments:
            odict1 (dictionary):  model dictionary
        """
        # dicts and lists
        self.vbos = cfg.verboseflag
        self.el = ModCheck()
        self.odict = odict1
        self.symb = self.odict.keys()
        self.symblist = []

        # paths and files
        self.rfile = cfg.rstfile
        self.figpath = cfg.ipath
        #print('rest file name', cfg.rstfile)        
        self.rf1 = codecs.open(self.rfile, 'w', encoding='utf8')
        # parameters
        self.fignum = 0
        self.widthp = 70
        self.xtraline = False
        self.prfilename = ''
        self.previous = ''
        self.literalflag = 0
        self.lastsect = ''
        self.lastcalcnumber = ''

    def gen_rst(self):
        """ Parse model dictionary and write rst file.

        """
                
        self.xtraline = True
        for _i in self.odict:               # execute dictionary line by line
            mtag = _i[0:2]
            mvals = self.odict[_i]
            #print('rstmtag', mtag, _i, mvals, mvals[0])
            if mvals[2:9] == '#- page':                 #- add page break
                print(' ', file=self.rf1)
                print(".. raw:: latex", file=self.rf1)
                print(' ', file=self.rf1)
                print('  \\newpage', file=self.rf1)
                print(' ', file=self.rf1)
                self.el.logwrite("pdf new page", self.vbos)
            if mvals[2:4] == '#-':
                if isinstance(str(mvals.strip())[-1], int):       # add spaces
                    _numspace = eval(mvals.strip()[-1])
                    for _i in range(_numspace):
                        self._rst_blank()
            if mtag ==   '_r':                
                self._rst_run(self.odict[_i])
            elif mtag == '_i':
                self._rst_ins(self.odict[_i])
            elif mtag == '_v':
                self._rst_val2(self.odict[_i])
            elif mtag == '_e':
                self._rst_eq(self.odict[_i])
            elif mtag == '_t':
                self._rst_table(self.odict[_i])
            elif mtag == '_s':
                self._rst_sect(self.odict[_i])
                self.xtraline = False
            elif mtag == '_x':
                self._rst_txt(self.odict[_i])
                self.xtraline = False
            elif mtag == '_y':
                self._rst_val1(self.odict[_i])
                self.xtraline = False
            else:
                pass
            if mtag == '_~':
                self._rst_blnk()
                continue
            if self.xtraline:
                self._rst_blnk()
        
        if '_lt' in self.odict:                  # add calc license
            self._rst_txt(self.odict[_i2],0)
        #for _i in self.odict: print(i, self.odict[i])
        self._rst_terms()                       # add term definitions
        self._rst_blnk()
        self._rst_txt(['  **[end of calc]**'])  # end calc
        self.rf1.close()                          # close rst file
        self.el.logwrite("< reST file written >", self.vbos)


    def _rst_txt(self, txt):
        """Print pass-through text.
          arguments:
            txt (string): text that is not part of an tag

        """
        #print('txt ',txt)
        if txt[0][0:3] == '  |' :                       # handle lines
            print(txt[0][2:].rstrip(), file=self.rf1)
            self.xtraline = False
        elif txt[0][0:3] == '  `' :                     # handle literal
            if self.literalflag == 2:
                self.literalflag = 0
            if self.literalflag == 1:
                self.literalflag = 2
            print('  ', file=self.rf1)
            self.xtraline = False     
        elif txt[0][0:4] == '  ::' :                    # handle literal
            print(txt[0][2:].rstrip(), file=self.rf1)
            self.literalflag = 1
            self.xtraline = False        
        elif txt[0][0:4] == '  ..' :                    # handle raw
            print(txt[0][2:].rstrip(), file=self.rf1)                
            self.xtraline = False        
        else:
            print(txt[0][2:].rstrip(), file=self.rf1)
            self.xtraline = True


    def _rst_blnk(self):
        """Print blank line.

        """
        if self.literalflag == 2:                       # handle literal
            print('  ', file=self.rf1)
            self.xtraline = False     
        else:
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{3mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ', file=self.rf1)


    def _rst_run(self, dval2):

        """        

            [r]   p0 |   p1   |   p2     |   p3    |   p4   |    p5   |   p6    
                        'os'     command     arg1      arg2      arg3     arg4 
                        'py'     script      arg1      arg2      arg3     arg4     
        """
        pass

    
    def _rst_ins(self, dval2):
        """Insert file data into or from reST        
            
            [i]      p0    |   p1     |   p2      |   p3   |   p4         
                    'fig'     file       caption     size     location
                    'text'    file       reference        
                    'lit'     file       reference
                    'csv'     file       
                    'mod'     file      
                    'func'    file       var name   reference 
                    'read'    file       var name   vector or table
                    'write'   file       var name
                    'app'     file       var name
    
            only the first three letters of p0 are read
            
        """
        option = ""
        fpath = ""
        fp = ""
        var2 = ""
        var3 = "100"
        var4 = "center"
                            
        option = dval2[0].strip()[0:3]
        fname = dval2[1].strip()
        fp =  os.path.join(self.figpath,fname)
        var2 = dval2[2].strip()
        var3 = dval2[3].strip()
        var4 = dval2[4].strip()

        if option == 'fig':
            if var4[0:1] == 'r' : var4 = 'right'
            elif var4[0:1] == 'l' : var4 = 'left'
            elif var4[0:1] == 'c' : var4 = 'center'            
            else: var4 = 'center'
            print(' ', file=self.rf1)
            print('.. figure:: ' + fp, file=self.rf1)
            print('   :width: ' + var3 + ' %', file=self.rf1)
            print('   :align: ' + var4, file=self.rf1)
            print('   ', file=self.rf1)
            print('   ' + var2, file=self.rf1)
            print(' ', file=self.rf1)
            self.el.logwrite("< figure "+fname+" added to TeX >", self.vbos)

       def vrst(self):
        """compose rst calc string for values

        Return:

        """
        pass

    def _rst_val1(self, dval2):
        """Print value description to reST.
            key: values        
            _y :  p0                | p1
                 block description    eqnum       
        """
        #print('dval2', dval2)

        descrip = dval2[0].strip()
        eqnum = dval2[1].strip()
        # equation reference line
        print('  ', file=self.rf1)
        print(".. raw:: latex", file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\vspace{7mm}', file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\hfill\\textbf{'+descrip+ ' ' +eqnum +'}', file=self.rf1)
        print('  ', file=self.rf1)


    def _rst_val2(self, dval2):
        """Print values to reST:
        
            key: values    
            _v :   p0  |   p1  |  p2      |    p3            
                 var     expr     statemnt   descrip     
                 
        """
        val1 = eval(dval2[1])
        ptype = type(val1)
        var1 = dval2[0].strip()
        state = var1 + ' = ' + str(val1)
        shift = int(self.widthp / 2.0)
        ref = dval2[3].strip().ljust(shift)
        valuepdf = " "*4 + ref + ' | ' + state
        if ptype == ndarray or ptype == list or ptype == tuple:
            shift = int(self.widthp / 2.1)
            ref = dval2[3].strip().ljust(shift)
            tmp1 = str(val1)
        if ptype == ndarray:
            if '[[' in tmp1:
                tmp2 = tmp1.replace(' [', '.  [')
                tmp1 = tmp2.replace('[[', '. [[')
            else:
                tmp1 = tmp1.replace('[', '. [')
            valuepdf = '. ' + ref + ' | ' + var1 + ' = ' + tmp1
        elif ptype == list or ptype == tuple:
            if ']]' in tmp1:
                tmp1 = tmp1.replace(']]', ']]\n')
            else:
                tmp1 = tmp1.replace(']', ']\n')
            valuepdf = '. ' + ref + ' | ' + var1 + ' = ' + tmp1
        print('  ', file=self.rf1)
        print('::', file=self.rf1)
        print('  ', file=self.rf1)
        print(valuepdf, file=self.rf1)
        print('  ', file=self.rf1)
        print('  ', file=self.rf1)


    def _rst_eq(self, dval):
        """Print equation to reST:
        
            key : _e + line number  
            value:  p0  |  p1     |  p2   |   p3    |  p4  | p5   |  p6  |  p7       
                    var   expr      state    descrip   dec1  dec2   unit   eqnum

        """
        try:                                # set decimal format
            eformat, rformat = str(dval[4]).strip(), str(dval[5]).strip()
            exec("set_printoptions(precision=" + eformat.strip() + ")")
            exec("Unum.VALUE_FORMAT = '%." + eformat.strip() + "f'")
            #print('eformat',eformat, rformat)
        except:
            eformat = '3'
            rformat = '3'
            set_printoptions(precision=3)
            Unum.VALUE_FORMAT = "%.3f"
        try:        
            eunit = dval[6].strip()
            #print('eunit', eunit)
        except:
            eunit = ' '
        var0 = dval[0].strip()
        for k1 in self.odict:                  # evaluate values and equations      
            if k1[0:2] in ['_v','_e']:
                    try:
                        exec(self.odict[k1][2].strip())
                    except:
                        pass  
        descrip = dval[3].strip()              # equation reference line
        eqnum = dval[7].strip()
        print('  ', file=self.rf1)
        print(".. raw:: latex", file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\vspace{7mm}', file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\hfill\\textbf{'+descrip+ ' ' +eqnum +'}', file=self.rf1)
        print('  ', file=self.rf1)
        for _j in self.odict:                       # symbolic form
            if _j[0:2] in ['_v','_e']:
                #print(str(self.odict[_j][0]))
                varsym(str(self.odict[_j][0]))
        try:                                        # try sympy processing
            symeq = sympify(dval[1].strip())
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{3mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('.. math:: ', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(symeq, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{4mm}', file=self.rf1)
            print('  ', file=self.rf1)
        except:                                    # otherwise write ASCII form
            symeq = dval[1].strip()
            print('  ', file=self.rf1)
            print('::', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + symeq, file=self.rf1)
            print('  ', file=self.rf1)
        try:                                # substitute values for variables
            symat = symeq.atoms(Symbol)
            latexrep = latex(symeq, mul_symbol="dot")
            #print('latex1', latexrep)
            switch1 = []
            for _n in symat:              # rewrite latex equation with braces
                #print('_n1', _n)
                newlatex1 = str(_n).split('__')
                if len(newlatex1) == 2:
                    newlatex1[1] += '}'
                    newlatex1 = '~d~'.join(newlatex1)
                newlatex1 = str(_n).split('_')
                if len(newlatex1) == 2:
                    newlatex1[1] += '}'
                    newlatex1 = '~s~'.join(newlatex1)
                newlatex1 = ''.join(newlatex1)
                newlatex1 = newlatex1.replace('~d~', '__{')
                newlatex1 = newlatex1.replace('~s~', '_{')
                #print('newlatex1', newlatex1)
                switch1.append([str(_n), newlatex1])
            for _n in switch1:                    
                #print('_n2', _n)
                expr1 = eval(_n[0])
                if type(expr1) == float:                # set sub decimal points
                    form = '{:.' + eformat.strip() +'f}'
                    symvar1 = '{' + form.format(expr1) + '}'
                else:
                    symvar1 = '{' + str(expr1) + '}'
                #print('replace',_n[1], symvar1)
                latexrep = latexrep.replace(_n[1], symvar1)
                latexrep = latexrep.replace("\{", "{")
                #print('latex2', latexrep)
            print('  ', file=self.rf1)                  # add equation to rst file
            print('.. math:: ', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latexrep, file=self.rf1)
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{1mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ', file=self.rf1)
        except:
            pass
        for j2 in self.odict:                           # restore units
            try:
                statex = self.odict[j2][2].strip()
                exec(statex)
            except:
                pass
        var3s = var0.split('_')                        
        if var3s[0] in greeks:                          # result var to greek
            var3g = "\\" + var0
        else:
            var3g = var0
        typev = type(eval(var0))
        #print('typev', typev)
        print1 = 0                                      # format result printing
        if typev == ndarray:
            print1 = 1
            tmp1 = str(eval(var0))
            if '[[' in tmp1:
                tmp2 = tmp1.replace(' [', '.  [')
                tmp1 = tmp2.replace('[[', '. [[')
            else:
                tmp1 = tmp1.replace('[', '. [')
        elif typev == list or typev == tuple:
            print1 = 1
            tmp1 = str(eval(var0))
            if '[[' in tmp1:
                tmp2 = tmp1.replace(' [', '.  [')
                tmp1 = tmp2.replace('[[', '. [[')
                tmp1 = tmp1.replace('],', '],\n')
            else:
                tmp1 = tmp1.replace('[', '. [')
                tmp1 = tmp1.replace('],', '],\n')
        elif typev == Unum:
            print1 = 2
            exec("Unum.VALUE_FORMAT = '%." + rformat.strip() + "f'")
            if len(eunit) > 0:
                tmp = eval(var0).au(eval(eunit))
            else:
                tmp = eval(var0)
            tmp1 = tmp.strUnit()
            tmp2 = tmp.asNumber()
            chkunit = str(tmp).split()
            #print('chkunit', tmp, chkunit)
            if len(chkunit) < 2:
                tmp1 = ''
            resultform = "{:,."+rformat + "f}"
            result1 = resultform.format(tmp2)
            tmp3 = var0 +"="+ result1 + ' '  + tmp1
        else:
            print1 = 2
            if type(eval(var0)) == float or type(eval(var0)) == float64:
                resultform = "{:,."+rformat + "f}"
                result1 = resultform.format(eval(var0))
                tmp3 = var0 +"="+ result1
            else:
                tmp3 = var0 +"="+ str(eval(var0))
        if print1 == 1:                                 # for lists and arrays
            print('  ', file=self.rf1)
            print('::', file=self.rf1)
            print('  ', file=self.rf1)
            print('. ' + var0 + ' = ', file=self.rf1)
            print(tmp1, file=self.rf1)
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{4mm}', file=self.rf1)
            print('  ', file=self.rf1)       
        if print1 == 2:                                 # add space at units
            try: 
                result2 = latex(tmp3).split()
                tmp3 = ''.join(result2[:-2]) + ' \ '.join(result2[-2:])
            except:
                pass
            #print(' ', file=self.rf1)
            #print('.. math:: ', file=self.rf1)
            #print('  ', file=self.rf1)
            #print("  {" + latex(tmp3, mode='plain') + "}", file=self.rf1)
            print('  ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\hfill{\\underline{'+tmp3 +'}}', file=self.rf1)
            print('  ', file=self.rf1)
        print(".. raw:: latex", file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\vspace{8mm}', file=self.rf1)
        print('  ', file=self.rf1)

        
    def _rst_table(self, dval):
        """Print table to reStructuredText:
        
            _t + line number - 9 - [t] table
            
            [t]   p0 |  p1  |  p2  |  p3  |  p4    |   p5   | p6   | p7  | p8
                        var  state1  desc   range1   range2   dec1   un1   un2
        """
        try:
            eformat, rformat = dval[6].split(',')
            exec("set_printoptions(precision=" + eformat + ")")
            exec("Unum.VALUE_FORMAT = '%." + eformat + "f'")
        except:
            eformat = '3'
            rformat = '3'
            set_printoptions(precision=3)
            Unum.VALUE_FORMAT = "%.3f"
            Unum.VALUE_FORMAT = "%.3f"
        # table heading
        vect = dval[1:]
        eqnum = dval[10].strip()
        tablehdr = 'Table  ' + eqnum
        print(".. raw:: latex", file=self.rf1)
        print('  ', file=self.rf1)
        print('   \\vspace{7mm}', file=self.rf1)
        print('  ', file=self.rf1)
        print("aaxbb " + "**" + tablehdr + "**", file=self.rf1)
        print('  ', file=self.rf1)
        ref5 = dval[5].strip()
        if ref5 != '':
            print(".. raw:: latex", file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\hfill\\text{' + ref5 + '}', file=self.rf1)
            print('   \\begin{flushleft}', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\end{flushleft}', file=self.rf1)
            print('  ', file=self.rf1)
        # draw horizontal line
        #print('  ', file=self.rf1)
        #print(".. raw:: latex", file=self.rf1)
        #print('  ', file=self.rf1)
        #print('   \\vspace{-1mm}', file=self.rf1)
        #print('  ', file=self.rf1)
        #print('   \\hrulefill', file=self.rf1)
        #print('  ', file=self.rf1)
        # symbolic forms
        for _j in self.symb:
            if str(_j)[0] != '_':
                varsym(str(_j))
        # range variables
        try:
            var1 = vect[2].strip()
            var2 = vect[3].strip()
        except:
            pass
        # equation
        try:
            var0 = vect[0].split('=')[0].strip()
            symeq = vect[0].split('=')[1].strip()
        except:
            pass
        # evaluate equation and array variables - keep units
        for k1 in self.odict:
            if k1[0] != '_' or k1[0:2] == '_a':
                    try:
                        exec(self.odict[k1][3].strip())
                    except:
                        pass
                    try:
                        exec(self.odict[k1][4].strip())
                    except:
                        pass
                    try:
                        exec(self.odict[k1][1].strip())
                    except:
                        pass
            #print(k1, eval(k1))
        # write explicit table
        if len(str(vect[2])) == 0 and len(str(vect[3])) == 0:
            ops = [' - ',' + ',' * ',' / ']
            _z1 = vect[0].split('=')[0].strip()
            cmd_str1 = _z1 + ' = array(' + vect[1] +')'
            exec(cmd_str1)

            cunit = dval[7]
            print('cunit', cunit)
            _rc = eval(_z1).tolist()

            # evaluate variables with units
            for inx in ndindex(eval(_z1).shape):
                print(21, type(_rc[inx[0]][inx[1]]),_rc[inx[0]][inx[1]] )
                try:
                    _fltn2a = _rc[inx[0]][inx[1]]
                    _fltn2b = _fltn2a.au(eval(cunit))
                    _fltn2c = _fltn2b.asNumber()
                    _rc[inx[0]][inx[1]] = str(_fltn2c)
                except:
                    pass
            # evaluate numbers
            for inx in ndindex(eval(_z1).shape):
                try:
                    _fltn1 = float(_rc[inx[0]][inx[1]])
                    _rc[inx[0]][inx[1]] = _fltn1
                except:
                    pass
            # evaluate expressions
            for inx in ndindex(eval(_z1).shape):
                for _k in ops:
                    if _k in str(_rc[inx[0]][inx[1]]) :
                        _fltn2 = _rc[inx[0]][inx[1]]
                        _rc[inx[0]][inx[1]] = eval(_fltn2)
                        break
            # print table
            table2 = tabulate
            fltf = "." + eformat.strip() + "f"
            ptable = table2.tabulate(_rc[1:], _rc[0], 'rst', floatfmt=fltf)
            print(ptable, file=self.rf1)
            print('  ', file=self.rf1)
            return
        # evaluate variables - strip units for arrays
        for k1 in self.odict:
            #print('k1', k1)
            if k1[0] != '_':
                    try:
                        exec(self.odict[k1][1].strip())
                    except:
                        pass
                    try:
                        state = self.odict[k1][1].strip()
                        varx = state.split('=')
                        state2 = varx[0].strip()+'='\
                        +varx[0].strip() + '.asNumber()'
                        exec(state2)
                        #print('j1', k1)
                    except:
                        pass
            if k1[0:2] == '_a':
                #print('k1-2', k1)
                try:
                    exec(self.odict[k1][3].strip())
                    exec(self.odict[k1][4].strip())
                    exec(self.odict[k1][1].strip())
                except:
                    pass
        # imported table
        if len(str(vect[1])) == 0:
            _a = eval(vect[0])
            # print table
            table2 = tabulate
            flt1 = "." + eformat.strip() + "f"
            ptable = table2.tabulate(_a[1:], _a[0], 'rst', floatfmt=flt1)
            print(ptable, file=self.rf1)
            print('  ', file=self.rf1)
        # explicit table
        elif len(str(vect[2])) == 0 and len(str(vect[3])) == 0:
            ops = [' - ',' + ',' * ',' / ']
            _a1 = vect[0].split('=')[0].strip()
            cmd_str1 = _a1 + ' = array(' + vect[1] +')'
            exec(cmd_str1)
            _z1 = vect[0].split('=')[0].strip()
            cmd_str1 = _z1 + ' = array(' + vect[1] +')'
            #print(cmd_str1)
            exec(cmd_str1)
            _rc = eval(_z1).tolist()
            # evaluate numbers
            for inx in ndindex(eval(_z1).shape):
                try:
                    _fltn1 = float(_rc[inx[0]][inx[1]])
                    _rc[inx[0]][inx[1]] = _fltn1
                except:
                    pass
                #print('chk1', inx, _a[inx[0]][inx[1]])
            # evaluate expressions
            for inx in ndindex(eval(_z1).shape):
                for _k in ops:
                        if _k in str(_rc[inx[0]][inx[1]]) :
                            _fltn2 = _rc[inx[0]][inx[1]]
                            _rc[inx[0]][inx[1]] = eval(_fltn2)
                            break
            # print table
            table2 = tabulate
            flt1 = "." + eformat.strip() + "f"
            ptable = table2.tabulate(_rc[1:], _rc[0], 'rst', floatfmt=flt1)
            print(ptable, file=self.rf1)
            print('  ', file=self.rf1)
        # single row vector - 1D table
        elif len(str(vect[3])) == 0 and len(str(vect[0])) != 0:
            # process range variable 1 and heading
            symeq1 = sympify(symeq)
            print('  ', file=self.rf1)
            print('.. raw:: latex', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{2mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  Variables:', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{1mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(var1, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{1mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('.. math:: ', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(symeq1, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            rnge1 = vect[2]
            exec(rnge1.strip())
            rnge1a = rnge1.split('=')
            rlist = [vect[6].strip() + ' = ' +
                     str(_r)for _r in eval(rnge1a[1])]
            #process equation
            equa1 = vect[0].strip()
            #print(equa1)
            exec(equa1)
            var2 = equa1.split('=')[0]
            etype = equa1.split('=')[1]
            elist1 = eval(var2)
            if etype.strip()[:1] == '[':
                # data is in list form
                #elist2 = []
                elist2 = eval(equa1.split('=')[1])
                # for _v in alist1:
                #         try:
                #             elist2.append(list(_v))
                #         except:
                #             elist2.append(_v)
            else:
                try:
                    elist2 = elist1.tolist()
                except:
                    elist2 = elist1

                elist2 = [elist2]
            # create 1D table
            ptable = tabulate.tabulate(elist2, rlist, 'rst',
                                floatfmt="."+eformat.strip()+"f")
            print(ptable, file=self.rf1)
            print('  ', file=self.rf1)
            #print(ptable)
        # 2D table
        elif len(str(vect[3])) != 0 and len(str(vect[0])) != 0:
            symeq1 = sympify(symeq)
            print('  ', file=self.rf1)
            print('.. raw:: latex', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{2mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  Variables:', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{1mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(var1, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{2mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(var2, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            print('.. math:: ', file=self.rf1)
            print('  ', file=self.rf1)
            print('   \\vspace{4mm}', file=self.rf1)
            print('  ', file=self.rf1)
            print('  ' + latex(symeq1, mul_symbol="dot"), file=self.rf1)
            print('  ', file=self.rf1)
            # process range variable 1
            rnge1 = vect[2]
            exec(rnge1.strip())
            rnge1a = rnge1.split('=')
            rlist = [vect[6].strip() + ' = ' +
                     str(_r) for _r in eval(rnge1a[1])]
            # process range variable 2
            rnge2 = vect[3]
            exec(rnge2.strip())
            rnge2a = rnge2.split('=')
            clist = [str(_r).strip() for _r in eval(rnge2a[1])]
            rlist.insert(0, vect[7].strip())
            # process equation
            equa1 = vect[0].strip()
            #print('equa1', equa1)
            exec(equa1)
            etype = equa1.split('=')[1]
            if etype.strip()[:1] == '[':
                # data is in list form
                #alist = []
                alist = eval(equa1.split('=')[1])
                #print('alist1', alist1)
                # for _v in alist1:
                #     for _x in _v:
                        #print('_x', _x)
                #         alist.append(list(_x))
                        #print('append', alist)
            else:
                # data is in equation form
                equa1a = vect[0].strip().split('=')
                equa2 = equa1a[1]
                rngx = rnge1a[1]
                rngy = rnge2a[1]
                ascii1 = rnge1a[0].strip()
                ascii2 = rnge2a[0].strip()

                # format table
                alist = []
                for _y12 in eval(rngy):
                    alistr = []
                    for _x12 in eval(rngx):
                        eq2a = equa2.replace(ascii1, str(_x12))
                        eq2b = eq2a.replace(ascii2, str(_y12))
                        el = eval(eq2b)
                        alistr.append(el)
                    alist.append(alistr)
                    #print('append', alist)

            for _n, _p in enumerate(alist):  _p.insert(0, clist[_n])
            # create 2D table
            flt1 = "." + eformat.strip() + "f"
            #print(alist)
            ptable = tabulate.tabulate(alist, rlist, 'rst', floatfmt=flt1)
            print(ptable, file=self.rf1)
            print('  ', file=self.rf1)


    def _rst_sect(self, dval):
        """Print section title to reST.
        
        ::
    
           _s :    p0         |       p1      |   p2        
                  left string    calc number     sect num   
       
        """        
        tleft = dval[0].strip()
        tright = dval[1].strip() + dval[2].strip()
        self.lastsect = int(dval[2].strip()[1:-1])
        self.lastcalcnumber = dval[1].strip()
        print(' ', file=self.rf1)
        print(".. raw:: latex", file=self.rf1)
        print(' ', file=self.rf1)
        print('   \\vspace{3mm}', file=self.rf1)
        print(' ', file=self.rf1)
        print(' ', file=self.rf1)
        print(tleft.strip() + "aaxbb " + tright.strip(),file=self.rf1)
        print("-" * self.widthp, file=self.rf1)
        print(' ', file=self.rf1)
        print(' ', file=self.rf1)
        print(".. raw:: latex", file=self.rf1)
        print(' ', file=self.rf1)
        print('   \\vspace{1mm}', file=self.rf1)
        print(' ', file=self.rf1)

    
    def _rst_terms(self):
        """Print section with term definitions to reST:
      
            key: values    
            _v :   p0  |   p1  |  p2      |    p3            
                 var     expr     statemnt   descrip     

            key : _e  
            value:  p0  |  p1     |  p2   |   p3    |  p4  | p5   |  p6  |  p7       
                    var   expr      state    descrip   dec1  dec2   unit   eqnu 
        
        """
        taglist =[]
        for _i in self.odict:
            mtag = _i[0:2]
            taglist.append(mtag)
        if ('_v' or '_e') in taglist:        
            tleft = "AST Variables and Definitions"
            tright = self.lastcalcnumber + '['+str(self.lastsect+1)+']'
            print(' ', file=self.rf1)
            print(".. raw:: latex", file=self.rf1)
            print(' ', file=self.rf1)
            print('   \\vspace{3mm}', file=self.rf1)
            print(' ', file=self.rf1)
            print(' ', file=self.rf1)
            print(tleft.strip() + "aaxbb " + tright.strip(),file=self.rf1)
            print("-" * self.widthp, file=self.rf1)
            print(' ', file=self.rf1)
            print(' ', file=self.rf1)
            print(".. math::", file=self.rf1) 
            print(' ', file=self.rf1)            
            print('  \\begin{align}', file=self.rf1)
            cnt = 0
            for _i in self.odict:            # execute dictionary line by line
                if _i[0:2] in ['_v','_e']:
                    cnt += 1
                    if cnt == 35:
                        print('  \\end{align}', file=self.rf1)
                        print(' ', file=self.rf1)
                        print(' ', file=self.rf1)
                        print(".. math::", file=self.rf1) 
                        print(' ', file=self.rf1)            
                        print('  \\begin{align}', file=self.rf1)
                        cnt = 0
                    mvals = self.odict[_i]
                    varstring1 = "  \\bm{" + str(mvals[0]) + "} "
                    varstring2 = "&= \\textrm{" + str(mvals[3]) + "}\\\\"
                    print(varstring1 + varstring2, file=self.rf1)
                    #print('rstmtag', mtag, _i, mvals, mvals[0])
            print('  \\end{align}', file=self.rf1)
            print(' ', file=self.rf1)
        else:
            pass


 """
    def _paramlines(dline1):
     set calc level parameter flags

        #| width:nn | pdf | noclean | margins:T:B:L:R | verbose |
    cfg.pdfflag = 0
    cfg.cleanflag = 1
    cfg.projectflag = 0
    cfg.echoflag = 0
    cfg.calcwidth = 80
    cfg.pdfmargins = "1.0in,0.75in,0.9in,1.0in"
    if mline1[0:2] == "#|":
        mline2 = mline1[2:].strip("\n").split(",")
        mline2 = [x.strip(" ") for x in mline2]
        # print('mline2', mline2)
        if "pdf" in mline2:
            cfg.pdfflag = 1
        if "noclean" in mline2:
            cfg.cleanflag = 0
        if "verbose" in mline2:
            cfg.verboseflag = 1
        if "stoc" in mline2:
            cfg.stocflag = 1
        if "width" in mline2:
            pass
        for param in mline2:
            if param.strip()[0:5] == "title":
                cfg.calctitle = param.strip()[6:]
        for param in mline2:
            if param.strip()[0:7] == "margins":
                cfg.pdfmargins = param.strip()[6:]
    else:
        pass


    vbos = cfg.verboseflag  # set verbose echo flag
    _dt = datetime.datetime
    with open(os.path.join(cfg.cpath, cfg.cfileutf), "w") as f2:
        f2.write(str(_dt.now()) + "      once version: " + __version__)
    _mdict = ModDict()  # 1 read model
    _mdict._build_mdict()  # 2 build dictionary
    mdict = {}
    mdict = _mdict.get_mdict()
    newmod = CalcUTF(mdict)  # 4 generate UTF calc
    newmod._gen_utf()
    newmod._write_py()  # 4 write Python script
    _el.logwrite("< python script written >", vbos)
    _el.logwrite("< pdfflag setting = " + str(cfg.pdfflag) + " >", vbos)
    if int(
        cfg.pdfflag
    ):  # 5 check for PDF parameter                                       # generate reST file
        rstout1 = CalcRST(mdict)
        rstout1.gen_rst()
        pdfout1 = CalcPDF()  # 5 generate TeX file
        pdfout1.gen_tex()
        pdfout1.reprt_list()  # 5 update reportmerge file
        _el.logwrite("< reportmerge.txt file updated >", 1)
        os.chdir(once.__path__[0])  # 5 check LaTeX install
        f4 = open("once.sty")
        f4.close()
        os.chdir(cfg.ppath)
        _el.logwrite("< style file found >", vbos)
        os.system("latex --version")
        _el.logwrite("< Tex Live installation found>", vbos)
        pdfout1.gen_pdf()  # 5 generate PDF calc
    os.chdir(cfg.ppath)
    return mdict  # 6 ret

    # on return clean up and echo result summaries
    vbos = cfg.verboseflag
    if cfg.cleanflag:  # check noclean flag
        _el.logwrite("<cleanflag setting = " + str(cfg.cleanflag) + ">", vbos)
        os.chdir(_tpath)
        for _i4 in _cleanlist:
            try:
                os.remove(_i4)
            except OSError:
                pass
        os.chdir(_ppath)
    if cfg.echoflag:  # check echo calc flag
        _el.logwrite("<echoflag setting = " + str(cfg.echoflag) + ">", vbos)
        try:
            with open(_cfile, "r") as file2:
                for il2 in file2.readlines():
                    print(il2.strip("\n"))
        except:
            _el.logwrite("< utf calc file could not be opened >", vbos)
    if cfg.openflagpdf:  # check open PDF flag
        try:
            pdffilex = os.path.join(_ppath, _cpath, _cfilepdf)
            os.system(pdffilex)
        except:
            _el.logwrite("< pdf calc file could not be opened >", vbos)

    if cfg.openflagutf:  # check open UTF flag
        try:
            utffilex = os.path.join(_ppath, _cpath, _cfileutf)
            os.system(utffilex)
        except:
            _el.logwrite("< txt calc file could not be opened >", vbos)

    calstart._variablesummary()  # echo calc results
    _el.logwrite("< end of once program >", 1)
    _el.logclose()  # close log
    # end of program
    """