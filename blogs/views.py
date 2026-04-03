import re

from .serializers import BlogPostSerializer
from .permissions import IsAdminOrReadOnly
# DRF
from rest_framework import viewsets, parsers, status
from rest_framework.response import Response

# models
from .models import BlogPost


class BlogPostViewSet(viewsets.ModelViewSet):
    serializer_class = BlogPostSerializer
    queryset = BlogPost.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"

    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def _normalize_payload(self, request):
        """Convert multipart keys like sections[0][title] into serializer-friendly nested data."""
        if isinstance(request.data, dict) and isinstance(request.data.get("sections"), list):
            return request.data

        section_pattern = re.compile(r"^sections\[(\d+)\](?:\[([a-z_]+)\]|([a-z_]+))(?:\[(\d+)\])?$")
        payload = {}

        for key in request.data.keys():
            values = request.data.getlist(key)
            payload[key] = values if len(values) > 1 else values[0]

        sections_map = {}
        section_keys = []

        for key in list(payload.keys()):
            match = section_pattern.match(key)
            if not match:
                continue

            section_keys.append(key)
            section_index = int(match.group(1))
            field_name = match.group(2) or match.group(3)
            list_item_index = match.group(4)

            section = sections_map.setdefault(section_index, {})
            value = payload[key]

            if field_name == "list_items":
                list_items = section.setdefault("list_items", [])
                if list_item_index is not None:
                    item_index = int(list_item_index)
                    while len(list_items) <= item_index:
                        list_items.append("")
                    list_items[item_index] = value
                elif isinstance(value, list):
                    list_items.extend(value)
                else:
                    list_items.append(value)
            else:
                section[field_name] = value

        for key in section_keys:
            payload.pop(key, None)

        if sections_map:
            payload["sections"] = [sections_map[index] for index in sorted(sections_map.keys())]

        return payload

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._normalize_payload(request))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=self._normalize_payload(request), partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def get_queryset(self):
        qs = BlogPost.objects.all()

        user = self.request.user
        if user.is_staff or user.is_superuser or getattr(user, "role", None) == "ADMIN":
            return qs

        return qs.filter(is_published=True)
