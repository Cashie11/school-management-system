from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse


def _destination(url, args=None):
    return reverse(url, args=args) if args else url


def form_view(
    request,
    *,
    form_class,
    template,
    title,
    success_url,
    success_url_args=None,
    instance=None,
    save_message="Saved.",
    extra=None,
    form_kwargs=None,
    initial=None,
    on_save=None,
):
    """Create or edit a tenant record with a ModelForm.

    The form must not expose ``school``; the model fills it from the active
    tenant context on save. ``on_save`` receives the saved instance, for example
    to send a notification.
    """
    form = form_class(
        request.POST or None, instance=instance, initial=initial or {}, **(form_kwargs or {})
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        if on_save is not None:
            on_save(obj)
        messages.success(request, save_message)
        return redirect(_destination(success_url, success_url_args))

    context = {"form": form, "title": title, "instance": instance}
    if extra:
        context.update(extra)
    return render(request, template, context)


def delete_view(
    request,
    *,
    obj,
    template,
    success_url,
    success_url_args=None,
    success_message="Deleted.",
    extra=None,
):
    if request.method == "POST":
        obj.delete()
        messages.success(request, success_message)
        return redirect(_destination(success_url, success_url_args))

    context = {"object": obj}
    if extra:
        context.update(extra)
    return render(request, template, context)
