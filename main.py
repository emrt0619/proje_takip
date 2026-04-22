"""
Kule Radar — Backend (FastAPI)
Mimari: IDataAdapter (Adapter Pattern) + Atomic File Write
Endpoints: GET /api/data, POST /api/data, POST /api/upload
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
import hashlib
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ──────────────────────────────────────────────
# 1. Adapter Pattern — Soyutlama Katmanı
# ──────────────────────────────────────────────

class IDataAdapter(ABC):
    """
    Veri erişim soyutlaması.
    Faz 1: MockJSONAdapter (lokal JSON dosyası)
    Faz 2: OpenProjectAdapter (dış API) — bu arayüzü implemente edecek.
    """

    @abstractmethod
    def read(self) -> dict[str, Any]:
        """Tüm dashboard verisini döndürür."""
        ...

    @abstractmethod
    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Dashboard verisini günceller ve yeni halini döndürür."""
        ...


class MockJSONAdapter(IDataAdapter):
    """
    Lokal JSON dosyasına okuma/yazma yapan adaptör.
    Yazma işlemlerinde Atomic File Replace stratejisi uygulanır:
      1. Veri geçici bir .tmp dosyasına yazılır.
      2. os.replace() ile atomik olarak asıl dosyanın üzerine taşınır.
    Bu sayede TV frontend'in yarım yazılmış bir dosya okuması engellenir.
    """

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path).resolve()
        if not self._path.exists():
            raise FileNotFoundError(
                f"Veri dosyası bulunamadı: {self._path}"
            )

    # ── READ ──────────────────────────────────
    def read(self) -> dict[str, Any]:
        with open(self._path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ── WRITE (Atomic) ───────────────────────
    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()
        payload.setdefault("system_status", 200)

        dir_path = self._path.parent
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", prefix=".dashboard_", dir=str(dir_path)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_fh:
                json.dump(payload, tmp_fh, ensure_ascii=False, indent=2)
                tmp_fh.flush()
                os.fsync(tmp_fh.fileno())
            # Atomik yer değiştirme — POSIX'te garanti altında.
            os.replace(tmp_path, str(self._path))
        except BaseException:
            # Hata durumunda geçici dosyayı temizle.
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        return payload


# ──────────────────────────────────────────────
# 2. FastAPI Uygulaması
# ──────────────────────────────────────────────

DATA_FILE = Path(__file__).resolve().parent / "dashboard_data.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"

# Uploads klasörünü garanti et
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

adapter: IDataAdapter = MockJSONAdapter(DATA_FILE)

app = FastAPI(
    title="Kule Radar API",
    version="2.0.0",
    docs_url="/docs",
)

active_tokens: set[str] = set()

def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Yetkisiz Erişim")
    token = authorization.split(" ")[1]
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")

class LoginRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

# CORS — TV ve Admin farklı origin'lerden erişebilir.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# İzin verilen dosya uzantıları
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ── GET /api/data ─────────────────────────────
@app.get("/api/data")
async def get_data() -> JSONResponse:
    """
    TV ve Admin paneli için tüm dashboard verisini döndürür.
    TV frontend'e uyumluluk için employees'den team bilgileri çözümlenir.
    """
    try:
        data = adapter.read()
        # TV uyumluluğu: team_ids → tam team nesnelerine çözümle
        employees = {e["id"]: e for e in data.get("employees", [])}
        resolved_projects = []
        for proj in data.get("active_projects", []):
            p = dict(proj)
            team_ids = p.pop("team_ids", [])
            p["team"] = []
            for eid in team_ids:
                emp = employees.get(eid)
                if emp:
                    p["team"].append({
                        "name": emp["name"],
                        "role": emp["role"],
                        "avatar_url": emp.get("photo_url", "")
                    })
            
            inst_team_ids = p.pop("installation_team_ids", [])
            p["installation_team"] = []
            for eid in inst_team_ids:
                emp = employees.get(eid)
                if emp:
                    p["installation_team"].append({
                        "name": emp["name"],
                        "role": emp["role"],
                        "avatar_url": emp.get("photo_url", "")
                    })
                    
            resolved_projects.append(p)

        # kitchen_heroes çözümle
        resolved_heroes = []
        for hero in data.get("kitchen_heroes", []):
            emp = employees.get(hero.get("employee_id", ""))
            resolved_heroes.append({
                "name": emp["name"] if emp else hero.get("name", ""),
                "achievement": hero.get("achievement", ""),
                "avatar_url": emp.get("photo_url", "") if emp else hero.get("avatar_url", "")
            })

        output = {
            "system_status": data.get("system_status", 200),
            "last_updated": data.get("last_updated", ""),
            "employees": data.get("employees", []),
            "active_projects": resolved_projects,
            "kitchen_heroes": resolved_heroes,
            # Admin için ham veriyi de gönder
            "_raw_projects": data.get("active_projects", []),
            "_raw_heroes": data.get("kitchen_heroes", []),
        }
        return JSONResponse(content=output)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── POST /api/data ────────────────────────────
@app.post("/api/data", dependencies=[Depends(verify_token)])
async def post_data(request: Request) -> JSONResponse:
    """
    Admin panelinden gelen veriyi atomik olarak JSON dosyasına yazar.
    Body: Tam dashboard JSON payload'ı.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz JSON gövdesi.")

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload bir JSON nesnesi olmalıdır."
        )

    try:
        # Mevcut veriyi oku ve admin_hash değerini koru
        current_data = adapter.read()
        if "admin_hash" in current_data:
            payload["admin_hash"] = current_data["admin_hash"]

        updated = adapter.write(payload)
        return JSONResponse(content={"ok": True, "data": updated})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── POST /api/upload ──────────────────────────
@app.post("/api/upload", dependencies=[Depends(verify_token)])
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """
    Personel fotoğrafı yükleme endpoint'i.
    Dosyayı atomik olarak /static/uploads/ klasörüne kaydeder.
    Strateji:
      1. Dosya geçici bir .tmp yoluna yazılır.
      2. os.replace() ile atomik olarak hedef konuma taşınır.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı boş olamaz.")

    # Uzantı kontrolü
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dosya formatı: {ext}. İzin verilenler: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Dosya boyutu kontrolü
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Dosya boyutu {MAX_FILE_SIZE // (1024*1024)}MB limitini aşıyor."
        )

    # Benzersiz dosya adı oluştur
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    target_path = UPLOAD_DIR / unique_name

    # Atomik yazma: önce .tmp dosyasına, sonra os.replace()
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp", prefix=".upload_", dir=str(UPLOAD_DIR)
    )
    try:
        with os.fdopen(fd, "wb") as tmp_fh:
            tmp_fh.write(content)
            tmp_fh.flush()
            os.fsync(tmp_fh.fileno())
        os.replace(tmp_path, str(target_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail="Dosya yazma hatası.")

    # Statik URL'yi döndür
    file_url = f"/static/uploads/{unique_name}"
    return JSONResponse(content={"ok": True, "url": file_url, "filename": unique_name})


# ── POST /api/login ───────────────────────────
@app.post("/api/login")
async def login(req: LoginRequest) -> JSONResponse:
    """Admin girişi yapar ve token döner."""
    data = adapter.read()
    admin_hash_str = data.get("admin_hash")
    if not admin_hash_str:
        raise HTTPException(status_code=500, detail="Admin parolası ayarlanmamış.")
    
    parts = admin_hash_str.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Admin parolası formatı geçersiz.")
    salt, stored_hash = parts

    computed = hashlib.sha256((req.password + salt).encode("utf-8")).hexdigest()
    if computed != stored_hash:
        raise HTTPException(status_code=401, detail="Hatalı parola")
    
    token = secrets.token_hex(32)
    active_tokens.add(token)
    return JSONResponse(content={"ok": True, "token": token})


# ── POST /api/change-password ──────────────────
@app.post("/api/change-password", dependencies=[Depends(verify_token)])
async def change_password(req: ChangePasswordRequest) -> JSONResponse:
    """Mevcut parolayı doğrular ve yenisiyle değiştirir."""
    data = adapter.read()
    admin_hash_str = data.get("admin_hash", ":")
    salt, stored_hash = admin_hash_str.split(":", 1)

    computed = hashlib.sha256((req.old_password + salt).encode("utf-8")).hexdigest()
    if computed != stored_hash:
        raise HTTPException(status_code=400, detail="Eski parola hatalı")
    
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Yeni parola çok kısa")

    new_salt = secrets.token_hex(8)
    new_hash = hashlib.sha256((req.new_password + new_salt).encode("utf-8")).hexdigest()
    
    data["admin_hash"] = f"{new_salt}:{new_hash}"
    try:
        adapter.write(data)
        return JSONResponse(content={"ok": True})
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Şifre güncellenirken hata oluştu.")


# ── Statik Dosya Sunucu ──────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


# ── Kök yol yönlendirmesi ────────────────────
@app.get("/")
async def root():
    """Ana sayfaya yönlendir."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    import os

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", 8000))
    except ValueError:
        port = 8000

    # Üretim (production) ortamında reload kapalı olmalıdır
    env = os.getenv("ENV", "development").lower()
    is_reload = (env != "production")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=is_reload,
        log_level="info",
    )
