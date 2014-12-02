# coding=utf-8
import logging
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.contrib.sites.models import Site
from social_graph import Graph, EdgeType, ATTRIBUTES
from . import LIKE, LIKED_BY, RATE, RATED_BY, FAVORITE, FAVORITE_OF, DENOUNCE, DENOUNCED_BY
from .signals import (
    item_liked,
    item_disliked,
    item_marked_as_favorite,
    item_unmarked_as_favorite,
    item_rated,
    item_rate_modified,
    item_denounced,
    item_denounce_removed
)

logger = logging.getLogger(__name__)

graph = Graph()


def like_edge():
    like = cache.get('LIKE_EDGE_TYPE')
    if like is not None:
        return like
    try:
        like = EdgeType.objects.get(name=LIKE)
        cache.set('LIKE_EDGE_TYPE', like)
        return like
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def liked_by_edge():
    liked_by = cache.get('LIKED_BY_EDGE_TYPE')
    if liked_by is not None:
        return liked_by
    try:
        liked_by = EdgeType.objects.get(name=LIKED_BY)
        cache.set('LIKED_BY_EDGE_TYPE', liked_by)
        return liked_by
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def rate_edge():
    rate = cache.get('RATE_EDGE_TYPE')
    if rate is not None:
        return rate
    try:
        rate = EdgeType.objects.get(name=RATE)
        cache.set('RATE_EDGE_TYPE', rate)
        return rate
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def rated_by_edge():
    rated_by = cache.get('RATED_BY_EDGE_TYPE')
    if rated_by is not None:
        return rated_by
    try:
        rated_by = EdgeType.objects.get(name=RATED_BY)
        cache.set('RATED_BY_EDGE_TYPE', rated_by)
        return rated_by
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def favorite_edge():
    favorite = cache.get('FAVORITE_EDGE_TYPE')
    if favorite is not None:
        return favorite
    try:
        favorite = EdgeType.objects.get(name=FAVORITE)
        cache.set('FAVORITE_EDGE_TYPE', favorite)
        return favorite
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def favorite_of_edge():
    favorite_of = cache.get('FAVORITE_OF_EDGE_TYPE')
    if favorite_of is not None:
        return favorite_of
    try:
        favorite_of = EdgeType.objects.get(name=FAVORITE_OF)
        cache.set('FAVORITE_OF_EDGE_TYPE', favorite_of)
        return favorite_of
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def denounce_edge():
    denounce = cache.get('DENOUNCE_EDGE_TYPE')
    if denounce is not None:
        return denounce
    try:
        denounce = EdgeType.objects.get(name=DENOUNCE)
        cache.set('DENOUNCE_EDGE_TYPE', denounce)
        return denounce
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


def denounced_by_edge():
    denounced_by = cache.get('DENOUNCED_BY_EDGE_TYPE')
    if denounced_by is not None:
        return denounced_by
    try:
        denounced_by = EdgeType.objects.get(name=DENOUNCED_BY)
        cache.set('DENOUNCED_BY_EDGE_TYPE', denounced_by)
        return denounced_by
    except EdgeType.DoesNotExist as e:
        logger.exception(e)


class ContentInteractionMixin(object):

    def get_site(self):
        return getattr(self, 'site', Site.objects.get_current())


class LikableMixin(ContentInteractionMixin):
    @property
    def likes(self):
        return graph.edge_count(self, liked_by_edge(), self.get_site())

    def liked_by(self, user):
        return graph.edge_get(self, liked_by_edge(), user, self.get_site()) is not None

    def like(self, user):
        _edge = graph.edge(user, self, like_edge(), self.get_site(), {})
        if _edge:
            item_liked.send(sender=self.__class__, instance=self, user=user)
        return _edge

    def unlike(self, user):
        _deleted = graph.no_edge(user, self, like_edge(), self.get_site())
        if _deleted:
            item_disliked.send(sender=self.__class__, instance=self, user=user)
        return _deleted


