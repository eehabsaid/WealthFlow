$dualGpuVars = @{
    "OLLAMA_VULKAN"                = "1"
    "OLLAMA_IGPU_ENABLE"           = "1"
    "GGML_VK_VISIBLE_DEVICES"      = "0,1"
    "OLLAMA_FLASH_ATTENTION"       = "1"
    "OLLAMA_KV_CACHE_TYPE"         = "q4_0"
    "OLLAMA_KEEP_ALIVE"            = "30m"
    "OLLAMA_MODELS"                = "D:\Ollama\Models"
    "OLLAMA_NUM_PARALLEL"          = "2"
    "OLLAMA_MAX_LOADED_MODELS"     = "2"
    "HF_HUB_DISABLE_TELEMETRY"     = "1"
    "OFFLINE_MODE"                 = "true"
    "OLLAMA_SCHED_SPREAD"          = "1"
    "OLLAMA_LOAD_TIMEOUT"          = "60m"
    "OLLAMA_MAX_TRANSFER_STREAMS"  = "1"
    "OLLAMA_LLM_LIBRARY"           = "cuda_v13"
}

# Clear old CUDA variable from both User and Machine scopes first
#[Environment]::SetEnvironmentVariable("OLLAMA_LLM_LIBRARY", $null, [System.EnvironmentVariableTarget]::User)
#[Environment]::SetEnvironmentVariable("OLLAMA_LLM_LIBRARY", $null, [System.EnvironmentVariableTarget]::Machine)

foreach ($key in $dualGpuVars.Keys) {
    # 1. Apply to User Environment
    [Environment]::SetEnvironmentVariable($key, $dualGpuVars[$key], [System.EnvironmentVariableTarget]::User)
    
    # 2. Apply to System (Machine) Environment (Global for all accounts)
    [Environment]::SetEnvironmentVariable($key, $dualGpuVars[$key], [System.EnvironmentVariableTarget]::Machine)
    
    # 3. Update current active PowerShell session
    Set-Item "Env:\$key" $dualGpuVars[$key]
}

Write-Host "Variables successfully applied to User, Machine, and Session scopes!" -ForegroundColor Green