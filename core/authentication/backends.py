"""Auth backends."""

from axes.backends import AxesStandaloneBackend


class RequestOptionalAxesBackend(AxesStandaloneBackend):
    """django-axes backend that steps aside when there is no HTTP request.

    Rate limiting only makes sense for real login attempts. Calls without a
    request (Django test client's login(), management commands, shell) cannot
    be tracked by IP and would otherwise raise; they fall through to the
    regular ModelBackend instead.
    """

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        if request is None:
            return None
        return super().authenticate(request, username=username, password=password, **kwargs)
