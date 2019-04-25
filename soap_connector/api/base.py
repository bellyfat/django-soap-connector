from typing import Type, List, ClassVar

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.reverse import reverse
from rest_framework.serializers import Serializer

from soap_connector.cache import Cache, Context

URL_NAMES = ['settings']


@api_view()
def root(request):
    """

    :param request:
    :return:
    """
    return Response({
        f'{name}': reverse(f'soap_connector:{name}_list', request=request)
        for name in URL_NAMES
    })


class SerializerMixin(object):
    """

    """
    serializer_class: ClassVar[Type[Serializer]] = None

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for
        validating and deserializing input, and for serializing
        output.
        """
        serializer_class: Type[Serializer] = \
            self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()

        return serializer_class(*args, **kwargs)

    def get_serializer_class(self) -> Type[Serializer]:
        """
        Provide different serializations depending on the
        object class.

        :return:
        """
        assert self.serializer_class is not None, (
                "'%s' should either include a `serializer_class` attribute, "
                "or override the `get_serializer_class()` method."
                % self.__class__.__name__)

        return self.serializer_class

    def get_serializer_context(self) -> Context:
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'view': self
        }


class BaseAPIView(SerializerMixin, APIView):
    """

    """
    object_class: ClassVar[type] = None

    def set_context(self, object_class: type,
                    serializer_class: Type[Serializer] = None):
        """

        :param object_class:
        :param serializer_class:
        :return:
        """
        self.object_class = object_class

        if serializer_class is not None:
            self.serializer_class = serializer_class

    @property
    def cache(self) -> Cache:
        """

        :return:
        """
        context: Context = self.get_serializer_context()
        cache = Cache(context)

        return cache

    def list(self, request: Request, *args, **kwargs) -> Response:
        """

        :param request:
        :return:
        """
        object_list: List[dict] = self.cache.values()
        if object_list:
            return Response(object_list, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)

    def get(self, request: Request, *args, **kwargs) -> Response:
        """

        :param request:
        :return:
        """
        pk: int = kwargs.get('pk', None)
        if pk is None:
            return self.list(request)
        else:
            data: dict = self.cache[pk]
            if data is not None:
                return Response(data, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)

    def post(self, request: Request, *args, **kwargs) -> Response:
        """

        :param request:
        :return:
        """
        if 'pk' in kwargs:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        context: Context = self.get_serializer_context()
        serializer: Serializer = self.serializer_class(
            data=request.data, context=context
        )
        if serializer.is_valid():
            data: dict = serializer.create(serializer.data)
            return Response(data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_409_CONFLICT)

    def delete(self, request: Request, *args, **kwargs) -> Response:
        """

        :param request:
        :return:
        """
        pk: int = kwargs.get('pk', None)

        if pk is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        elif self.cache[pk]:
            del self.cache[pk]
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request: Request, *args, **kwargs) -> Response:
        """

        :param request:
        :return:
        """
        if 'pk' not in kwargs or \
                kwargs['pk'] not in self.cache:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            context: Context = self.get_serializer_context()
            serializer = self.serializer_class(
                data=request.data, context=context
            )
            if serializer.is_valid():
                data = serializer.update(None, serializer.data)
                return Response(data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_409_CONFLICT)