class FavoriteListItemMixin(ContentInteractionMixin):
    @property
    def favorite_marks(self):
        return graph.edge_count(self, favorite_of_edge(), self.get_site())

    def favorite_of(self, user):
        return graph.edge_get(self, favorite_of_edge(), user, self.get_site()) is not None

    def mark_as_favorite(self, user):
        _edge = graph.edge(user, self, favorite_edge(), self.get_site(), {})
        if _edge:
            item_marked_as_favorite.send(sender=self.__class__, instance=self, user=user)
        return _edge

    def delete_favorite(self, user):
        _deleted = graph.no_edge(user, self, favorite_edge(), self.get_site())
        if _deleted:
            item_unmarked_as_favorite.send(sender=self.__class__, instance=self, user=user)
        return _deleted


class RateableMixin(ContentInteractionMixin):
    def rating(self, user):
        _edge = graph.edge_get(self, rated_by_edge(), user, self.get_site())
        return _edge[ATTRIBUTES]['rating'] if _edge is not None else None

    def full_rating(self, user):
        _edge = graph.edge_get(self, rated_by_edge(), user, self.get_site())
        return (
            _edge[ATTRIBUTES]['rating'] if _edge is not None else None,
            _edge[ATTRIBUTES]['comment'] if _edge is not None else None
        )

    def rated_by(self, user):
        return graph.edge_get(self, rated_by_edge(), user, self.get_site()) is not None

    def save_rate(self, user, rating, comment=None):
        _edge = graph.edge(user, self, rate_edge(), self.get_site(), {'rating': rating, 'comment': comment})
        if _edge:
            item_rated.send(sender=self.__class__, instance=self, user=user, rating=rating, comment=comment)
        return _edge

    def change_rate(self, user, rating, comment=None):
        old_rating = self.rating(user)
        _edge = graph.edge(user, self, rate_edge(), self.get_site(), {'rating': rating, 'comment': comment})
        if _edge:
            item_rate_modified.send(
                sender=self.__class__,
                instance=self,
                user=user,
                old_rating=old_rating,
                rating=rating,
                comment=comment
            )
        return _edge


class DenounceTargetMixin(ContentInteractionMixin):
    @property
    def denounces(self):
        return graph.edge_count(self, denounced_by_edge(), self.get_site())

    def denounced_by(self, user):
        return graph.edge_get(self, denounced_by_edge(), user, self.get_site()) is not None

    def denounce_comment(self, user):
        _edge = graph.edge_get(self, denounced_by_edge(), user, self.get_site())
        return _edge[ATTRIBUTES]['comment'] if _edge is not None else None

    def denounce(self, user, comment):
        _edge = graph.edge(user, self, denounce_edge(), self.get_site(), {'comment': comment})
        if _edge:
            item_denounced.send(sender=self.__class__, instance=self, user=user, comment=comment)
        return _edge

    def remove_denounce(self, user):
        _deleted = graph.no_edge(user, self, denounce_edge(), self.get_site())
        if _deleted:
            item_denounce_removed.send(sender=self.__class__, instance=self, user=user)
        return _deleted


class LikableManagerMixin(object):
    graph = graph

    def liked_by(self, user):
        like = like_edge()
        count = self.graph.edge_count(user, like)
        content_type = ContentType.objects.get_for_model(self.model)
        ids = [node.pk for node, attributes, time in self.graph.edge_range(user, like, 0, count) if ContentType.objects.get_for_model(node) == content_type]
        return self.get_queryset().filter(pk__in=ids)


class FavoriteListItemManagerMixin(object):
    graph = graph

    def favorites(self, user):
        favorite = favorite_edge()
        count = self.graph.edge_count(user, favorite)
        content_type = ContentType.objects.get_for_model(self.model)
        ids = [node.pk for node, attributes, time in self.graph.edge_range(user, favorite, 0, count) if ContentType.objects.get_for_model(node) == content_type]
        return self.get_queryset().filter(pk__in=ids)


class DenounceTargetManagerMixin(object):
    graph = graph

    def denounced_by(self, user):
        denounce = denounce_edge()
        count = self.graph.edge_count(user, denounce)
        content_type = ContentType.objects.get_for_model(self.model)
        ids = [node.pk for node, attributes, time in self.graph.edge_range(user, denounce, 0, count) if ContentType.objects.get_for_model(node) == content_type]
        return self.get_queryset().filter(pk__in=ids)