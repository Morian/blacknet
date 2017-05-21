import ssl

from config import BlacknetConfigurationInterface
from common import *


class BlacknetSSLInterface(BlacknetConfigurationInterface):
    """ SSL Interface for all components using it """


    def __init__(self, config, role):
        BlacknetConfigurationInterface.__init__(self, config, role)
        self._server_sockfile = False
        self.__ssl_config = None
        self.__ssl_context = None


    @property
    def ssl_config(self):
        if not self.__ssl_config:
            cert = self.get_config('cert')
            cafile = self.get_config('cafile')
            hostname = None
            if self.has_config('server_hostname'):
                hostname = self.get_config('server_hostname')
            self.__ssl_config = (cert, cafile, hostname)
        return self.__ssl_config


    @property
    def ssl_context(self):
        if not self.__ssl_context:
            (cert, cafile, hostname) = self.ssl_config

            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.verify_flags = ssl.VERIFY_DEFAULT
            if ssl.HAS_ECDH:
                ssl_context.options |= ssl.OP_SINGLE_ECDH_USE
            ssl_context.load_verify_locations(cafile)
            ssl_context.load_cert_chain(cert)
            ssl_context.set_ciphers(":".join(BLACKNET_CIPHERS))
            if hostname:
                ssl_context.check_hostname = True
            self.__ssl_context = ssl_context
        return self.__ssl_context


    def reload(self):
        self.__ssl_config = None
        self.__ssl_context = None
