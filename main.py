#!/usr/bin/env python
#coding:utf-8


__license__= '''
smtp-enum - Enumerates email accounts through different methods

Copyright (C) 2012  Alejandro Nolla Blanco - alejandro.nolla@gmail.com 
Nick: z0mbiehunt3r - Twitter: https://twitter.com/z0mbiehunt3r
Blog: navegandoentrecolisiones.blogspot.com


This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

'''
You've got desire
So let it out
You've got the fire
Stand up and shout

You are the strongest chain
And not just some reflection
So never hide again

Dio - Stand up and Shout
'''


import multiprocessing
import sys

try:
    import argparse
except ImportError:
    print 'You need argparse (http://code.google.com/p/argparse/)'
    sys.exit(-1)

# Own library
import smtpEnumerator

def __banner():
    """
    Print banner... no, really?
    """
    
    banner = '''
        |----------------------------------------------------------|
        |                         smtp-enum                        |
        |               Alejandro Nolla (z0mbiehunt3r)             |
        |                                      Powered by buguroo! |
        |----------------------------------------------------------|\n'''
    
    print banner

#----------------------------------------------------------------------    
def __checkArgs():
    """
    It checks if enough arguments are given, if not, show program help
    """
    
    if len(sys.argv) < 9:
        parser.print_help()
        sys.exit(-1)

#----------------------------------------------------------------------
def __readAccounts(accountsfile):
    """
    Read a given text file and returns account list
    
    @param filepath: Text file to read
    @type filepath: str
    
    @return: List of accounts ['anolla', 'alejandro.nolla']
    @rtype: list    
    """
    
    try:
        fd = open(accountsfile, mode='r')
    except:
        print '[!] Error reading accounts from %s' %accountsfile
        sys.exit(-1)
        
    accounts = fd.readlines()
    # Remove trailing whitespace
    accounts = map(str.rstrip, accounts)
    
    return accounts
    

#----------------------------------------------------------------------        
if __name__=='__main__':
    
    __banner()
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Enumerate SMTP accounts', add_help=False)
    
    gr1 = parser.add_argument_group('Main arguments')
    gr1.add_argument('-d', '--domain', dest='domain', required=True, help='Domain analyzed')
    gr1.add_argument('-f', '--file', dest='accounts', required=True, help='File with accounts')
    gr1.add_argument('-o', '--output', dest='output', required=True, help='Output file')
    gr1.add_argument('-m', '--method', dest='methods', required=True, choices=['vrfy', 'expn', 'rcptto', 'all'], help='Enumeration method(s) to use')
    
    gr2 = parser.add_argument_group('Optional arguments')
    gr2.add_argument('-s', '--server', dest='server', required=False, help='SMTP server to analyze')    
    gr2.add_argument('-p', '--port', dest='port', required=False, type=int, default=25, help='SMTP server port')
    gr2.add_argument('--processes', dest='processes', action='store', type=int, required=False, help='number of process to use (default one per core)', default=multiprocessing.cpu_count())
    gr2.add_argument('--full-smtp', dest='fullsmtp', action='store_true', required=False, help='enumerate against all SMTP servers')
    
    # Check if enough arguments are given
    __checkArgs()
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        accounts = __readAccounts(args.accounts)
        print '[*] Readed %i accounts to test' %len(accounts)
        
        # Need to get MX servers?
        if not args.server:
            print '[*] MX server not provided, going to retrieve them...'
            mxservers = smtpEnumerator.getMX(args.domain)
            
            if len(mxservers) == 0:
                print '[!] Couldn\'t retrieve any MX server...'
                sys.exit(-1)
            
            for x, mxserver in enumerate(mxservers):
                print '   [%i] %s {priority %i}' %(x,mxserver[0], mxserver[1])
            
            smtp_servers_targets = [] # store smtp servers for enumerate against to
            total_verified_accounts = set()
            
            if args.fullsmtp:
                smtp_servers_targets = [smtp_server[0] for smtp_server in mxservers]
            else:
                response = False
                # Ask for MX server to use
                while response is False:
                    try:
                        response = int(raw_input('Server to use? '))
                        smtp_servers_targets.append(mxservers[response][0])
                    except IndexError:
                        response = False
        
        else:
            smtp_servers_targets = [args.server]
        
        for smtp_server in smtp_servers_targets:
            print '[*] Going to enumerate email accounts against %s with method %s' %(smtp_server, args.methods.upper())
        
            se = smtpEnumerator.smtpEnumerator(smtp_server, args.port, args.domain)
            
            print '[*] Checking supported SMTP commands'
            # Not being listed as available methods doesn't mean that it isn't supported... just saying
            if not se.checkMethods():
                print '[!] Server didn\'t answered/supported EHLO, maybe blocked for spammer?'
                sys.exit()
            
            # Check selected methods
            if args.methods == 'vrfy':
                if 'VRFY' not in se.methods_allowed:
                    print '   [!] VRFY method seems not available'
                    print '[-] Finished'
                    sys.exit()
                else:
                    # is it really available to enumerate accounts?
                    if se.checkVRFYMethod():
                        print '[+] VRFY method can be used, going to enumerate accounts'
                        se.verified_accounts = se.enumerateVRFY(accounts, args.processes)
                        if len(se.verified_accounts) == 0:
                            print '   [-] Couldn\'t enumerate any account'
                        else:
                            for verified_account in se.verified_accounts:
                                print '   <--> %s' %verified_account
                    else:
                        # It's a trap!
                        print '   [!] VRFY method was listed as accepted but seems not available'
                        print '[-] Finished'
                        sys.exit()                
                                
            elif args.methods == 'expn':
                if 'EXPN' not in se.methods_allowed:
                    print '   [!] EXPN method seems not available'
                    print '[-] Finished'
                    sys.exit()
                else:
                    # is it really available to enumerate accounts?
                    if se.checkEXPNMethod():
                        print '[+] EXPN method can be used, going to enumerate accounts'
                        se.verified_accounts = se.enumerateEXPN(accounts, args.processes)
                        if len(se.verified_accounts) == 0:
                            print '   [-] Couldn\'t enumerate any account'
                        else:
                            for verified_account in se.verified_accounts:
                                print '   <--> %s' %verified_account
                    else:
                        # It's a trap!
                        print '   [!] EXPN method was listed as accepted but seems not available'
                        print '[-] Finished'
                        sys.exit()                
            
            elif args.methods == 'rcptto':
                if se.checkRCPTTOMethod():
                    print '[+] RCPT TO method can be used, going to enumerate accounts'
                    se.verified_accounts = se.enumerateRCPTTO(accounts, args.processes)
                    if len(se.verified_accounts) == 0:
                        print '   [-] Couldn\'t enumerate any account'
                    else:
                        for verified_account in se.verified_accounts:
                            print '   <--> %s' %verified_account
                else:
                    print '   [!] RCPT TO method seems not available'
                    print '[-] Finished'
                    sys.exit()            
            
            elif args.methods == 'all':
                verified_accounts = []
                
                # VRFY method
                if se.checkVRFYMethod():
                    print '[+] VRFY method can be used, going to enumerate accounts'
                    new_accounts = se.enumerateVRFY(accounts, args.processes)
                    if len(new_accounts) == 0:
                        print '   [-] Couldn\'t enumerate any account'
                    else:
                        verified_accounts.extend(new_accounts)
                        for new_account in new_accounts:
                            print '   <--> %s' %new_account         
                
                # EXPN method
                if se.checkEXPNMethod():
                    print '[+] EXPN method can be used, going to enumerate accounts'
                    new_accounts = se.enumerateEXPN(accounts, args.processes)
                    if len(new_accounts) == 0:
                        print '   [-] Couldn\'t enumerate any account'
                    else:
                        verified_accounts.extend(new_accounts)
                        for new_account in new_accounts:
                            print '   <--> %s' %new_account
                
                # RCPT TO method
                if se.checkRCPTTOMethod():
                    print '[+] RCPT TO method can be used, going to enumerate accounts'
                    new_accounts = se.enumerateRCPTTO(accounts, args.processes)
                    if len(new_accounts) == 0:
                        print '   [-] Couldn\'t enumerate any account'
                    else:
                        verified_accounts.extend(new_accounts)                    
                        for new_account in new_accounts:
                            print '   <--> %s' %new_account
                
                # Insert total verified accounts to smtpEnumerator object
                se.verified_accounts = verified_accounts
            total_verified_accounts.update(set(se.verified_accounts))


        total_verified_accounts.update(set(se.verified_accounts))
        if len(total_verified_accounts) > 0:
            se.verified_accounts = total_verified_accounts # quick 'n dirty...
            print '[*] Saved enumerated accounts {%i}...' %len(se.verified_accounts)
            se.writeAccounts(args.output)
            print '[-] Done'
        else:
            print '[-] 0 accounts enumerated...'
            

    except KeyboardInterrupt:
        print 'Exiting...'
        sys.exit()
