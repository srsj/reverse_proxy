_DEFAULT_LIMIT_TO_ALL_URLS = 60000  # rpm (1000 req x s)
_DEFAULT_LIMIT_TO_ALLL_IP = 600  # rpm (10 req x s)
_DEFAULT_LIMIT_TO_ALLL_URLIP = 120  # rpm (2 req+IP x s)

# Here we should add limits to certain IP's or URL. This should be defined by someone
# If it was not configured in advanced, a PUB SUB should be implemented here so that
# every instance of the proxy subscribes, and when someone publish a new default limit
# for a specific URL or specific IP we should update this dict.
# To add a limit for a IP (1.2.3.4) Eg: default_configuration['1.2.3.4'] = my_desired_limit
default_configuration = {'default_url': _DEFAULT_LIMIT_TO_ALL_URLS,
                         'default_ip': _DEFAULT_LIMIT_TO_ALLL_IP,
                         'default_urlip': _DEFAULT_LIMIT_TO_ALLL_URLIP
                         }
