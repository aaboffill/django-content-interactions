# coding=utf-8
import json
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import force_text
from django.utils.module_loading import import_by_path
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View, FormView, CreateView, UpdateView, DeleteView, ListView
from django.contrib.sites.models import Site
from forms import ShareForm, RateForm, DenounceForm, CommentForm
from utils import intmin
from models import Comment

logger = logging.getLogger(__name__)

MODAL_VALIDATION_ERROR_MESSAGE = _(u"A validation error has occurred.")
MODAL_SHARE_SUCCESS_MESSAGE = _(u"The item has been successfully shared.")
MODAL_RECOMMEND_SUCCESS_MESSAGE = _(u"The item has been successfully recommended.")
MODAL_RATE_SUCCESS_MESSAGE = _(u"The item has been successfully rated.")
MODAL_DENOUNCE_SUCCESS_MESSAGE = _(u"The item has been successfully denounced.")
MODAL_DELETE_DENOUNCE_SUCCESS_MESSAGE = _(u"The denounce has been successfully deleted.")
DELETE_COMMENT_SUCCESS_MESSAGE = _(u"The comment has been successfully deleted.")


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    response_class = HttpResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        response_kwargs['content_type'] = 'application/json'
        return self.response_class(
            self.convert_context_to_json(context),
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


class LikeView(JSONResponseMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            model = import_by_path(request.POST['model'])
            pk = request.POST['pk']
            instance = model.objects.get(pk=pk)

            if instance.liked_by(request.user):
                instance.unlike(request.user)
                tooltip = _(u"Like")
                toggle_status = False
            else:
                instance.like(request.user)
                tooltip = _(u"Unlike")
                toggle_status = True

            likes = instance.likes

            return self.render_to_response({
                'result': True,
                'toggle_status': toggle_status,
                'counter': likes,
                'counterStr': intmin(likes),
                'tooltip': force_text(tooltip)
            })

        except MultiValueDictKeyError as e:
            logger.exception(e)
            return self.render_to_response({'result': False})
        except ImproperlyConfigured as e:
            logger.exception(e)
            return self.render_to_response({'result': False})
        except Exception as e:
            logger.exception(e)
            return self.render_to_response({'result': False})


class FavoriteView(JSONResponseMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            model = import_by_path(request.POST['model'])
            pk = request.POST['pk']
            instance = model.objects.get(pk=pk)

            if instance.favorite_of(request.user):
                instance.delete_favorite(request.user)
                tooltip = _(u"Mark as Favorite")
                toggle_status = True
            else:
                instance.mark_as_favorite(request.user)
                tooltip = _(u"Not my Favorite")
                toggle_status = True

            favorite_marks = instance.favorite_marks

            return self.render_to_response({
                'result': True,
                'toggle_status': toggle_status,
                'counter': favorite_marks,
                'counterStr': intmin(favorite_marks),
                'tooltip': force_text(tooltip)
            })

        except Exception as e:
            logger.exception(e)
            return self.render_to_response({'result': False})


class ShareView(FormView):
    template_name = 'content_interactions/share.html'
    form_class = ShareForm

    def get_initial(self):
        content_type_pk = self.request.REQUEST.get('content_type', None)
        return {
            'content_type': ContentType.objects.get(pk=content_type_pk) if content_type_pk else None,
            'object_pk': self.request.REQUEST.get('object_pk', None),
            'user': self.request.user
        }

    def form_valid(self, form):
        """
        If the form is valid, share item.
        """
        form.share()
        context = {
            'successMsg': force_text(MODAL_SHARE_SUCCESS_MESSAGE),
        }
        return HttpResponse(json.dumps(context), content_type='application/json')

    def form_invalid(self, form):
        context = {
            'errorMsg': force_text(MODAL_VALIDATION_ERROR_MESSAGE)
        }
        return HttpResponseBadRequest(json.dumps(context), content_type='application/json')


class RateView(FormView):
    template_name = 'content_interactions/rate.html'
    form_class = RateForm

    def get_initial(self):
        content_type_pk = self.request.GET.get('content_type', None)
        content_type = ContentType.objects.get_for_id(content_type_pk) if content_type_pk else None
        object_pk = self.request.GET.get('object_pk', None)
        # find the related model
        model = content_type.get_object_for_this_type(**{'pk': object_pk}) if content_type and object_pk else None
        full_rating = model.full_rating(self.request.user) if model and model.rated_by(self.request.user) else None
        return {
            'content_type': content_type,
            'object_pk': object_pk,
            'rating': full_rating[0] if full_rating else self.request.GET.get('min_rate', 0),
            'user': self.request.user,
            'comment': full_rating[1] if full_rating else None,
        }

    def form_valid(self, form):
        """
        If the form is valid, save the rating associated with the model.
        """
        form.save_rating()
        context = {
            'successMsg': force_text(MODAL_RATE_SUCCESS_MESSAGE),
        }
        return HttpResponse(json.dumps(context), content_type='application/json')

    def form_invalid(self, form):
        context = {
            'errorMsg': force_text(MODAL_VALIDATION_ERROR_MESSAGE)
        }
        return HttpResponseBadRequest(json.dumps(context), content_type='application/json')


class DenounceView(FormView):
    template_name = 'content_interactions/denounce.html'
    form_class = DenounceForm

    def get_initial(self):
        content_type_pk = self.request.GET.get('content_type', None)
        content_type = ContentType.objects.get_for_id(content_type_pk) if content_type_pk else None
        object_pk = self.request.GET.get('object_pk', None)
        return {
            'content_type': content_type,
            'object_pk': object_pk,
            'user': self.request.user
        }

    def form_valid(self, form):
        """
        If the form is valid, toggle denounce status.
        """
        denounced = form.save_denounce()
        denounces = form.obj.denounces
        context = {
            'successMsg': force_text(MODAL_DENOUNCE_SUCCESS_MESSAGE) if denounced
            else force_text(MODAL_DELETE_DENOUNCE_SUCCESS_MESSAGE),
            'result': True,
            'toggle_status': denounced,
            'counter': denounces,
            'counterStr': intmin(denounces),
            'tooltip': force_text(_(u"Delete Denounce") if denounced else _(u"Denounce"))
        }
        return HttpResponse(json.dumps(context), content_type='application/json')

    def form_invalid(self, form):
        context = {
            'errorMsg': force_text(MODAL_VALIDATION_ERROR_MESSAGE)
        }
        return HttpResponseBadRequest(json.dumps(context), content_type='application/json')


class CommentViewMixin(object):
    model = Comment
    form_class = CommentForm

    def _get_model_str(self):
        raise ImproperlyConfigured('You must implement "_get_model_str" method.')

    def get_template_names(self):
        names = []
        names.append(
            "%s/%s/%s%s.html" % (
                self.model._meta.app_label,
                self._get_model_str(),
                self.model._meta.model_name,
                self.template_name_suffix
            )
        )
        names.append(
            "%s/%s%s.html" % (
                self.model._meta.app_label,
                self.model._meta.model_name,
                self.template_name_suffix
            )
        )
        return names

    def form_valid(self, form):
        self.object = form.save()
        self.template_name_suffix = "_detail"
        return self.render_to_response({
            'comment': self.object,
            'user': self.request.user
        })

    def form_invalid(self, form):
        context = {
            'errorMsg': force_text(MODAL_VALIDATION_ERROR_MESSAGE)
        }
        return HttpResponseBadRequest(json.dumps(context), content_type='application/json')


class CommentCreateView(CommentViewMixin, CreateView):

    def get(self, request, *args, **kwargs):
        self.template_name_suffix = "_create" if not "comment_pk" in kwargs else "_answer"
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(CommentCreateView, self).get_initial()
        initial.update({
            'content_type': ContentType.objects.get_for_id(self.kwargs.get('content_type_pk')),
            'object_pk': self.kwargs.get('object_pk'),
            'site': Site.objects.get_current(),
        })
        if self.request.user.is_authenticated:
            initial.update({'user': self.request.user})
        comment_pk = self.kwargs.get('comment_pk', False)
        if comment_pk:
            initial.update({'answer_to': Comment.objects.get(pk=comment_pk)})
        return initial

    def _get_model_str(self):
        return ContentType.objects.get_for_id(self.kwargs.get('content_type_pk')).model


class CommentUpdateView(CommentViewMixin,UpdateView):
    template_name_suffix = "_edit"

    def get_object(self, queryset=None):
        obj = super(CommentUpdateView, self).get_object(queryset)
        if self.request.user.pk != obj.user.pk:
            raise ImproperlyConfigured(_(u"The comment must be edited by the user creator."))
        return obj

    def _get_model_str(self):
        return self.get_object().content_object._meta.model_name


class CommentListView(ListView):
    model = Comment
    context_object_name = 'comments'
    content_object = None

    def get_queryset(self):
        content_type = ContentType.objects.get_for_id(self.kwargs.get('content_type_pk'))
        self.content_object = content_type.get_object_for_this_type(pk=self.kwargs.get('object_pk'))
        return self.model.on_site.for_model(self.content_object).first_level()

    def get_template_names(self):
        names = super(CommentListView, self).get_template_names()
        names.insert(
            0,
            "%s/%s/%s%s.html" % (
                self.model._meta.app_label,
                self.content_object._meta.model_name,
                self.model._meta.model_name,
                self.template_name_suffix
            )
        )
        return names


class CommentDeleteView(DeleteView):
    model = Comment

    def get_object(self, queryset=None):
        from django.contrib.auth.models import User

        obj = super(CommentDeleteView, self).get_object(queryset)
        comment_manager = obj.content_object.get_comments_manager()
        if (isinstance(comment_manager, User) and comment_manager.pk != self.request.user.pk) and self.request.user.pk != obj.user.pk:
            raise ImproperlyConfigured(
                _(u"The comment must be deleted by the user creator or user content_type manager.")
            )
        return obj

    def delete(self, request, *args, **kwargs):
        """
        Calls the delete() method on the fetched object and then
        redirects to the success URL.
        """
        self.object = self.get_object()
        context = {
            'successMsg': force_text(DELETE_COMMENT_SUCCESS_MESSAGE),
            'result': True,
            'pk': self.object.pk,
        }
        self.object.delete()
        return HttpResponse(json.dumps(context), content_type='application/json')

