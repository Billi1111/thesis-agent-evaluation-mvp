param(
    [ValidateSet('qwen3_14b','gpt_oss_20b')][string]$Model='qwen3_14b',
    [string]$LlamaRoot='C:\Users\bilal\Documents\ChatGPT\llama.cpp',
    [string]$QwenPath='C:\Users\bilal\Desktop\Local Models\Qwen3-14B-Q4_K_M.gguf',
    [switch]$Stop
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$runtimeDir=Join-Path $projectRoot 'experiments\runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$pidPath=Join-Path $runtimeDir 'benchmark-server.pid'
$serverExe=Join-Path $LlamaRoot 'bin\llama-server.exe'
# Stop only a process launched by this benchmark with its dedicated port.
if(Test-Path -LiteralPath $pidPath){
    $savedId=[int](Get-Content -LiteralPath $pidPath -Raw).Trim()
    $candidate=Get-CimInstance Win32_Process -Filter "ProcessId=$savedId" -ErrorAction SilentlyContinue
    if($candidate -and $candidate.ExecutablePath -eq $serverExe -and $candidate.CommandLine -match '--port 8091'){
        Stop-Process -Id $savedId
        Wait-Process -Id $savedId -Timeout 30 -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } elseif($candidate){ throw 'Saved PID belongs to another process; refusing to stop it.' }
    Remove-Item -LiteralPath $pidPath
}
if($Stop){ Write-Output 'Benchmark server stopped; normal chat launchers are unchanged.'; exit 0 }
try {
    $socket=New-Object System.Net.Sockets.TcpClient
    $connect=$socket.ConnectAsync('127.0.0.1',8091)
    try { [void]$connect.Wait(500) } catch {}
    if($socket.Connected){ throw 'Port 8091 is in use; stop its owner before running the benchmark.' }
} finally { $socket.Dispose() }
$modelPath=if($Model -eq 'qwen3_14b'){$QwenPath}else{Join-Path $LlamaRoot 'models\gpt-oss-20b-UD-Q4_K_XL.gguf'}
$alias=if($Model -eq 'qwen3_14b'){'qwen3-14b'}else{'gpt-oss-20b'}
if(-not(Test-Path -LiteralPath $modelPath)){ throw "Missing model: $modelPath" }
$serverArgs=@('-m',('"'+$modelPath+'"'),'--alias',$alias,
    '--fit','on','--fit-target','2048','--load-mode','none',
    '-c','8192','-b','512','-ub','128','-fa','on','--jinja','-np','1','-t','8',
    '--temp','0','--top-p','1','--top-k','0','--min-p','0','--seed','42',
    '--reasoning-effort','low','--reasoning-budget','256',
    '--host','127.0.0.1','--port','8091')
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$proc=Start-Process -FilePath $serverExe -ArgumentList $serverArgs -WorkingDirectory $LlamaRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir "$Model-$stamp.stdout.log") -RedirectStandardError (Join-Path $runtimeDir "$Model-$stamp.stderr.log") -PassThru
Set-Content -LiteralPath $pidPath -Value $proc.Id
$metadata=@{model=$Model;alias=$alias;path=$modelPath;size_bytes=(Get-Item -LiteralPath $modelPath).Length;sha256=(Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash;server_version=(& $serverExe --version 2>&1 | Out-String);arguments=$serverArgs;port=8091;started_at=(Get-Date -Format o)}
$metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runtimeDir "$Model.json") -Encoding utf8
Write-Output "Loading $alias on benchmark port 8091..."
$deadline=[DateTime]::UtcNow.AddMinutes(10)
while([DateTime]::UtcNow -lt $deadline){
    $proc.Refresh()
    if($proc.HasExited){ throw 'llama-server exited; inspect experiments/runtime logs.' }
    try {
        $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8091/health' -TimeoutSec 2
        if($health.status -eq 'ok'){ Write-Output "$alias ready at http://127.0.0.1:8091"; exit 0 }
    } catch {}
    Start-Sleep -Seconds 2
}
throw 'Model load timed out.'
