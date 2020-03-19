#! python
"""convert rivet strings to utf-8 calcs

This module converts each rivet string to a utf-8 calc string, using
a class for each of the 5 string types. String markup inlcudes commands and 
tags.  See parse_tag function for tag summary.

List of commands by string type {notes in braces}:
type    : commands
----      --------
repro   : summary {block}, labels {block}, append {block}, link
insert  : text, tex, sym, img {block}, table {block}, cite, foot, link,   
values  : link
equation: format, link
table   : create, write, read, plot, add, save, {plus insert commands}

detail
------
r__('''r-string''') {repository and calc data}
    || summary | {toc} sections / functions  | {include} docstrings  
        {paragraph text}
    || labels 
        {csv list}
    || append           
        x.pdf {pdf file name}, {appendix title text}
    || link | http:\\www.x {link text}
i__('''i-string''') {insert text and images}
    || text | x.txt {text file} | {indent n} i:n, (max width) w:65 
    || tex  | {latex equation text}
    || sym  | {sympy equation text}
    || img  | x.png/x.jpg {image file} | {scale} s:1, {fig number} #:t(rue)/f(alse) 
        figure title text
    || table | inline | {table number} #:t{rue}/f{alse} 
        table title text
    || table | x.rst {file name} | {table number} #:t/f 
        table title text
    || table | n.csv {file name} | {row}r:[], {col}c:[], {max width}m:30, #:t/f  
        table title text
    || link | {http link text}
    || cite | {citation text} | citation description text   
    || foot | footnote description text
v__('''v-string''') {define values}
e__('''e-string''') {define equations}
    || format | {decimals}e:n, {result}r:n, {check}c:0, {print}p:0/1/2, #:t/f  
t__('''t-string''') (define tables and plots)
    || create| table name
    || write | .csv file name | table name 
    || read  | .csv file name | table name
    || plot | f.csv {file name} |(col names)x:c1,y:c2,(rows)r:[],(kind)k:line,(grid)g:t/f
    || add (data to plot) | (col names) x:c3, y:c4, (color)c:blue        
    || save | n.png / n.jpg {file names} | f {name from plot command} 
    {plus all insert commands}

List of tags {notes in braces}:
------------------------------
    [abc]_      {citation name}   
    [#]_        {# generates footnote number) 
    [page]_     {new doc page)
    [line]_     {draw horizontal line)
    [r]_        {right justify line of text)
    [c]_        {center line of text)
"""
import os
import sys
import csv
import textwrap
import subprocess
import tempfile
import re
import io
from io import StringIO
from numpy import *
import numpy.linalg as la
import pandas as pd
import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.abc import _clash2
import matplotlib.pyplot as plt 
import matplotlib.image as mpimg
from IPython.display import Image as ipyImage, display
from tabulate import tabulate 
from pathlib import Path

def _tags(tagS: str, calcS: str, hdrD: dict) -> str:
    """parse tags
    
    Args:
        tagS (str): line from rivet string
    
    List of tags (notes in paranthesis):
    [abc]_      (citation name)   
    [#]_        (footnote number generator) 
    [page]_     (new doc page)
    [line]_     (draw horizontal line)
    [r]_        (right justify line of text)
    [c]_        (center line of text)

    """
    if "[page]_" in tagS:
        pass
    elif "[line]_" in tagS:
        pass
    elif "[r]_" in tagS:
        tagL = tagS.split("[r]")
        utfS = str.rjust(tagL[0].strip(), 80)
        print(utfS + "\n"); calcS += utfS        
        return calcS
    elif "[link]_" in tagS:
        rL = tagS.split("]_")
        utfS = "link: "+ rL[1].strip()
        print(utfS + "\n"); calcS += utfS
        return calcS
    elif "[foot]_" in tagS:
        rL = tagS.split("]_")
        utfS = "[" + str(hdrD["footque"].popleft()) + "] " + rL[1].strip()
        print(utfS + "\n"); calcS += utfS
        return calcS
    elif "[cite]_" in tagS:
        pass
    else:
        tag = re.search(r"\[.*?\]_", tagS)
        tagx = tag.group(0)
        modline = tagS.replace(" " + tagx,"")

