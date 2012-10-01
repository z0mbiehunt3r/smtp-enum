__license__= '''
smtp-enum - Enumerates email accounts through different methods

Copyright (C) 2012  Alejandro Nolla Blanco - alejandro.nolla@gmail.com 
Nick: z0mbiehunt3r - @z0mbiehunt3r
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
Should improve exception handler and compare results for thread Vs multiprocess
'''

import multiprocessing
import os
import re
import socket
import sys

try:
   import dns.resolver 
except ImportError:
   print 'You need dnspython (http://www.dnspython.org/)'
   sys.exit(-1)


"""
SMTP commands are character strings terminated by <CRLF> (http://tools.ietf.org/html/rfc821)

"Constants" to use when checking available methods
"""
EHLOCOMMAND = 'EHLO test\r\n'
VRFYCOMMAND = 'VRFY postmaster\r\n'
EXPNCOMMAND = 'EXPN postmaster\r\n'
MAILFROMCOMMAND = 'MAIL FROM: <admin@gmail.com>\r\n'
BUFFERSIZE = 1024
RCPTTOACCOUNT = 'inexistentaccount123'


########################################################################
class smtpEnumerator():
   """
   Class used to store info about enumerated domain, allowed methods, enumerated email accounts and so
   """

   #----------------------------------------------------------------------
   def __init__(self, host, port, domain):
      """Constructor"""

      self.host = host
      self.port = port
      self.domain = domain

      self.banner = ''
      self.methods_allowed = []
      self.verified_accounts = []
      self.expn_available = False
      self.vrfy_available = False
      self.rcpto_available = False

   #----------------------------------------------------------------------
   def readBanner(self):
      """
      Connect to SMTP server and read banner
      """

      try:
	 sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	 sock.connect((self.host, self.port))

	 response = sock.recv(BUFFERSIZE)
	 sock.close()

	 replycode = response[0:3]
	 banner = response.rstrip()
	 self.banner = banner

      except Exception, e:
	 pass

   #----------------------------------------------------------------------
   def checkMethods(self):
      """
      Connect to SMTP server and send EHLO command to get accepted commands
      """
      try:
	 sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	 sock.connect((self.host, self.port))

	 # Read banner
	 sock.recv(BUFFERSIZE)

	 sock.send(EHLOCOMMAND)
	 response = sock.recv(BUFFERSIZE)
	 sock.close()

	 replycode = response[0:3]

	 # Don't insert SMTP code as method
	 methods_allowed = response.splitlines()[1:]

	 # Method looks like 250-SIZE
	 for method in methods_allowed:
	    # Remove SMTP code
	    self.methods_allowed.append(method[4:])

      except Exception, e:
	 pass

   #----------------------------------------------------------------------
   def checkEXPNMethod(self):
      """
      Use EXPN command to try to expand a mail list

      For the EXPN command, the string identifies a mailing list, and the
      successful (i.e., 250) multiline response MAY include the full name
      of the users and MUST give the mailboxes on the mailing list.

      (http://tools.ietf.org/html/rfc821#page-8)
      """

      if 'EXPN' in self.methods_allowed:
	 # Check if it's really available
	 try:
	    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    sock.connect((self.host, self.port))

	    # Read banner
	    sock.recv(BUFFERSIZE)

	    sock.send(EHLOCOMMAND)
	    response = sock.recv(BUFFERSIZE)

	    sock.send(EXPNCOMMAND)
	    response = sock.recv(BUFFERSIZE)
	    replycode = response[0:3]
	    sock.close()

	    if replycode[0] == '2':
	       self.expn_available = True
	    else:
	       self.expn_available = False

	 except Exception, e:
	    pass

      return self.expn_available

   #----------------------------------------------------------------------
   def checkVRFYMethod(self):
      """
      For the VRFY command, the string is a user name, and the response may
      include the full name of the user and must include the mailbox of the user.

      (http://tools.ietf.org/html/rfc821#page-8)
      """

      if 'VRFY' in self.methods_allowed:
	 # Check if it's really available
	 try:
	    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    sock.connect((self.host, self.port))

	    # Read banner
	    sock.recv(BUFFERSIZE)

	    sock.send(EHLOCOMMAND)
	    response = sock.recv(BUFFERSIZE)

	    sock.send(VRFYCOMMAND)
	    response = sock.recv(BUFFERSIZE)
	    replycode = response[0:3]
	    sock.close()

	    if replycode == '250' or replycode == '251':
	       self.vrfy_available = True
	    else:
	       self.vrfy_available = False

	 except Exception, e:
	    pass

      return self.vrfy_available        

   #----------------------------------------------------------------------
   def enumerateVRFY(self, accounts, processes):
      """
      Enumerate accounts through VRFY SMTP method

      S: VRFY Smith
      R: 250 Fred Smith <Smith@USC-ISIF.ARPA>

      (http://tools.ietf.org/html/rfc821#page-8)

      @param accounts: Accounts to test if exist (['alejandro', 'miguelin'])
      @type accounts: list

      @param processes: Number of simultaneous processes to use
      @type processes: int

      @return: Enumerated accounts (['miguelin'])
      @rtype: list
      """

      if not self.vrfy_available:
	 return []

      # Shared list with accounts to process
      accounts_input = multiprocessing.Manager().list()
      accounts_input.extend(accounts)
      # Shared list with processed accounts
      accounts_output = multiprocessing.Manager().list()

      # Pool of processes
      m_pool = multiprocessing.Pool(processes)

      # Start working
      for p in range(processes):
	 m_pool.apply_async(enumerateVRFYWorker, (self.host, self.port, self.domain, accounts_input, accounts_output))

      # Wait until finished...
      m_pool.close()
      m_pool.join()      

      return accounts_output

   #----------------------------------------------------------------------
   def enumerateEXPN(self, accounts, processes):
      """
      Enumerate accounts through EXPN SMTP method

      S: EXPN Example-People
      R: 250-Jon Postel <Postel@USC-ISIF.ARPA>
      R: 250-Fred Fonebone <Fonebone@USC-ISIQ.ARPA>
      R: 250-Sam Q. Smith <SQSmith@USC-ISIQ.ARPA>
      R: 250-Quincy Smith <@USC-ISIF.ARPA:Q-Smith@ISI-VAXA.ARPA>
      R: 250-<joe@foo-unix.ARPA>
      R: 250 <xyz@bar-unix.ARPA>

      (http://tools.ietf.org/html/rfc821#page-9)

      @param accounts: Accounts to test if exist (['alejandro', 'miguelin'])
      @type accounts: list

      @param processes: Number of simultaneous processes to use
      @type processes: int

      @return: Enumerated accounts (['miguelin'])
      @rtype: list
      """

      if not self.expn_available:
	 return []

      # Shared list with accounts to process
      accounts_input = multiprocessing.Manager().list()
      accounts_input.extend(accounts)
      # Shared list with processed accounts
      accounts_output = multiprocessing.Manager().list()

      # Pool of processes
      m_pool = multiprocessing.Pool(processes)

      # Start working
      for p in range(processes):
	 m_pool.apply_async(enumerateEXPNWorker, (self.host, self.port, self.domain, accounts_input, accounts_output))

      # Wait until finished...
      m_pool.close()
      m_pool.join()      

      return accounts_output

   #----------------------------------------------------------------------
   def checkRCPTTOMethod(self):
      """
      Only useful if server returns different responses depending on whether or not the account

      S: RCPT TO:<Jones@Beta.ARPA>
      R: 250 OK

      S: RCPT TO:<Green@Beta.ARPA>
      R: 550 No such user here

      (http://tools.ietf.org/html/rfc821#page-6)
      """

      try:
	 sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	 sock.connect((self.host, self.port))

	 # Read banner
	 sock.recv(BUFFERSIZE)

	 sock.send(EHLOCOMMAND)
	 response = sock.recv(BUFFERSIZE)

	 sock.send(MAILFROMCOMMAND)
	 response = sock.recv(BUFFERSIZE)

	 # Compose receiver account@domain
	 sock.send('RCPT TO: <%s@%s>\r\n' %(RCPTTOACCOUNT, self.domain))
	 response = sock.recv(BUFFERSIZE)

	 """
	 Sometimes we may be listed as spammer in some black list
	 NEED IMPROVEMENT!
	 """
	 if re.search('spam', response):
	    print '[!] Your IP address is listed as SPAMMER!!!'
	    sys.exit(-1)

	 replycode = response[0:3]

	 if replycode == '550':
	    self.rcpto_available = True
	 else:
	    self.rcpto_available = False

      except Exception, e:
	 pass

      return self.rcpto_available

   #----------------------------------------------------------------------
   def enumerateRCPTTO(self, accounts, processes):
      """
      Enumerate accounts based on different responses depending on whether or not the account

      S: RCPT TO:<Jones@Beta.ARPA>
      R: 250 OK

      S: RCPT TO:<Green@Beta.ARPA>
      R: 550 No such user here

      (http://tools.ietf.org/html/rfc821#page-6)

      @param accounts: Accounts to test if exist (['alejandro', 'miguelin'])
      @type accounts: list

      @param processes: Number of simultaneous processes to use
      @type processes: int

      @return: Enumerated accounts (['miguelin'])
      @rtype: list
      """

      if not self.rcpto_available:
	 return []

      # Shared list with accounts to process
      accounts_input = multiprocessing.Manager().list()
      accounts_input.extend(accounts)
      # Shared list with processed accounts
      accounts_output = multiprocessing.Manager().list()

      # Pool of processes
      m_pool = multiprocessing.Pool(processes)

      # Start working
      for p in range(processes):
	 m_pool.apply_async(enumerateRCPTTOWorker, (self.host, self.port, self.domain, accounts_input, accounts_output))

      # Wait until finished...
      m_pool.close()
      m_pool.join()

      return accounts_output

   #----------------------------------------------------------------------
   def writeAccounts(self, outputfile):
      """
      Just write already enumerated accounts saved in smtpEnumerator object to a text file

      @param outputfile: Text file to write accounts
      @type outputfile: str
      """

      if os.path.exists(outputfile):
	 response = ''
	 print '[!] Output file %s exists, data will be overwritten!' %outputfile
	 while response != 'Y' and response != 'N':
	    # Make it uppercase and remove trailing whitespace
	    response = raw_input('Overwrite? (Y/N) ').upper().rstrip()

	    if response == 'N':
	       print '[*] Exiting...'
	       sys.exit(0)
      else:
	 fd = open(outputfile, mode='w')
	 for account in self.verified_accounts:
	    fd.write('%s\n' %account)
	 fd.close()

