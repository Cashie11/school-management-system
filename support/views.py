from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import super_admin_required

from .forms import SupportMessageForm
from .help_content import grouped_guides, guide_by_slug
from .models import SupportMessage
from .services import queue_support_message


def help_index(request):
    return render(request, "support/help_index.html", {"guide_groups": grouped_guides()})


def help_article(request, slug):
    guide = guide_by_slug(slug)
    if guide is None:
        raise Http404("Unknown help article")
    return render(request, "support/help_article.html", {"guide": guide})


def contact(request):
    if request.method == "POST":
        form = SupportMessageForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):
                # Honeypot filled: a bot. Show the normal confirmation and drop it.
                return redirect("support:contact_done")
            support_message = form.save(commit=False)
            if request.user.is_authenticated and request.user.school_id:
                support_message.school_id = request.user.school_id
            support_message.save()
            queue_support_message(support_message)
            return redirect("support:contact_done")
    else:
        initial = {}
        if request.user.is_authenticated:
            initial["email"] = request.user.email
        form = SupportMessageForm(initial=initial)
    return render(request, "support/contact.html", {"form": form})


def contact_done(request):
    return render(request, "support/contact_done.html")


@super_admin_required
def message_list(request):
    return render(
        request,
        "support/message_list.html",
        {"support_messages": SupportMessage.objects.select_related("school")},
    )


@super_admin_required
def message_resolve(request, pk):
    support_message = get_object_or_404(SupportMessage, pk=pk)
    if request.method == "POST":
        support_message.status = SupportMessage.Status.RESOLVED
        support_message.save(update_fields=["status"])
        messages.success(request, "Support message marked as resolved.")
    return redirect("support:message_list")
