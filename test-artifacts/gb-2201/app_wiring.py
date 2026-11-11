"""用最小桩验证后端应用可完整导入、所有路由正确注册（不启动服务器）。"""
import os, sys, types, tempfile
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + tmp + '/w.sqlite'
os.environ['SEED_DEMO'] = 'false'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend')))

# ---- pydantic 桩 ----
pydantic = types.ModuleType('pydantic')
class BaseModel:
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)
def Field(default=None, **kw): return default
pydantic.BaseModel = BaseModel; pydantic.Field = Field
sys.modules['pydantic'] = pydantic

# ---- fastapi 桩 ----
fastapi = types.ModuleType('fastapi')
class HTTPException(Exception):
    def __init__(self, status_code, detail): self.status_code = status_code; self.detail = detail
class Depends:  # 占位，直接透传依赖
    def __init__(self, fn=None): self.fn = fn
class APIRouter:
    def __init__(self, prefix='', tags=None): self.prefix = prefix; self.routes = []
    def _reg(self, method, path, **kw):
        def deco(fn):
            self.routes.append((method, self.prefix + path, fn.__name__)); return fn
        return deco
    def get(self, path, **kw): return self._reg('GET', path, **kw)
    def post(self, path, **kw): return self._reg('POST', path, **kw)
    def patch(self, path, **kw): return self._reg('PATCH', path, **kw)
    def delete(self, path, **kw): return self._reg('DELETE', path, **kw)
class FastAPI(APIRouter):
    def __init__(self, title='', lifespan=None):
        super().__init__(); self.title = title; self.middlewares = []
    def add_middleware(self, mw, **kw): self.middlewares.append(mw)
    def include_router(self, r): self.routes.extend(r.routes)
fastapi.FastAPI = FastAPI; fastapi.APIRouter = APIRouter
fastapi.Depends = Depends; fastapi.HTTPException = HTTPException
class Request: ...
fastapi.Request = Request
sys.modules['fastapi'] = fastapi

security_mod = types.ModuleType('fastapi.security')
class HTTPBearer:
    def __init__(self, auto_error=True): pass
security_mod.HTTPBearer = HTTPBearer
sys.modules['fastapi.security'] = security_mod
responses_mod = types.ModuleType('fastapi.responses')
class Response:
    def __init__(self, content='', media_type='', headers=None): pass
responses_mod.Response = Response
sys.modules['fastapi.responses'] = responses_mod

# ---- starlette 桩 ----
starlette = types.ModuleType('starlette')
sys.modules['starlette'] = starlette
base_mod = types.ModuleType('starlette.middleware.base')
class BaseHTTPMiddleware: ...
base_mod.BaseHTTPMiddleware = BaseHTTPMiddleware
sys.modules['starlette.middleware'] = types.ModuleType('starlette.middleware')
sys.modules['starlette.middleware.base'] = base_mod
sresp = types.ModuleType('starlette.responses')
class JSONResponse:
    def __init__(self, *a, **k): pass
sresp.JSONResponse = JSONResponse
sys.modules['starlette.responses'] = sresp

# numpy 桩（复用验收测试里的）
acc = open(os.path.join(os.path.dirname(__file__), 'ingest_acceptance.py')).read()
np_start = acc.index("np = types.ModuleType('numpy')")
np_end = acc.index('sys.modules[\'numpy\'] = np') + len("sys.modules['numpy'] = np")
g = {'types': types, 'sys': sys}
exec(acc[np_start:np_end], g)
sys.modules['numpy'] = g['np']

from src.main import app
paths = [(m, p) for m, p, _ in app.routes]
expected = [
    ('POST', '/datasets'), ('GET', '/datasets'), ('GET', '/datasets/{id}'),
    ('POST', '/datasets/{id}/ingest'), ('GET', '/datasets/{id}/batches'),
    ('PATCH', '/datasets/{id}'), ('GET', '/ingest-batches'),
    ('GET', '/runs'), ('POST', '/runs'), ('GET', '/reports'),
    ('GET', '/audit'), ('GET', '/health'),
]
missing = [e for e in expected if e not in paths]
print('已注册路由数:', len(paths))
for p in paths: print(' ', p[0], p[1])
if missing:
    print('MISSING:', missing); sys.exit(1)
print('PASS 应用导入成功，补发/批次路由全部注册，无接线错误')