class RepoU:
    """convert repo-string to utf-calc string

    Attributes:
        rstrL (list): rivet-strings
        folderD (dict): folder structure
        hdrD (dict): header information
    """
    def __init__(self, strL :list,  hdrD :dict, folderD :dict) -> str:
        self.calcS = """"""
        self.strL = strL
        self.folderD = folderD
        self.hdrD = hdrD

    def r_parse(self) -> str:
        """ parse repo string
       
       Returns:
            string :  formatted utf-calc string
        """
        endflgB = False; rtmpS = ""; rL = []; indxI = -1
        rcmdL = ["summary", "label", "append" ]
        methodL =  [self.r_summary, self.r_label, self.r_append]
        
        for rS in self.strL:
            if rS[0:2] == "##":  continue           # remove review comment
            rS = rS[4:]                             # remove indent
            if len(rS.strip()) == 0:                # blank line, end block
                if endflgB:
                    rL.append(rtmpS.strip())
                    methodL[indxI](rL)              # call attribute from list                          
                    endflgB = False; rtmpS = ""; rL = []; indx = -1      
                print("\n"); self.calcS += "\n" 
                continue
            if endflgB:                             # add lines until blank
                rtmpS = rtmpS + rS + "\n"; continue
            if rS[0:2] == "||":                     # find command
                rL = rS[2:].split("|")
                indxI = rcmdL.index(rL[0].strip())            
                endflgB = True; continue
            # commands
            if rS[0] == "#" : continue              # remove comment 
            if rS[0:2] == "::" : continue           # remove preformat 
            if "]_" in rS:                          # find tag
                if "[#]_" in rS:
                    incrI = self.hdrD["footque"][-1] + 1
                    self.hdrD["footque"].append(incrI)
                    rS = rS.replace("[#]_", "[" + 
                        str(self.hdrD["footque"].popleft()) + "]" )
                    print(rS); self.calcS += rS + "\n"
                else:
                    self.calcS = _tags(rS, self.calcS, self.hdrD)
            else:
                print(rS); self.calcS += rS + "\n"    

        return self.calcS        

    def r_summary(self, rL):
        utfS = "Summary\n"
        utfS += "-------\n"
        utfS += rL[2]
        print(utfS + "\n"); self.calcS += utfS
        
    def r_append(self, rL):
        utfS = "Appendices\n"
        utfS += "----------\n" 
        utfS += rL[2].strip()
        print(utfS + "\n"); self.calcS += utfS

    def r_label(self, rL):
        #print(3,rL)
        csvL = rL[2].split("\n")
        tabL = [x.split(",") for x in csvL]
        maxlenI = max(len(x) for x in tabL)
        for idx,val in enumerate(tabL):
            if len(val) < maxlenI:
                addL = maxlenI - len(val)
                tabL[idx].extend("-"*addL)
        headers = ["category"]
        for i in range(maxlenI-1) : headers.append("label") 
        old_stdout = sys.stdout
        output = StringIO()
        output.write(tabulate(tabL, headers, tablefmt="grid"))            
        utfS = output.getvalue()
        print(utfS + "\n"); self.calcS += utfS
        sys.stdout = old_stdout    
    
