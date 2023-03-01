import re

# build regex query
protocol = r'https?://'  # Match http or https
ipv4 = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'  # This will match numbers over 255 so invalid IPs will register
ipv6 = r'(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))' #https://stackoverflow.com/questions/53497/regular-expression-that-matches-valid-ipv6-addresses
char = r'[A-Za-z0-9_-]'
domain = char + r'+(\.' + char + r'+)+'
tld_domain = domain + r'\.(com|uk|org|edu|gov|net|ca|de|jp|fr|au|us|ru|ch|it|nl|se|no|es|mil|co|int|biz|info|io|ly|tech)'
# if protocol is not provided we need to have a tld to check that its not a typo e.g. ~google.com~ should be found but not 'end of ~sentence.beginning~ of next sentence'
port = r'(?::\d+)?'
path = r'((?:/?|[/?]\S+)$)?'

query = r''
query += protocol + domain + port + path  # Accept any domain if http(s) is specified. This allows custom DNS domains such as localhost (although not realistic in a phishing attack)
query += r'|' + tld_domain + port + path  # Accept domain without protocol if tld is found. Port and path are optional
query += r'|(' + protocol + r')?' + r'(' + ipv4 + r'|' + '\[' + ipv6 + '\]' + r')' + port + path  # Accept  ipv4 with optional protocol, port and path
query += r'|' + ipv6  # Accept valid ipv6 address as URL (without protocol, port or path)


def is_link(test_string):
    match = re.fullmatch(query, test_string)
    if match:
        return match.group()
    else:
        return None

def find_all_matches(test_list):
    matches = []
    for possible_match in test_list:
        link = is_link(possible_match)
        if link:
            matches.append(link)
    return matches
