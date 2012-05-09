#!/usr/bin/env python
# simpatico.py
#
# Version: 0.1
# Authors: Sean Purdon
#          Jackson Gatenby
#
# Note: this is just a basis, feel free to
# start over with much structured approach.
# I personally think a C tokenizer will be 
# needed for simple and reliable style 
# marking instead of pure regex..

import sys
import os
import re

import tokenizer

sswith = lambda x, y: x.strip().startswith(y)
sewith = lambda x, y: x.strip().endswith(y)

def check_all():
    """Check all the .c and .h files in the current directory

    """
    files = [x for x in os.listdir(os.getcwd())
             if x.endswith('.c') or x.endswith('.h')]

    for f in files:
        print '%s:'%f
        check(f)
        print

NAMING = "Naming"
BRACES = "Braces"
INDENTATION = "Indentation"
WHITESPACE = "Whitespace"
COMMENTS = "Comments"
OVERALL = "Overall"
LINELENGTH = "Line length"

INDENT = 4

TYPES = {'int', 'char', 'size_t', 'pid_t', 'bool', 'long', 'short',
         'float', 'double', 'long double', 'FILE', 'void'}

class StyleChecker(object):
    def __init__(self, filename):
        self.filename = filename
        with open(filename, 'r') as f:
            self.lines = [line.rstrip('\n') for line in f.readlines()]
        self.tokens = tokenizer.tokenize(filename)

        self.errors = []
        self.types = set(TYPES)

    def check(self):
        # keep track of information about expected level of indents
        self.indent = 0

        self.check_line_lengths()
        for self.pos in xrange(len(self.tokens)):
            self.check_names()
            self.check_indent()

    def _error(self, linenum, type, message):
        self.errors.append((linenum, type, message))

    def check_line_lengths(self):
        """Check the line lengths of the *whole file*"""
        for lnum, line in enumerate(self.lines, 1):
            if len(line) > 79:
               self._error(lnum, LINELENGTH, "{} characters".format(len(line)))

    def check_names(self):
        """Check if the next token is a definition with an invalid name
        
        Known/suspected issues:
        * Will not differentiate between variable and function definitions.
        * Will not check typedefs, structs, #defines, etc.

        """
        token = self.tokens[self.pos]
        if token.type == 'identifier':
            # Is this the definition of this name?
            if self.pos >= 2 and self.tokens[self.pos-1].type == 'space' and \
                    self.tokens[self.pos-2].type in self.types:
                # Is it an invalid name?
                # Check: is the first letter lowercase?
                if not token.value[0].islower():
                    self._error(token.linenum, NAMING, "({})".format(token.value))

    def check_indent(self):
        """Check if the next token is an incorrect indentation.

        Also, if the current token requires that future indents be at a different
        level, then make note of that.

        Known/suspected issues:
        * Cannot account for two dedents at the end of a switch statement.
        * Cannot account for double indent of multi-line statements.
        * Might break if braces are wrong in some instances. e.g. this would be picked up as correct indentation:

        if (1 == 1) {
        return; }

        """
        token = self.tokens[self.pos]
        # Does this token require different indentation on the next line?
        nextline = [t.type for t in self.tokens if t.linenum == token.linenum + 1]
        if token.type in ('leftbrace', 'case', 'switch'):
            self.indent += 1
        elif token.type == 'newline' and ('rightbrace' in nextline or 'case' in nextline):
            self.indent -= 1

        if token.type == 'newline':
            # check the next line is blank or has correct indentation
            nexttok = self.tokens[self.pos + 1]
            if (self.indent > 0 and
                    nexttok.type not in ('newline', 'eof') and
                    (nexttok.type != 'space' or len(nexttok.value) != INDENT * self.indent)):
                # There is an error on the next line
                msg = "Expected {} got {}".format(INDENT * self.indent, len(nexttok.value))
                self._error(token.linenum + 1, INDENTATION, msg)
            elif self.indent == 0 and nexttok.type == 'space':
                # There is an error on the next line
                msg = "Expected {} got {}".format(INDENT * self.indent, len(nexttok.value))
                self._error(token.linenum + 1, INDENTATION, msg)


    def report(self):
        errors = sorted(self.errors)
        for linenum, type, message in errors:
            print "{:>4}: {}: {}".format(linenum, type, message)