class InsertU:
    """convert rivet-string to utf-calc string 

    Attributes:
        strL (list): rivet-string
        folderD (dict): folder structure
        hdrD (dict):  header information
        setD (dict): command settings
    """

    def __init__(self, strL: list,  hdrD: dict, folderD: dict, setD: dict):
        self.calcS = """"""
        self.strL = strL
        self.folderD = folderD
        self.hdrD = hdrD
        self.setD =setD

    def i_parse(self) -> tuple:
        """ parse insert-string
       
       Returns:
            tuple :  a string and 3 dictionaries
        """
        endflgB = False; itmpS = ""; iL = []; indxI = -1
        icmdL = ["text", "sympy", "latex", "table", "image", "image2"]
        attribL =  [self.i_text, self.i_sympy, self.i_latex, 
                    self.i_table, self.i_image, self.i_image2]
        for iS in self.strL:
            if iS[0:2] == "##":  continue          # remove review comment
            iS = iS[4:]                            # remove 4 space indent
            if len(iS.strip()) == 0:               # if empty line                   
                print("\n"); self.calcS += "\n"; continue      
            if endflgB:                            # add next line
                itmpS = itmpS + iS + "\n"; 
                iL.append(itmpS.strip())
                attribL[indxI](iL)                  # call attribute from list                           
                endflgB = False; itmpS = ""; iL = []; indxI = -1
                continue
            if iS[0:2] == "||":                     # process a command
                iL = iS[2:].split("|")
                callS = ((iL[0].split(":"))[0]).strip()
                indxI = icmdL.index(callS)            
                endflgB = True; continue
            if iS[0] == "#" : continue              # remove comment 
            if iS[0:2] == "::" : continue           # remove preformat 
            if "]_" in iS:                          # process a tag
                if "[#]_" in iS:
                    iS = iS.replace("[#]_", "[" + 
                        str(self.hdrD["footque"][-1]) + "]" )
                    print(iS); self.calcS += iS + "\n"
                    incrI = self.hdrD["footque"][-1] + 1
                    self.hdrD["footque"].append(incrI)
                else:
                    self.calcS = _tags(iS, self.calcS, self.hdrD); continue    
            else:        
                print(iS); self.calcS += iS + "\n"

        return self.calcS, self.hdrD, self.setD

    def i_text(self, iL: list):
        """insert text from file
        
        Args:
            iL (list): text command list
        """
        try: 
            widthI = int(iL[0].split(":")[1])
        except:
            widthI = self.setD["txtwidth"]
        self.setD.update({"txtwidth":widthI})
        txtpath = Path(self.folderD["xpath"] /  iL[1].strip())
        with open(txtpath, 'r') as txtf1:
                utfL = txtf1.readlines()
        txtS = "".join(utfL)
        indI = int((80-widthI)/2)
        indS = " "*indI
        utfL = textwrap.wrap(txtS, width=widthI)
        utfL = [s+"\n" for s in utfL]
        utfS = indS + indS.join(utfL)
        print(utfS); self.calcS += utfS + "\n"
        
    def i_latex(self,iL: list):
        """insert formated equation from LaTeX string
        
        Args:
            ipL (list): parameter list

        """
        try:
            scaleI = int(iL[0].split(":")[1])
        except:
            scaleI = self.setD["scale1"]
        self.setD.update({"scale1":scaleI})
        txS = iL[1].strip()
        #txs = txs.encode('unicode-escape').decode()
        ltxS = parse_latex(txS)
        utfS = sp.pretty(sp.sympify(ltxS, _clash2, evaluate=False))
        print(utfS+"\n"); self.calcS += utfS + "\n"   

    def i_sympy(self,iL):
        """insert formated equation from SymPy string 
        
        Args:
            ipL (list): parameter list
        """
        try:
            scaleI = int(iL[0].split(":")[1])
        except:
            scaleI = self.setD["scale1"]
        self.imgD.update({"scale1":scaleI})
        spS = iL[1].strip()
        spL = spS.split("=")
        spS = "Eq(" + spL[0] +",(" + spL[1] +"))" 
        #sps = sps.encode('unicode-escape').decode()
        utfS = sp.pretty(sp.sympify(spS, _clash2, evaluate=False))
        print(utfS); self.calcS += utfS + "\n"   
            
    def i_image(self, iL: list):
        """insert image from file
        
        Args:
            ipl (list): parameter list
        """
        try:
            scaleI = int(iL[0].split(":")[1])
        except:
            scaleI = self.imgD["scale1"]
        self.setD.update({"scale1":scaleI})
        self.hdrD["fignum"] += 1
        figI = self.hdrD["fignum"]
        sectI = self.hdrD["sectnum"]
        fileS = iL[1].strip()
        captionS = iL[2].strip()
        imgpathS = str(Path(self.folderD["fpath"], fileS))
        utfS = ("Figure " + str(sectI) + '.' + str(figI) + "  "  
               + captionS + "\npath: " + imgpathS)
        print(utfS); self.calcS += utfS + "\n"
        try:
            display(ipyImage(filename = imgpathS))
        except:
            pass

    def i_image2(self, iL: list):
        """insert image from file
        
        Args:
            ipl (list): parameter list
        """
        try:
            scaleI = int(iL[0].split(":")[1])
        except:
            scaleI = self.setD["scale1"]
        self.imgD.update({"scale1":scaleI})
        self.hdrD["fignum"] += 1
        figI = self.hdrD["fignum"]
        sectI = self.hdrD["sectnum"]
        fileS = iL[1].strip()
        captionS = iL[2].strip()
        imgP = str(Path(self.folderD["fpath"], fileS))
        utfS = ("Figure " + str(sectI) + '.' + str(figI) + "  "  
               + captionS + "\npath: " + imgP)
        print(utfS); self.calcS += utfS + "\n"

    def i_table(self, iL: list):
        """insert table from inline or csv, rst file 
        
        Args:
            ipl (list): parameter list
        """       
        try:
            widthI = int(iL[0].split(":")[1])
        except:
            widthI = int(self.imgD["width"])
        self.setD.update({"width":widthI})
        tableS = ""; utfS = ""
        fileS = iL[1].strip()
        tfileS = Path(self.folderD["tpath"], fileS)   
        tableI = self.hdrD["tablenum"] + 1
        self.hdrD.update({"tablenum":tableI})
        sectI = self.hdrD["sectnum"]
        if ".csv" in iL[1]:                        # csv file       
            format1 = []
            with open(tfileS,'r') as csvfile:
                readL = list(csv.reader(csvfile))
            for row in readL:
                wrow=[]
                for i in row:
                    templist = textwrap.wrap(i, widthI) 
                    wrow.append("""\n""".join(templist))
                format1.append(wrow)
            old_stdout = sys.stdout
            output = StringIO()
            output.write(tabulate(format1, tablefmt="grid", headers="firstrow"))            
            utfS = output.getvalue()
            titleS = "  \n"
            sys.stdout = old_stdout
            try: titleS = iL[2].strip() + titleS
            except: pass        
        elif ".rst" in iL[1]:                        # rst file
            with open(tfileS,'r') as rst: 
                utfS = rst.read()
            titleS = "  \n"
            try: titleS = iL[2].strip() + titleS
            except: pass
        else:                                       # inline reST table 
            utfs = ""
            titleS = "  "
            try: titleS = iL[2].strip() + titleS
            except: pass
        utfS = ("\nTable " + str(sectI)+'.' + str(tableI) + 
                        "  " + titleS ) + utfS                                              
        print(utfS); self.calcS += utfS + "\n"  

