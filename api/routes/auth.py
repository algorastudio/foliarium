"""api/routes/auth.py — Login e logout."""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import create_session, delete_session
from api.deps import DB_NON_DISPONIBILE, get_db, get_current_session
from catasto_exceptions import DBMError

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str
    nome_completo: str
    ruolo: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db=Depends(get_db)):
    try:
        creds = db.get_user_credentials(req.username)
    except DBMError:
        # Database giu' o query fallita: non e' un problema di credenziali.
        # Il dettaglio tecnico e' gia' nel log del layer DB.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=DB_NON_DISPONIBILE,
        )
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    pwd_hash = creds.get("password_hash", "")
    try:
        ok = bcrypt.checkpw(req.password.encode(), pwd_hash.encode())
    except Exception:
        ok = False

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")

    if not creds.get("attivo", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabilitato")

    token = create_session(creds["id"], creds["username"], creds["ruolo"])
    return LoginResponse(
        token=token,
        user_id=creds["id"],
        username=creds["username"],
        nome_completo=creds.get("nome_completo", creds["username"]),
        ruolo=creds["ruolo"],
    )


@router.post("/logout")
def logout(session: dict = Depends(get_current_session)):
    delete_session(session.get("_token", ""))
    return {"ok": True}


@router.get("/me")
def me(session: dict = Depends(get_current_session)):
    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "ruolo": session["ruolo"],
    }
