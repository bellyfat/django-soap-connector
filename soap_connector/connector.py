import logging
import operator
import math
from typing import List, Optional

from django.template.defaultfilters import slugify

from rest_framework.reverse import reverse

from zeep.client import Client
from zeep.wsdl.definitions import Service, Port
from zeep.wsdl.messages.soap import SoapMessage
from zeep import xsd

from soap_connector.serializers import ClientSerializer
from soap_connector.api.base import BaseAPIView

logger = logging.getLogger(__name__)


def to_number(s: str) -> int:
    """
    Transform 's' parameter into number and returns it.

    :param s:
    :return:
    """
    return int.from_bytes(s.encode(), 'little')


def from_number(n: int) -> str:
    """
    Transform 'n' parameter into string and returns it.

    :param n:
    :return:
    """
    return n.to_bytes(math.ceil(n.bit_length() / 8), 'little').decode()


def parser(parts: Optional[List[str]] = ()):
    """
    Returns a parser signature.

    :param parts:
    :return:
    """
    for part in parts:
        params = part.split(', ')
        for param in params:
            qname, _type = param.split(': ')
            yield qname, _type


def signature(soap_message: SoapMessage):
    if not soap_message.envelope:
        return None

    if soap_message.body:
        parts = [soap_message.body.type.signature(schema=soap_message.wsdl.types, standalone=False)]

        # print("PARTS: ", parts)
        # print("TYPE: ", soap_message.body.type)
        # print("ELEMENTS: ", soap_message.body.type.elements)
        # print("ELEMENTS_NESTED: ", soap_message.body.type.elements_nested)
        # print("ATTRIBUTES: ", soap_message.body.type.attributes)

        for element in soap_message.body.type.elements:
            # print("0: ", element[0])
            # print("1: ", element[1].get_prefixed_name(soap_message.wsdl.types), type(element[1].type).__name__)
            pass

    else:
        parts = []

        # if soap_message.header.type._element:
        #     print("ELEMENT: ", soap_message.header.type._element, type(soap_message.header.type._element))
        #     print("TYPE: ", soap_message.header.type, type(soap_message.header.type))
        #
        #     parts.append('_soapheaders={%s}' % soap_message.header.type.signature(
        #         schema=soap_message.wsdl.types, standalone=False))

    return parts


class Connector(object):
    """

    """

    def __init__(self, client: dict, **kwargs):
        """

        :param kwargs:
        """
        fields = {
            key: value for key, value in client.items()
            if client and key in ClientSerializer.Meta.fields
        }
        self.client = Client(**fields)
        self.client_pk = client['pk']
        self.context = kwargs['context']

    @classmethod
    def from_view(cls, view: BaseAPIView) -> "Connector":
        """

        :param view:
        :return:
        """
        assert issubclass(view.object_class, Client), (
                "'%s' needs that view context be a Client object "
                "class in order to retrieve serialized client data "
                "from cache."
                % cls.__name__)
        context = view.get_serializer_context()
        pk = view.kwargs['pk']
        client = view.cache[pk]
        if client:
            return cls(client, context=context)

    @property
    def prefixes(self):
        """

        :return:
        """
        object_list = []

        for data in self.client.wsdl.types.prefix_map.items():
            pk = slugify(data[0])
            url = self.resolver('prefix', prefix_pk=pk)
            object_list.append({
                'pk': pk,
                'prefix': data[0],
                'namespace': data[1],
                'url': url})

        return object_list

    @property
    def global_elements(self):
        """

        :return:
        """
        elements = self.client.wsdl.types.elements
        object_list = []

        for obj in sorted(elements, key=lambda k: k.qname):
            element = obj.signature(schema=self.client.wsdl.types)
            if element:
                pk = slugify(element)
                url = self.resolver('global_element', element_pk=pk)
                object_list.append({'pk': pk, 'global_element': element, 'url': url})

        return object_list

    @property
    def global_types(self):
        """

        :return:
        """
        object_list = []
        for type_obj in sorted(
                self.client.wsdl.types.types,
                key=lambda k: k.qname or ''):
            signature = type_obj.signature(schema=self.client.wsdl.types)

            if signature:
                prefixed_name = type_obj.get_prefixed_name(schema=self.client.wsdl.types)
                pk = prefixed_name or signature
                url = self.resolver('global_type', type_pk=slugify(pk))
                object_list.append({
                    'pk': slugify(pk),
                    'prefix': self.resolver('prefix', prefix_pk=pk.rsplit(':', 1)[0]),
                    'name': type_obj.name,
                    'signature': signature,
                    'url': url
                })

        return object_list

    @property
    def bindings(self):
        """

        :return:
        """
        object_list = []
        for binding_obj in sorted(
                self.client.wsdl.bindings.values(),
                key=lambda k: str(k)):
            pk = slugify(binding_obj.name.localname)
            url = self.resolver('binding', binding_pk=pk)
            object_list.append({
                'pk': pk,
                'name': binding_obj.name.localname,
                'namespace': binding_obj.name.namespace,
                'port_name': str(binding_obj.port_name),
                'url': url
            })

        return object_list

    @property
    def services(self):
        """

        :return:
        """
        object_list = []
        for service in self.client.wsdl.services.values():
            pk = slugify(service.name)
            url = self.resolver('service', service_pk=pk)
            object_list.append({
                'pk': pk,
                'service': service.name,
                'ports': self.ports(service),
                'url': url
            })

        return object_list

    def ports(self, service: Service):
        """

        :return:
        """
        object_list = []
        for port in service.ports.values():
            pk = slugify(port.name)
            url = self.resolver('port', service_pk=slugify(service.name), port_pk=pk)
            object_list.append({
                'pk': pk,
                'port': port.name,
                'operations': self.operations(service, port),
                'url': url
            })

        return object_list

    def operations(self, service: Service, port: Port):
        """

        :return:
        """
        object_list = []
        operations = sorted(
            port.binding._operations.values(),
            key=operator.attrgetter('name')
        )
        for operation in operations:
            pk = slugify(operation.name)
            url = self.resolver(
                'operation',
                service_pk=slugify(service.name),
                port_pk=slugify(port.name),
                operation_pk=pk)
            object_list.append({'pk': pk, 'operation': operation.name, 'url': url})

        return object_list

    def resolver(self, name, **kwargs):
        """

        :return:
        """
        return reverse(
            f'soap_connector:client_' + name + '_detail',
            kwargs={'pk': self.client_pk, **kwargs},
            request=self.context['request']
        )
