"""
Command-line runner for the sandbox studies.

A study script defines one function per analysis, marked with ``@study``, and
an optional ``setup()`` that computes the data they share::

    from runner import study, run

    def setup():
        return dict(levels=...)          # or any object; available as ``ctx``

    @study
    def trigraph(ctx, opts):
        '''Location and count of subcycle durations.'''
        ...

    @study(default=False)
    def return_plots(ctx, opts):
        ...

    if __name__ == "__main__":
        run(setup)

Each study receives ``ctx`` (what ``setup`` returned, as attributes) and
``opts``, with ``opts.save`` (write figures/sounds to files) and ``opts.show``
(display figures, play sounds). ``setup`` runs once, before the first study.

Command line::

    python study_of_x.py                 # the default studies
    python study_of_x.py name1 name2     # the given studies, in that order
    python study_of_x.py --all           # every study
    python study_of_x.py --list          # names, defaults and descriptions
    python study_of_x.py NAME --save     # also save the results
    python study_of_x.py NAME --no-show  # don't open windows or play sounds
"""

import argparse
import shlex
import sys
from types import SimpleNamespace
from typing import Callable

# Registered studies, per module: {module name: {study name: (function, default)}}
_REGISTRY: dict[str, dict[str, tuple[Callable, bool]]] = {}


def study(fn: Callable | None = None, *, default: bool = True):
    """
    Register a study function. Use as ``@study`` or ``@study(default=False)``;
    studies with ``default=False`` run only when named or with ``--all``.
    """
    def register(f: Callable) -> Callable:
        _REGISTRY.setdefault(f.__module__, {})[f.__name__] = (f, default)
        return f
    return register if fn is None else register(fn)


def _summary(f: Callable) -> str:
    doc = (f.__doc__ or '').strip()
    return doc.splitlines()[0] if doc else ''


def run(setup: Callable | None = None, argv: list[str] | None = None) -> None:
    """Parse the command line and run the selected studies of the calling script."""
    module = setup.__module__ if setup is not None else sys._getframe(1).f_globals['__name__']
    studies = _REGISTRY.get(module, {})
    defaults = [name for name, (_, default) in studies.items() if default]

    parser = argparse.ArgumentParser(
        description=(sys.modules[module].__doc__ or '').strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('names', nargs='*', metavar='STUDY',
                        help=f"studies to run (default: {', '.join(defaults) or 'none'})")
    parser.add_argument('-l', '--list', action='store_true', help='list the studies and exit')
    parser.add_argument('-a', '--all', action='store_true', help='run every study')
    parser.add_argument('-s', '--save', action='store_true', help='save figures and sounds to files')
    parser.add_argument('-n', '--no-show', action='store_true',
                        help="don't display figures or play sounds (batch runs)")
    # Split arguments that hold several words (e.g. "counts trigraph --save" typed
    # into the editor's task prompt, which arrives as a single argument)
    argv = [word for arg in (sys.argv[1:] if argv is None else argv) for word in shlex.split(arg)]
    args = parser.parse_args(argv)

    if args.list:
        width = max((len(name) for name in studies), default=0)
        for name, (f, default) in studies.items():
            print(f"{'*' if default else ' '} {name:<{width}}  {_summary(f)}")
        print("\n* = runs by default")
        return

    unknown = [name for name in args.names if name not in studies]
    if unknown:
        parser.error(f"unknown studies: {', '.join(unknown)} (choose from: {', '.join(studies)})")
    selected = args.names or (list(studies) if args.all else defaults)
    if not selected:
        parser.error("no default studies; name one or use --all (see --list)")

    if args.no_show:
        import matplotlib.pyplot as plt
        plt.switch_backend('Agg')
        plt.show = lambda *a, **k: plt.close('all')

    opts = SimpleNamespace(save=args.save, show=not args.no_show)
    ctx = None
    if setup is not None:
        ctx = setup()
        if isinstance(ctx, dict):
            ctx = SimpleNamespace(**ctx)

    for name in selected:
        print(f"== {name}", flush=True)
        studies[name][0](ctx, opts)
