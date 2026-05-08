# shim: mantenuto per backward compatibility — rimosso in fase cleanup
import sys as _sys
from foliarium.core.services import email as _real
_sys.modules[__name__] = _real
