from ._traefik import init_traefik, restart_traefik


def init():
    """ Initialize the current machine to be a PAAS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """

    print("MyPaas needs a domain name that will be used for")
    print("the dashboard, API endpoint, monitoring, etc.")
    print("This can be e.g. paas.mydomain.com, or admin.mydomain.com")
    print("Note that you must point the DNS record to this server.")
    paas_domain = input("Domain for this PAAS: ")

    # print("Traefik will use Let's Encrypt to get SSL/TSL certificates.")
    # print("Let's Encrypt needs an email address to use when something is wrong.")
    # email = input("Email for Let's Encrypt: ")
    email = ""

    print("Initializing Traefik")
    init_traefik(paas_domain, email)
    restart_traefik()

    # todo: Start deploy daemon