class ValueU:
    """convert value rivet-string to utf-calc string
        
    Attributes:
        strl (list): rivet strings
        hdrd (dict): header information
        folderd (dict): folder structure
        rivetd (dict) : rivet calculation variables
        equl (list) : equations for export

    """
 
    def __init__(self, strL: list, equL: list, hdrD: dict, exportL: list, 
                                folderD: dict, rivetD: dict, ):
        """convert rivet string of type value to utf-calc string
        
        """
        self.calcS = """"""
        self.strL = strL
        self.folderD = folderD
        self.hdrD = hdrD
        self.exportL = exportL
        self.rivetD = rivetD
          
    def v_parse(self)-> tuple:
        """parse strings of type value

        Return:
            calcS (list): utf formatted calc strings
            rivetD (list): local() dictionary
        """
        locals().update(self.rivetd)

        endflg = False
        itmpl = []
        for vls in self.strl:
            if vls[0:2] == "##":  continue          # remove review comment
            vls = vls[4:]                           # remove 4 space indent
            if len(vls.strip()) == 0:
                self.calcl.append(" ")              # insert blank line
                print(21, vls)
                continue
            if vls[0] == "#" : continue             # remove comment 
            if vls[0:2] == "::" : continue          # remove preformat 
            if "|" in vls:                          # act on parse tag
                vpl = vls.split("|")
                if "=>" in vpl[0]: 
                    self.v_lookup(vpl)              # assign vector 
                elif ":" in vpl[0]:
                    self.v_reprint(vpl)             # reprint a value
                else: self.v_assign(vpl)            # assign a value
            else: 
                self.calcl.append(vls)
                print(vls)

        self.rivetd.append(locals())

        return (self.calcl, self.rivetd, self.equl)
        
    def v_assign(self, vpl: list):
        """assign value to variable
        
        Args:
            vpl (list): list of value string components
        """
        
        locals().update(self.rivetd)

        pys = str(vpl[0]) + "# " + vpl[1].strip()
        vl = vpl[0].split("=")[1].strip()
        exec(vpl[0].strip())
        chkl = ""
        if "[" in vl:
            chkl = vl.split("[")[0].strip()
            evalx = eval(chkl) 
            if isinstance(evalx, list):
                exts = str(vpl[0]).strip() + " = " + str(eval(vl))
                utfs = str.ljust(exts,40) + " | " + vpl[1].strip()
        else:
            utfs =  str.ljust(str(vpl[0]).strip(),40) + " | " + vpl[1].strip()
        
        self.equl.append(pys)
        self.calcl.append(utfs)
        self.rivetd.update(locals())
        
        print(utfs)


    def v_lookup(self, vpl: list):
        """assign vector from csv file to variable
        
        Args:
            vpl (list): list of value string items
        """
        
        locals().update(self.rivetd)
        
        files1 = vpl[0].split("=>")[0]
        files2 = files1.split("[")[0].strip()
        rows = files1.split(".csv")[1].strip()
        filep = os.path.join(self.folderd["tpath"], files2)

        with open(filep,'r') as csvf:
            readl = list(csv.reader(csvf))
        rowl = eval("readl" + rows)

        vars = vpl[0].split("=>")[1].strip()
        cmds = vars + "=" + str(rowl)
        exec(cmds)
        utfs = str.ljust(vpl[0].strip(),40) + " | " + vpl[1].strip()

        self.calcl.append(utfs)
        self.rivetd.update(locals())

        print(utfs)
    
    def v_reprint(self, vpl: list):
        """reprint a variable value
        
        Args:
            vpl (list): list of value string items
        """

        vars = vpl[0].split(":")[0].strip()
        ans = str(eval(vars))
        utfs = str.ljust(vars + " = " + ans, 40) + " | " + vpl[1].strip()

        print(utfs)