#----------------------------------------------------------------------
def getMX(domain):
   """
   Make a DNS query to get MX entries for given domain

   @param domain: Domain which MX entries want to get
   @type domain: str

   @return: List of MX entries and their preferences ([['mx1.acme.local',10], ['mx2.acme.local',20]])
   @rtype: list
   """

   mxentries = []

   try:
      answers = dns.resolver.query(domain, rdtype=dns.rdatatype.MX)
      for answer in answers:
	 preference = answer.preference
	 # answer -> '20 mail02.xxxxx.com.'
	 name = answer.to_text().split(' ')[1].rstrip('.')
	 mxentries.append([name, preference])      
   except:
      pass

   return mxentries


"""
Workers section, out of class because of pickle problem...

socket.setdefaulttimeout() also affect multiprocessing...
http://bugs.python.org/issue6056
"""

#----------------------------------------------------------------------
def enumerateVRFYWorker(host, port, domain, accounts_input, accounts_output):
   """
   Worker to enumerate accounts through VRFY SMTP method

   S: VRFY Smith
   R: 250 Fred Smith <Smith@USC-ISIF.ARPA>

   @param host: SMTP server to connect ('mx1.acme.local' / '10.10.10.123')
   @type host: str

   @param port: SMTP server port
   @type port: int

   @param domain: Domain which email accounts want to enumerate ('acme.local')
   @type domain: str

   @param accounts_input: Shared list with accounts to test (['alejandro', 'miguelin'])
   @type accounts_input: list

   @param accounts_output: Shared list to write enumerated accounts (['miguelin'])
   @type accounts_output: list
   """

   try:
      while len(accounts_input) > 0:
	 account = accounts_input.pop()
	 try:
	    #socket.setdefaulttimeout(timeout)
	    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    sock.connect((host, port))

	    # Read banner
	    sock.recv(BUFFERSIZE)

	    sock.send(EHLOCOMMAND)
	    response = sock.recv(BUFFERSIZE)

	    sock.send('VRFY %s@%s\r\n' %(account, domain))
	    response = sock.recv(BUFFERSIZE)
	    replycode = response[0:3]
	    if replycode[0] == '2':
	       accounts_output.append(account)

	    sock.close()
	    #socket.setdefaulttimeout(0)

	 except Exception, e:
	    pass	    
   except KeyboardInterrupt:
      print 'Ctrl^C - killing process...'
      return

