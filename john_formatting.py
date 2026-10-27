"""John's experimental layout. Changes here never run for Metro standard.

Start identical to Metro. Put John's requested document formatting changes in
apply(), using only the supplied document (never change shared module globals).
The same hook is used by preview, Word builds and PDF builds.
"""


def apply(document):
    """Apply John's experiments to this document only."""
    return document
