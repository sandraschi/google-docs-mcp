# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Tauri-embedded backend.
#
# strip=False, upx=False (mandatory — strip/upx corrupt the PKG on Windows).
# noarchive=True (mandatory — PYZ importer is unreliable in onefile mode for
# stdlib modules loaded from disk-extracted datas).
#
# Repo-specific SKIP list customization: the generic fleet template excludes
# 'google' as a binary-size optimization for repos that accidentally pull in
# google-cloud-* transitively. This repo's entire purpose IS the Google APIs
# (google-api-python-client, google-auth, google-auth-oauthlib) — excluding
# 'google' here would silently produce a broken backend that cannot import
# its own core dependency. Do not copy this SKIP list back into the generic
# template without this repo's exclusion removed for other repos.
a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    datas=[
        ("src/google_docs_mcp", "google_docs_mcp"),
        ("assets", "assets"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "googleapiclient.discovery_cache",
        "google.auth.transport.requests",
        "google_auth_oauthlib.flow",
    ],
    # 'unittest' deliberately NOT excluded: httplib2 -> pyparsing.testing imports it at
    # import time (transitive via googleapiclient); excluding it breaks the frozen build
    # with "ModuleNotFoundError: No module named 'unittest'". Found by smoke-testing the
    # actual frozen exe, not by static analysis.
    excludes=["tkinter", "setuptools", "pip", "wheel", "_distutils_hack"],
    noarchive=True,
)

# Strip .dist-info but preserve metadata for packages that read their own
# version at import time (fastmcp, prefab_ui, pydantic all call
# importlib.metadata.version()).
_keep_dist = ["fastmcp-", "mcp-", "prefab_ui-", "opentelemetry-", "email_validator-", "google_api_python_client-"]
_saved = [
    e for e in a.datas
    if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and ".dist-info" in str(e[0])
]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and ".dist-info" in str(e[0]))]
a.datas.extend(_saved)

# NOTE: 'google' deliberately NOT in this SKIP list — see header comment.
SKIP = [
    "torch", "playwright", "bitsandbytes", "llvmlite", "pyarrow", "pymupdf",
    "grpc", "numba", "Cython", "azure", "boto3", "botocore", "matplotlib",
    "PIL", "pandas", "scipy", "sklearn", "onnxruntime",
]
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name="google-docs-mcp-backend",
    debug=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