#----------------------------------------------------------------------
def enumerateEXPNWorker(host, port, domain, accounts_input, accounts_output):
   """
   Worker to enumerate accounts through EXPN SMTP method

   S: EXPN Example-People
   R: 250-Jon Postel <Postel@USC-ISIF.ARPA>
   R: 250-Fred Fonebone <Fonebone@USC-ISIQ.ARPA>
   R: 250-Sam Q. Smith <SQSmith@USC-ISIQ.ARPA>
   R: 250-Quincy Smith <@USC-ISIF.ARPA:Q-Smith@ISI-VAXA.ARPA>
   R: 250-<joe@foo-unix.ARPA>
   R: 250 <xyz@bar-unix.ARPA>

   @param host: SMTP server to connect ('mx1.acme.local' / '10.10.10.123')
   @type host: str

   @param port: SMTP server port
   @type port: int

   @param domain: Domain which email accounts want to enumerate ('acme.local')
   @type domain: str

   @param accounts_input: Shared list with accounts to test (['alejandro', 'miguelin'])
   @type accounts_input: list

   @param accounts_output: Shared list to write enumerated accounts (['miguelin'])
   @type accounts_output: list   
   """

   try:
      while len(accounts_input) > 0:
	 account = accounts_input.pop()      
	 try:
	    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    sock.connect((host, port))

	    # Read banner
	    sock.recv(BUFFERSIZE)

	    sock.send(EHLOCOMMAND)
	    response = sock.recv(BUFFERSIZE)

	    sock.send('EXPN %s\r\n' %account)
	    response = sock.recv(BUFFERSIZE)
	    replycode = response[0:3]

	    # List name exists
	    if replycode[0] == '2':
	       users = response.splitlines()
	       for user in users:
		  #if verbosity: print user
		  regex = re.search('<(.+)>', user)
		  if regex is not None:
		     emailaddress = regex.group(1)
		     if emailaddress not in accounts_output: accounts_output.append(emailaddress)
	    sock.close()   
	 except:
	    pass

   except KeyboardInterrupt:
      print 'Ctrl^C - killing process...'
      return      

