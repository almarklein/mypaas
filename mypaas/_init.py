from ._traefik import init_traefik, restart_traefik


def init():
    """ Initialize the current machine to be a PAAS. You will be asked
    a few questions, so Traefik and the deploy server can be configured
    correctly.
    """

    print("Traefik provides a dashboard that displays the complete routing")
    print("config of your PAAS. Please pick a domain to host this dashboard")
    print("on (e.g. traefik.mydomain.com). Note that you must point the DNS")
    print("record to your server.")
    dashboard_domain = input("Domain for the Traefik dashboard: ")

    print("Traefik will use Let's Encrypt to get SSL/TSL certificates.")
    print("Let's Encrypt needs an email address to use when something is wrong.")
    email = input("Email for Let's Encrypt: ")

    print("Initializing Traefik")
    init_traefik(email, dashboard_domain)
    restart_traefik()

    # todo: Start deploy server
    # todo: Start deploy daemon