class EquationU:
    """Convert rivet string type **equation** to utf-calc string

    """

    def __init__(self, strl: list,  hdrd: dict, folderd: dict, 
                                        rivetd: dict, equl: list):     
        """convert rivet string type **equation** to utf-calc string
        
        Args:
            strl (list): rivet strings
            hdrd (dict): header information
            folderd (dict): folder structure
            rivetd (dict) : rivet calculation variables
            equl (list) : equations for export
        """
        self.calcl = []
        self.strl = strl
        self.folderd = folderd
        self.hdrd = hdrd
        self.equl = equl
        self.rivetd = rivetd
        self.paramd = { "e":2,"r":2,"c":0, "p":2, "n":"t"}

    def e_parse(self) -> tuple:
        """parse strings of type equation
        
        Return:
            ecalc (list): list of calculated equation lines
            local_dict (list): local() dictionary
        """
        locals().update(self.rivetd)                
        endflg = False
        etmpl = []                                  # block string

        for els in self.strl:
            if els[0:2] == "##":  continue          # remove review comment
            els = els[4:]                           # remove 4 space indent
            if len(els.strip()) == 0:
                self.calcl.append(" ")              # blank line
                print(" "); continue
            if els[0] == "#" : continue             # remove comment 
            if els[0:2] == "::" : continue          # remove preformat 
            if "=" in els:                          # find parse tag
                epl = els.split("|")
                print(32, epl)            
                if endflg:                          # append line to block
                    etmpl.append(epl[0]); epl = etmpl
                    print(36, etmpl)
                    endflg = False; etmpl = []
                if els.strip()[-1] == "|":          # set block flag
                    endflg = True
                    etmpl = epl
                    print(35, etmpl); continue
                print(37, epl[0,1])
                e_updateparams(epl[1].strip())
                exec(epl[0].strip())                # exec equation
                if self.paramd["p"] == 1:
                    eq_symbol(epl,1)
                if self.paramd["p"] == 2:
                    eq_symbol(epl,2)
            else:
                print(39, els)
                self.calcl.append(els)

        self.rivetd.update(locals())
        return self.calcl

    def e_updateparams(self, eps: str):
        """update process parameters from tag
        
        Args:
            eps (string): equation print parameters
        """
        try:
            paraml = eps.split(",")
            for i in paraml:
                key = i.split(":")[0].strip() 
                self.paramd[key] = i.split(":")[1]
        except:
            pass
        eformat = self.paramd["e"]
        rformat = self.paramd["r"]
        exec("set_printoptions(precision=" + eformat.strip() + ")")
        exec("Unum.VALUE_FORMAT = '%." + eformat.strip() + "f'")

    def eq_symbol(self, epl: list, flag: int):
        """[summary]
        
        Args:
            epl (list): [description]
        """
        locals().update(self.rivetd)
        utfs = epl[0].strip(); descrips = epl[3]; pard = dict(epl[1])
        vars = utfs.split("=")
        results = vars[0].strip() + " = " + str(eval(vars[1]))
        eqnums = (" [ " + self.paramd["sectnum"] + "." + 
                                self.paramd["eqnum"] + " ] ")
        print(" "); self.calcl.append(" ") 
        ehdr = (descrips + " [ " + results + " ] " + 
            " [ " + eqnums + " ] ").rjust(self.paramd["swidth"])
        print((ehdr)); self.calcl.append("ehdr") 
        print(" "); self.calcl.append(" ")       
        try: 
            eps = "Eq(" + epl[0] +",(" + epl[1] +"))" 
            #sps = sps.encode('unicode-escape').decode()
            utfs = sp.pretty(sp.sympify(eps, _clash2, evaluate=False))
            print(utfs); self.calcl.append(utfs)
        except:
            print(utfs); self.calcl.append(utfs)

        try: self.equl.append(" # " + epl[3].strip())       # export eq to py
        except: pass
        self.equl.append(epl[0].strip())
        self.rivetd.update(locals())
        if flag == 2: eq_sub(epl, eps)      # substitute variable with number
        if pard["c"] != 0: eq_chk(results, pard["c"])   # check result

    def eq_sub(self, epl: list, eps: str):

        locals().update(self.rivetd)
        utfs = epl[0].strip(); descrips = epl[3]; pard = dict(epl[1])
        vars = utfs.split("=")
        results = vars[0].strip() + " = " + str(eval(vars[1]))
        try: 
            eps = "Eq(" + epl[0] +",(" + epl[1] +"))" 
            #sps = sps.encode('unicode-escape').decode()
            utfs = sp.pretty(sp.sympify(eps, _clash2, evaluate=False))
            print(utfs); self.calcl.append(utfs)
        except:
            print(utfs); self.calcl.append(utfs)
        try:
            symeq = sp.sympify(eps.strip())                                                 # substitute                            
            symat = symeq.atoms(sp.Symbol)
            for _n2 in symat:
                evlen = len((eval(_n2.__str__())).__str__())  # get var length
                new_var = str(_n2).rjust(evlen, '~')
                new_var = new_var.replace('_','|')
                symeq1 = symeq.subs(_n2, sp.Symbols(new_var))
            out2 = sp.pretty(symeq1, wrap_line=False)
            #print('out2a\n', out2)
            symat1 = symeq1.atoms(sp.Symbol)       # adjust character length
            for _n1 in symat1:                   
                orig_var = str(_n1).replace('~', '')
                orig_var = orig_var.replace('|', '_')
                try:
                    expr = eval((self.odict[orig_var][1]).split("=")[1])
                    if type(expr) == float:
                        form = '{:.' + eformat +'f}'
                        symeval1 = form.format(eval(str(expr)))
                    else:
                        symeval1 = eval(orig_var.__str__()).__str__()
                except:
                    symeval1 = eval(orig_var.__str__()).__str__()
                out2 = out2.replace(_n1.__str__(), symeval1)
            #print('out2b\n', out2)
            out3 = out2                         # clean up unicode 
            out3.replace('*', '\\u22C5') 
            #print('out3a\n', out3)
            _cnt = 0
            for _m in out3:
                if _m == '-':
                    _cnt += 1
                    continue
                else:
                    if _cnt > 1:
                        out3 = out3.replace('-'*_cnt, u'\u2014'*_cnt)
                    _cnt = 0
            #print('out3b \n', out3)
            self._write_utf(out3, 1, 0)         # print substituted form
            self._write_utf(" ", 0, 0)
        except:
            pass   

        typev = type(eval(var0))                # print result right justified
        if typev == ndarray:
            tmp1 = eval(var0)
            self._write_utf((var0 + " = "), 1, 0)
            self._write_utf(' ', 0, 0)
            self._write_utf(tmp1, 0, 0)
        elif typev == list or typev == tuple:
            tmp1 = eval(var0)
            self._write_utf((var0 + " = "), 1)
            self._write_utf(' ', 0)
            plist1 = ppr.pformat(tmp1, width=40)
            self._write_utf(plist1, 0, 0)
        elif typev == Unum:
            exec("Unum.VALUE_FORMAT = '%." + rformat.strip() + "f'")
            if len(cunit) > 0:
                tmp = eval(var0).au(eval(cunit))
            else:
                tmp = eval(var0)
            tmp1 = tmp.strUnit()
            tmp2 = tmp.asNumber()
            chkunit = str(tmp).split()
            #print('chkunit', tmp, chkunit)
            if len(chkunit) < 2: tmp1 = ''
            resultform = "{:,."+ rformat + "f}"
            result1 = resultform.format(tmp2)
            tmp3 = result1 + ' '  + tmp1
            self._write_utf((var0 + " = " + tmp3).rjust(self.widthc-1), 1, 0)
        else:
            if type(eval(var0)) == float or type(eval(var0)) == float64:
                resultform = "{:,."+rformat + "f}"
                result1 = resultform.format(eval(var0))
                self._write_utf((var0 +"="+
                                 str(result1)).rjust(self.widthc-1), 1, 0)
            else:
                    self._write_utf((var0 +"="+
                                     str(eval(var0))).rjust(self.widthc-1), 1, 0)
        tmp = int(self.widthc-2) * '-'           # print horizontal line
        self._write_utf((u'\u2514' + tmp + u'\u2518').rjust(self.widthc), 1, 0)
        self._write_utf(" ", 0, 0)

        self.equl.append(pys)
        self.calcl.append(utfs)
        self.rivetd.update(locals())

    def eq_chk(results, compare):
        pass

