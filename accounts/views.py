from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static

from .forms import SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account is ready.")
            return redirect("accounts:dashboard")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")


def manifest(request):
    """Lets phones install Dropa to the home screen like an app."""
    return JsonResponse(
        {
            "name": "Dropa",
            "short_name": "Dropa",
            "description": "Food delivery inside your estate.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f5f3ee",
            "theme_color": "#1f6b4f",
            "icons": [
                {"src": static("accounts/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": static("accounts/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
        },
        content_type="application/manifest+json",
    )


SERVICE_WORKER = """
// Dropa service worker. It deliberately caches nothing: orders change by the minute.
self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (event) { event.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", function (event) {
  if (event.request.mode !== "navigate") { return; }
  event.respondWith(
    fetch(event.request).catch(function () {
      return new Response(
        "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'>" +
        "<body style='font-family:system-ui;padding:2rem'><h1>You're offline</h1>" +
        "<p>Dropa needs an internet connection. Reconnect and try again.</p>",
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      );
    })
  );
});
"""


def service_worker(request):
    return HttpResponse(SERVICE_WORKER, content_type="application/javascript")
