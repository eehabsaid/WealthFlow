"""Shell guard for the `shell` tool. One command line may chain commands (`&&`, `||`, `;`, `|`) and redirect output. The line is split into its commands and each
one goes through the same `classify` as every other command, so: git writes, nested shells (bash -c, cmd, powershell) and the project's deny list are DENIED
(never approvable); destructive/system commands, installs, network, paths outside the project and unlisted commands ASK (as the Settings > Behavior switches
say); a redirect into a file is checked like a file write (forbidden/internal = denied, protected/outside the project = ask). Pure functions."""

from __future__ import annotations

from .parsing import (  # noqa: F401
    SEPARATORS,
    SAFE,
    NULL_TARGETS,
    Parsed,
    _scan,
    _unquote,
    parse,
    _strip,
)
from .classify import (  # noqa: F401
    _redirect,
    classify_line,
    classify_safe_paths,
)

__all__ = ['SEPARATORS', 'SAFE', 'NULL_TARGETS', 'Parsed', '_scan', '_unquote', 'parse', '_strip', '_redirect', 'classify_line', 'classify_safe_paths']