def check(filename):
    """Check a file for errors.

    """
    checker = StyleChecker(filename)
    checker.check()
    checker.report()

def check_braces(lines):
    errors = []

    for n, line in enumerate(lines):
        if sswith(line, '*') or sswith(line, '/*'):
            continue
        
        if (' while' in line or ' for' in line or ' do' in line
            or ' if' in line or ' else' in line or ' switch' in line):
            i = 0
            while '{' not in lines[n + i] and ';' not in lines[n + i]:
                i += 1
                line = lines[n + i]

            if '{' in line:
                lst = line.rsplit('{', 1)
                if lst[0][-1] != ' ':
                    errors.append((n+1, 'Braces Error (spacing)'))

        if 'else' in line:
            if not sswith(line, '}'):
                errors.append((n+1, 'Braces Error (else placement)'))
            else:
                if line.split('{')[0][-1] != ' ':
                    errors.append((n+1, 'Braces Error (spacing)'))

    return errors

def check_horiz_whitespace(lines):
    errors = []

    for n, line in enumerate(lines):
        if sswith(line, '*') or sswith(line, '/*'):
            continue
        
        for c in (',', ';'):
            if not check_char_spacing(line, c):
                errors.append((n+1, "Horizontal Whitespace Error (%s)"%c))

        for c in ('=', '+=', '-=', '/=', '*='):
            if not check_char_spacing(line, c, True):
                errors.append((n+1, "Horizontal Whitespace Error (%s)"%c))

    return errors

def check_char_spacing(line, c, before=False):
    if c == '=':
        line = line.replace('==', '')
        line = line.replace('!=', '')
        line = line.replace('+=', '')
        line = line.replace('-=', '')
        line = line.replace('/=', '')
        line = line.replace('*=', '')
        line = line.replace('<=', '')
        line = line.replace('>=', '')
        
    if c not in line:
        return True
    lst = line.split(c)

    for i, s in enumerate(lst):
        if not s:
            continue
        if (i and s[0] not in ' \n') or (before and i != len(lst)-1 and s[-1] != ' '):
            return False
    return True

def check_naming(lines):
    errors = []

    seenTypedef = False
    inTypedef = False
    
    for n, line in enumerate(lines):
        if 'typedef' in line:
            seenTypedef = True
        if '{' in line and seenTypedef:
            inTypedef = True
        if '}' in line and inTypedef:
            inTypedef = False
            seenTypedef = False
            t = line.rstrip().split()[-1].rstrip(';')
            validTypes.append(t)
            if t[0].islower():
                errors.append((n+1, 'Type Naming Error (%s)'%t))
    
    matchStr = r'(unsigned )?(%s)\**\s+\**(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)'%'|'.join(validTypes)

    for n, line in enumerate(lines):
        if sswith(line, '*') or sswith(line, '/*'):
            continue
        
        match = re.search(matchStr, line)
        if match is not None:
            _, _, svs = line.partition(match.groups()[1])
            decs = [x for x in svs.split(',') if x.strip()]

            vs = [match.group('var')]
            if len(decs) > 1:
                for dec in decs:
                    m2 = re.search(matchStr, dec)
                    if m2 is None:
                        continue
                    vs.append(m2.group('var'))

            if line[0] != ' ':
                vs = vs[1:]

            vs = [x.strip('*,') for x in vs]
            vs = [x for x in vs if x]

            for v in vs:
                if v[0].isupper():
                    errors.append((n+1,"Variable Naming Error (%s)"%v))

    for n, line in enumerate(lines):
        if line.startswith('#define '):
            define = line.split()[1]
            for c in define:
                if c.islower():
                    errors.append((n+1, "#define Naming Error (%s)"%define))
                    break
    
    return errors

