from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from follows import services
from notifications.models import Notification
from notifications.services import notify
from profiles.permissions import IsActiveProfile
from profiles.public_views import my_profile

from .models import Comment, PostLike
from .serializers import CommentCreateSerializer, CommentSerializer


def _visible_post_or_404(request, pk):
    # The ONLY way these endpoints find a post: through the viewer's visible set.
    return get_object_or_404(services.visible_posts(my_profile(request)), pk=pk)


class LikeView(APIView):
    """POST = like, DELETE = unlike. Idempotent both ways."""

    permission_classes = [permissions.IsAuthenticated, IsActiveProfile]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'like_write'

    def post(self, request, pk):
        post = _visible_post_or_404(request, pk)
        me = my_profile(request)
        _, created = PostLike.objects.get_or_create(post=post, profile=me)
        if created:
            notify(post.author, me, Notification.LIKE, post=post)
        return Response({'like_count': post.likes.count(), 'liked_by_me': True}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        post = _visible_post_or_404(request, pk)
        PostLike.objects.filter(post=post, profile=my_profile(request)).delete()
        return Response({'like_count': post.likes.count(), 'liked_by_me': False})


class CommentsPagination(CursorPagination):
    page_size = 30
    ordering = '-created_at'


class PostCommentsView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveProfile]
    pagination_class = CommentsPagination

    def get_serializer_class(self):
        return CommentCreateSerializer if self.request.method == 'POST' else CommentSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'viewer': my_profile(self.request)}

    def get_throttles(self):
        if self.request.method == 'POST':
            throttle = ScopedRateThrottle()
            self.throttle_scope = 'comment_create'
            return [throttle]
        return super().get_throttles()

    def get_queryset(self):
        viewer = my_profile(self.request)
        post = _visible_post_or_404(self.request, self.kwargs['pk'])
        return services.visible_comments(viewer).filter(post=post).select_related('author', 'author__avatar', 'post')

    def create(self, request, *args, **kwargs):
        post = _visible_post_or_404(request, kwargs['pk'])
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        me = my_profile(request)
        comment = serializer.save(post=post, author=me)
        notify(post.author, me, Notification.COMMENT, post=post, comment=comment)
        return Response(CommentSerializer(comment, context=self.get_serializer_context()).data,
                        status=status.HTTP_201_CREATED)


class CommentDeleteView(generics.DestroyAPIView):
    """A comment can be deleted by its author OR by the author of the post it
    is on (moderating your own thread). Anyone else's id is a 404."""

    permission_classes = [permissions.IsAuthenticated, IsActiveProfile]

    def get_queryset(self):
        me = my_profile(self.request)
        return Comment.objects.filter(Q(author=me) | Q(post__author=me))