class TableU:
    """Process table_strings to utf-calc

    Returns utf string of table results
    """
 
    def __init__(self, tlist: list, rivet_dict: dict, \
                     folders: dict, strnum: list):    
        """

        Args:
            tlist (list): list of input lines in table string
        """
        self.rivet = rivet_dict
        self.tcalc = []
        self.tlist = tlist
        self.folderd = folders
        self.maxwidth = strnum[0]
        self.sectnum = strnum[1]
        self.eqnum = strnum[2]
        self.fignum = strnum[3]
        self.pltfile = ""
        self.pltname = ""

        try:
            plt.close()
        except:
            pass

    def t_str(self) -> tuple:
        """compose utf calc string for values

        Return:
            vcalc (list): list of calculated strings
            local_dict (list): local() dictionary
        """
        locals().update(self.rivet)

        if ".xlsx" in ipl[2]:                   # excel file
            df = pd.read_excel(filep, usecols = lambda x: x in list(col), 
                            skiprows = lambda x: x not in list(rowl))
            old_stdout = sys.stdout
            output = StringIO()
            output.write(tabulate(df, tablefmt="grid", headers="firstrow"))            
            table1 = output.getvalue()
            sys.stdout = old_stdout
            #self.icalc.append("\n" + str(data1) + "\n")
        else:
            pass
        
        for tline in self.tlist:
            globals().update(locals())
            tline1 = tline[4:]
            if len(tline1.strip()) == 0:
                self.tcalc.append("\n")
                continue
            exstr = ""
            if "|" == tline1[0]: 
                if " read " in tline1[:8]:
                    exstr = self.t_read(tline1)
                elif " write " in tline1[:8]:
                    extstr = self.t_write(tline1)
                elif " create " in tline1[:8]:
                    exstr = self.t_create(tline1)
                elif " insert " in tline1[:10]:
                    self.t_insert(tline1)
                elif " plot " in tline1[:8]:
                    cmd1, cmd2 = self.t_plot(tline1)
                    exec(cmd1)
                    exec(cmd2)
                    plt.savefig(self.pltfile)
                else:
                    self.tcalc.append(tline1)
                exec(exstr)
                continue
            if "=" in tline1:
                tline1a = tline1.split("|")
                if len(tline1a) > 1:
                    tcalc_eq = ""
                    tcalc_eq = tline1a[0].strip() 
                    exec(tcalc_eq)
                    self.tcalc.append(tcalc_eq + " | " + tline1a[1])        
                else:
                    exec(tline1a[0])
                    self.tcalc.append(tline1a)
            else: 
                self.tcalc.append(tline1)
        
        eq1 = []
        return locals(), self.tcalc, eq1
       
    def t_read(self, tline1: str) -> str:
        """[summary]
        
        Args:
            tline1 (str): [description]
        """
        tline1a = tline1.split("|")
        temp1 = tline1a[1].split("read")
        temp2 = temp1[1].split("to")
        filename = temp2[0].strip() + ".csv"
        tablename = temp2[1].strip()
        pathname = Path(self.folderd["tpath"], filename).as_posix()
        cmdline = tablename + " = pd.read_table(" + '"' + \
                        pathname + '"' +", sep=',')" 
        
        df = pd.read_csv(csvfiles, usecols = lambda x: x in list(col), 
                       skiprows = lambda x: x in list(rowl))     
        globals().update(locals())        
        return cmdline

    def t_write(self, tline1: str) -> str:
        """[summary]
        
        Args:
            tline1 (str): [description]
        """
        tline1a = tline1.split("|")
        temp1 = tline1a[1].split("write")
        temp2 = temp1[1].split("to")
        filename = temp2[1].strip() + ".csv"
        tablename = temp2[0].strip()
        pathname =  Path(self.folderd["tpath"], filename ).as_posix()
        cmdline = tablename + ".to_csv(" +  '"' + \
                        pathname +  '"' + ", sep=',')"
        
        return cmdline

    def t_create(self, tline1:str) -> str:
        """[summary]
        
        Args:
            tline (str): [description]
        """
        tline1a = tline1.split("|")
        temp = tline1a[1].split("new")
        tablename = temp[1].strip()
        cmdline = tablename + " = pd.DataFrame()"
        
        globals().update(locals())
        return cmdline

    def t_plot(self, tline1: str)-> list:
        """[summary]
        
        Args:
            tline (str): [description]
        """                
        tline1a = tline1.split("|")
        tline1b = (tline1a[1].strip()).split(" ")
        if len(tline1b) > 1:
            self.pltname = tline1b[1]
            filename = self.pltname + ".png"
            filepath = self.folderd["fpath"]
            self.pltfile = Path(filepath, filename).as_posix()
            pltcmd = tline1a[2].strip()
            cmdline1 = "ax = plt.gca()"
            cmdline2 = self.pltname + ".plot(" + pltcmd + ", ax=ax)"
        else:
            pltcmd = tline1a[2].strip()
            cmdline1 = ""
            cmdline2 = self.pltname + ".plot(" + pltcmd + ", ax=ax)"

        globals().update(locals())
        return cmdline1, cmdline2

    def t_insert(self, tline1: str):
        """[summary]
        
        Args:
            tline (str): [description]
        """
        tline1a = tline1.split("|")
        if ("png" in tline1a[1]) or ("jpg" in tline1a[1]):
            plt.close()
            filename = tline1a[1].split("insert")[1].strip()
            filepath = self.folderd["fpath"]
            imgfile = Path(filepath, filename).as_posix()
            img = mpimg.imread(imgfile)
            imgplot = plt.imshow(img)
            plt.pause(0.5)
            plt.draw()
            plt.pause(2)
        else:       
            tablename = tline1a[1].split("insert")[1].strip()
            print("ti", tablename)
            tabletitle = tline1a[2] + "\n"
            tname = eval(tablename)
            old_stdout = sys.stdout
            output = StringIO()
            output.write(tabulate(tname, tablefmt="grid", headers="firstrow"))            
            rstout = output.getvalue()
            sys.stdout = old_stdout

            self.tcalc.append(tabletitle)
            self.tcalc.append(rstout)

            globals().update(locals())
