import os
from io import BytesIO
from http.server import SimpleHTTPRequestHandler
import socketserver
from urllib.parse import urlparse, parse_qsl
import configparser
import json

from xero.auth import PublicCredentials
from xero.exceptions import XeroException
from xero import Xero

PORT = 8000


# You should use redis or a file based persistent
# storage handler if you are running multiple servers.
OAUTH_PERSISTENT_SERVER_STORAGE = {}


class PublicCredentialsHandler(SimpleHTTPRequestHandler):
    def page_response(self, title='', body=''):
        """
        Helper to render an html page with dynamic content
        """
        f = BytesIO()
        f.write('<!DOCTYPE html">\n'.encode())
        f.write('<html>\n'.encode())
        f.write('<head><title>{}</title><head>\n'.format(title).encode())
        f.write('<body>\n<h2>{}</h2>\n'.format(title).encode())
        f.write('<div class="content">{}</div>\n'.format(body).encode())
        f.write('</body>\n</html>\n'.encode())
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        self.copyfile(f, self.wfile)
        f.close()

    def redirect_response(self, url, permanent=False):
        """
        Generate redirect response
        """
        if permanent:
            self.send_response(301)
        else:
            self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        """
        Handle GET request
        """
        config = configparser.ConfigParser()
        config.read('config.ini')

        consumer_key                    = config['APP']['XERO_CONSUMER_KEY']
        consumer_secret                 = config['APP']['XERO_CONSUMER_SECRET']
        callback_url                    = config['APP']['CALLBACK_URL']
        accounts_and_vendors_files_path = config['APP']['ACCOUNTS_AND_VENDORS_FILES_PATH']
        vendors_file_name               = config['APP']['VENDORS_FILE_NAME']
        accounts_file_name              = config['APP']['ACCOUNTS_FILE_NAME']

        if consumer_key is None or consumer_secret is None:
            raise KeyError(
                'Please define both XERO_CONSUMER_KEY and XERO_CONSUMER_SECRET variables in config.ini file')

        if callback_url is None:
            raise KeyError(
                'Please define callback_url in config.ini file')

        if accounts_and_vendors_files_path is None or vendors_file_name is None or vendors_file_name is None:
            raise KeyError(
                'Please define Account and Vendors file names and paths in config.ini file')

        print("Serving path: {}".format(self.path))
        path = urlparse(self.path)

        if path.path == '/do-auth':
            credentials = PublicCredentials(
                consumer_key, consumer_secret, callback_uri= callback_url)

            # Save generated credentials details to persistent storage
            for key, value in credentials.state.items():
                OAUTH_PERSISTENT_SERVER_STORAGE.update({key: value})

            # Redirect to Xero at url provided by credentials generation
            self.redirect_response(credentials.url)
            return

        elif path.path == '/oauth':
            params = dict(parse_qsl(path.query))
            if 'oauth_token' not in params or 'oauth_verifier' not in params or 'org' not in params:
                self.send_error(500, message='Missing parameters required.')
                return

            stored_values = OAUTH_PERSISTENT_SERVER_STORAGE
            credentials = PublicCredentials(**stored_values)

            try:
                credentials.verify(params['oauth_verifier'])

                # Resave our verified credentials
                for key, value in credentials.state.items():
                    OAUTH_PERSISTENT_SERVER_STORAGE.update({key: value})

            except XeroException as e:
                self.send_error(500, message='{}: {}'.format(e.__class__, e.message))
                return

            # Once verified, api can be invoked with xero = Xero(credentials)
            self.redirect_response('/verified')
            return

        elif path.path == '/verified':
            stored_values = OAUTH_PERSISTENT_SERVER_STORAGE
            credentials = PublicCredentials(**stored_values)

            try:
                xero = Xero(credentials)

            except XeroException as e:
                self.send_error(500, message='{}: {}'.format(e.__class__, e.message))
                return

            page_body = ''

            vendors  = xero.contacts.filter(IsSupplier=True)
            accounts = xero.accounts.all()

            if vendors:
                vendors_file = accounts_and_vendors_files_path + '/' + vendors_file_name
                with open(vendors_file, 'w') as fileVendors:
                    json.dump(vendors, fileVendors, indent=4, sort_keys=True, default=str)
                page_body += ('Check vendors list in ' + accounts_and_vendors_files_path
                            + '/' + vendors_file_name + '<br>')
            else:
                page_body += 'No vendors.\n'

            if accounts:
                accounts_file = accounts_and_vendors_files_path + '/' + accounts_file_name
                with open(accounts_file, 'w') as fileAccounts:
                    json.dump(accounts, fileAccounts, indent=4, sort_keys=True, default=str)
                    page_body += ('Check account list in ' + accounts_and_vendors_files_path
                                + '/' + accounts_file_name)
            else:
                page_body += 'No accounts.\n'

            self.page_response(title='Downloading vendor and account files', body=page_body)
            return

        SimpleHTTPRequestHandler.do_GET(self)


if __name__ == '__main__':
    httpd = socketserver.TCPServer(("", PORT), PublicCredentialsHandler)

    print("serving at port", PORT)
    httpd.serve_forever()
