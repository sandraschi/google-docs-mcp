@{
    Name         = 'google-docs-mcp'
    BackendPort  = 11972
    FrontendPort = 11973
    HealthPath   = '/api/health'
    WebRoot      = 'webapp'

    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'google_docs_mcp.backend.app:app'
        SyncExtras    = @('dev')
    }

    Frontend = @{
        Kind           = 'vite-bun'
        PackageManager = 'bun'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
