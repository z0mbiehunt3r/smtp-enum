smtp-enum
=========

Enumerates email accounts through different methods

Requisites
-----
You will need argparse (<http://code.google.com/p/argparse/>) and dnspython (<http://www.dnspython.org/>), can be installed easily through pip (<http://pypi.python.org/pypi/pip>).

Usage
-----
```
$ ./main.py -d acme.local -f accounts.txt -m all -o ./enumerated.txt
```