#----------------------------------------------------------------------
def enumerateRCPTTOWorker(host, port, domain, accounts_input, accounts_output):
   """
   Worker to enumerate accounts through RCPT TO SMTP method

   S: RCPT TO:<Jones@Beta.ARPA>
   R: 250 OK

   S: RCPT TO:<Green@Beta.ARPA>
   R: 550 No such user here

   @param host: SMTP server to connect ('mx1.acme.local' / '10.10.10.123')
   @type host: str

   @param port: SMTP server port
   @type port: int

   @param domain: Domain which email accounts want to enumerate ('acme.local')
   @type domain: str

   @param accounts_input: Shared list with accounts to test (['alejandro', 'miguelin'])
   @type accounts_input: list

   @param accounts_output: Shared list to write enumerated accounts (['miguelin'])
   @type accounts_output: list     
   """
   try:
      while len(accounts_input) > 0:
	 account = accounts_input.pop()
	 try:
	    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    sock.connect((host, port))

	    # Read banner
	    sock.recv(BUFFERSIZE)

	    sock.send(EHLOCOMMAND)
	    response = sock.recv(BUFFERSIZE)

	    sock.send(MAILFROMCOMMAND)
	    response = sock.recv(BUFFERSIZE)
	    sock.send('RCPT TO: <%s@%s>\r\n' %(account, domain))
	    response = sock.recv(BUFFERSIZE)
	    replycode = response[0:3]

	    # List name exists
	    if replycode[0] == '2':
	       accounts_output.append('%s@%s' %(account, domain))
	    sock.close()

	 except Exception, e:
	    pass    
   except KeyboardInterrupt:
      print 'Ctrl^C - killing process...'
      return