def check_line_lengths(lines):
    errors = []

    for n, line in enumerate(lines):
        if len(line) > 79:
            errors.append((n+1, 'Line Length Error (%s characters)'%len(line)))

    return errors

def check_indents(lines):
    errors = []
    
    indent = 0
    idc = ' '*4

    dbrackets = 0

    lineCont = False
    inCase = False
    
    for n, line in enumerate(lines):
        # skip lines with only whitespace or comments
        if not line.strip() or sswith(line, '/*'):
            continue

        #handle falling out of case without break
        if inCase and sswith(line, '}') and indent == caseIndent:
            inCase = False
        
        if inCase and sswith(line, 'case '):
            inCase = False
        # special case of closing brace needing to be one back
        # special case of line continuation (needing two further indents)
        # special case of case statements (need one further indent)
        reqindent = indent - sswith(line, '}') + lineCont*2 + inCase
        if ((not line.startswith(idc*reqindent)
             or line.startswith(idc*reqindent+' '))
             and not sswith(line, '*')):
            errors.append((n+1,
                           'Indentation error (expected %d, got %d)'%(
                               len(idc*reqindent), len(line) - len(line.lstrip()))))

        indent += count_char(line, '{') - count_char(line, '}')

        dbrackets += (count_char(line, '(') - count_char(line, ')'))
        lineCont = dbrackets > 0
        if not lineCont:
            dbrackets = 0

        if sswith(line, 'case ') or sswith(line, 'default:'):
            inCase = True
            caseIndent = indent
        if inCase and sswith(line, 'break;'):
            inCase = False

    return errors

  

def count_char(string, char):
    n = 0
    for c in string:
        if c == char:
            n += 1
    return n

def check_function_lengths_names(lines):
    errors = []

    inFunction = False
    curFunctiion = ''
    c = 0

    for n, line in enumerate(lines):
        if inFunction:
            c += 1
            if line.startswith('}'):
                inFunction = False

                if c > 50:
                    errors.append((n+1-c,
                                   'Function Length Error (%s is %s lines)'%(
                                       curFunction, c)))

                c = 0

        else:
            if not line_is_function_or_prototype(line):
                continue
            if sewith(line, ';') or (sewith(line, ',')
                             and sewith(lines[n+1], ';')):
                continue

            curFunction = line.partition(' ')[2].partition('(')[0]
            inFunction = True

            for ch in curFunction:
                if ch.isupper():
                    errors.append((n+1,
                            'Function Naming Error (%s contains uppercase)'%(
                                curFunction)))
                    break
            

    return errors

def line_is_function_or_prototype(line):
    if line and line[0] in ' {}/#' or not line.strip():
        return False
    if 'typedef' in line or 'struct' in line or 'union' in line:
        return False
    return True

def get_lines(filename):
    """Get a list of lines out of the given filename

    """
    return [x+'\n' for x in remove_comments_and_strings(filename).split('\n')]

def remove_comments_and_strings(filename):
    f = open(filename, 'U')

    s = ''

    inComment = False
    inString = False
    inChar = False

    preComment = False
    preEndComment = False

    for line in f:
        line = line.rstrip('\n')
        for c in line:
            if c == '"':
                inString = not inString
            if c == "'":
                inChar = not inChar
            if preComment:
                preComment = False
                if c == '*':
                    inComment = True
                    s = s[:-1]
                if c == '/':
                    break
            else:
                if c == '/':
                    preComment = True
            if c == '*':
                preEndComment = True
            elif preEndComment:
                if c == '/':
                    if inComment:
                        inComment = False
                        continue
                preEndComment = False
            if inComment or inString or inChar:
                continue
            s += c
        inString = False
        inChar = False
        preComment = False
        preEndComment = False
        s += '\n'
        
    return s
    

#####
import signal

def sigint_handler(signum, frame):
    print 'Failed to parse file.'
    exit()
    
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    #try:
        for i in range(1, len(sys.argv)):
            if sys.argv[i].strip():
                print
                print 'Parsing %s...'%sys.argv[i]
                check(sys.argv[i])
    #except:
#        sigint_handler(None, None)
