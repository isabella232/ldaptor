# See rfc2253

escapedChars = r',+"\<>;'
escapedChars_leading = r' #'
escapedChars_trailing = r' #'

def escape(s):
    r=''
    r_trailer=''

    if s and s[0] in escapedChars_leading:
	r='\\'+s[0]
	s=s[1:]

    if s and s[-1] in escapedChars_trailing:
	r_trailer='\\'+s[-1]
	s=s[:-1]

    for c in s:
	if c in escapedChars:
	    r=r+'\\'+c
	elif ord(c)<=31:
	    r=r+'\\%02X' % ord(c)
	else:
	    r=r+c

    return r+r_trailer

def unescape(s):
    r=''
    while s:
	if s[0]=='\\':
	    if s[1] in '0123456789abcdef':
		r=r+chr(int(s[1:3], 16))
		s=s[3:]
	    else:
		r=r+s[1]
		s=s[2:]
	else:
	    r=r+s[0]
	    s=s[1:]
    return r

def _splitOnNotEscaped(s, separator):
    if not s:
	return []

    r=['']
    while s:
	if s[0]=='\\':
	    r[-1]=r[-1]+s[:2]
	    s=s[2:]
	else:
	    if s[0] in separator:
		r.append('')
		s=s[1:]
		while s[0]==' ':
		    s=s[1:]
	    else:
		r[-1]=r[-1]+s[0]
		s=s[1:]
    return r

class InvalidRelativeDistinguishedName(Exception):
    """Invalid relative distinguished name."""

    def __init__(self, rdn):
        Exception.__init__(self)
        self.rdn = rdn

    def __str__(self):
        return "Invalid relative distinguished name %s." \
               % repr(self.rdn)

class LDAPAttributeTypeAndValue:
    # TODO I should be used everywhere
    def __init__(self, stringValue=None, attributeType=None, value=None):
        if stringValue is None:
	    assert attributeType is not None
	    assert value is not None
	    self.attributeType = attributeType
            self.value = value
	else:
	    assert attributeType is None
	    assert value is None
            try:
                self.attributeType, self.value = stringValue.split('=', 1)
            except ValueError, e:
                if str(e) == 'unpack list of wrong size':
                    raise InvalidRelativeDistinguishedName, stringValue
                else:
                    raise

    def __str__(self):
	return '='.join((escape(self.attributeType), escape(self.value)))

    def __repr__(self):
	return (self.__class__.__name__
		+ '(attributeType='
		+ repr(self.attributeType)
		+ ', value='
		+ repr(self.value)
		+ ')')

    def __hash__(self):
	return hash((self.attributeType, self.value))

    def __eq__(self, other):
	if not isinstance(other, LDAPAttributeTypeAndValue):
	    return NotImplemented
	return (self.attributeType == other.attributeType
                and self.value == other.value)

    def __ne__(self, other):
	return not (self == other)

class RelativeDistinguishedName:
    """LDAP Relative Distinguished Name."""

    def __init__(self, stringValue=None, attributeTypesAndValues=None):
	if stringValue is None:
	    assert attributeTypesAndValues is not None
            import types
            assert not isinstance(attributeTypesAndValues, types.StringType)
	    self.attributeTypesAndValues = tuple(attributeTypesAndValues)
	else:
	    assert attributeTypesAndValues is None
	    self.attributeTypesAndValues = tuple([LDAPAttributeTypeAndValue(stringValue=unescape(x))
						  for x in _splitOnNotEscaped(stringValue, '+')])

    def split(self):
	return self.attributeTypesAndValues

    def __str__(self):
	return '+'.join([str(x) for x in self.attributeTypesAndValues])

    def __repr__(self):
	return (self.__class__.__name__
		+ '(attributeTypesAndValues='
		+ repr(self.attributeTypesAndValues)
		+ ')')

    def __hash__(self):
	return hash(self.attributeTypesAndValues)

    def __eq__(self, other):
	if not isinstance(other, RelativeDistinguishedName):
	    return NotImplemented
	return self.split() == other.split()

    def __ne__(self, other):
	return not (self == other)

    def count(self):
	return len(self.attributeTypesAndValues)


class DistinguishedName:
    """LDAP Distinguished Name."""

    def __init__(self, stringValue=None, listOfRDNs=None):
	if stringValue is None:
	    assert listOfRDNs is not None
	    for x in listOfRDNs:
		assert isinstance(x, RelativeDistinguishedName)
	    self.listOfRDNs = tuple(listOfRDNs)
	else:
	    assert listOfRDNs is None
	    self.listOfRDNs = tuple([RelativeDistinguishedName(stringValue=x)
				     for x in _splitOnNotEscaped(stringValue, ',')])

    def split(self):
	return self.listOfRDNs

    def up(self):
	return DistinguishedName(listOfRDNs=self.listOfRDNs[1:])

    def __str__(self):
	return ','.join([str(x) for x in self.listOfRDNs])

    def __repr__(self):
	return (self.__class__.__name__
		+ '(listOfRDNs='
		+ repr(self.listOfRDNs)
		+ ')')

    def __hash__(self):
	return hash(self.listOfRDNs)

    def __eq__(self, other):
	if not isinstance(other, DistinguishedName):
	    return NotImplemented
	return self.split() == other.split()

    def __ne__(self, other):
	return not (self == other)

    def getDomainName(self):
	domainParts = []
	l=list(self.listOfRDNs)
	l.reverse()
	for rdn in l:
	    if rdn.count() != 1:
		break
	    attributeTypeAndValue = rdn.split()[0]
	    if attributeTypeAndValue.attributeType.upper() != 'DC':
		break
	    domainParts.insert(0, attributeTypeAndValue.value)
	if domainParts:
	    return '.'.join(domainParts)
	else:
	    return None

    def contains(self, other):
	"""Does the tree rooted at DN contain or equal the other DN."""
	if self == other:
	    return 1
        if not isinstance(other, DistinguishedName):
            other=DistinguishedName(other)
	its=list(other.split())
	mine=list(self.split())

	while mine and its:
	    m=mine.pop()
	    i=its.pop()
	    if m!=i:
		return 0
	if mine:
	    return 0
	return 1