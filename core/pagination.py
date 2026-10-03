from django.core.paginator import Paginator

DEFAULT_PER_PAGE = 25


def paginate(request, queryset, per_page=DEFAULT_PER_PAGE):
    """Return the requested page of a queryset.

    The page object is iterable, so templates can loop over it exactly like the
    queryset they used before.
    """
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))
