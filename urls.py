from django.urls import path

from .views import CommentDeleteView, LikeView, PostCommentsView

# Mounted under /api/posts/
post_engagement_urlpatterns = [
    path('<uuid:pk>/like/', LikeView.as_view(), name='post-like'),
    path('<uuid:pk>/comments/', PostCommentsView.as_view(), name='post-comments'),
]

# Mounted under /api/comments/
urlpatterns = [
    path('<uuid:pk>/', CommentDeleteView.as_view(), name='comment-delete'),
]
