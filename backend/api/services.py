import rest_framework.serializers as slz
import base64
from django.core.files.base import ContentFile


BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Base64ImageField(slz.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class Base62Field():

    def to_base62(num):

        if num == 0:
            return BASE62_ALPHABET[0]

        base62 = []
        while num:
            base62.append(BASE62_ALPHABET[num % 62])
            num //= 62

        return ''.join(reversed(base62))

    def from_base62(short_code):
        num = 0
        for char in short_code:
            num = num * 62 + BASE62_ALPHABET.index(char)
        return num
