param([string]$Output='experiments/results/reproduction', [switch]$SmokeOnly, [switch]$Resume,
      [ValidateSet('qwen3_14b','gpt_oss_20b')][string[]]$Models=@('qwen3_14b','gpt_oss_20b'))
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $python=Join-Path $projectRoot '.venv\Scripts\python.exe'
    if(-not(Test-Path -LiteralPath $python)){ throw 'Create .venv and install requirements.txt first; see README.md.' }
    & $python -m evaluation.runner validate
    if($LASTEXITCODE -ne 0){ throw 'Dataset validation failed.' }
    foreach($model in $Models){
        & (Join-Path $PSScriptRoot 'Start-Benchmark-Model.ps1') -Model $model
        if($LASTEXITCODE -ne 0){ throw "Could not start $model" }
        $runOutput=Join-Path $Output $model
        $runArgs=@('-m','evaluation.runner','run','--models',$model,'--output',$runOutput)
        if($SmokeOnly){ $runArgs+=@('--ids','TICKET_001','TICKET_031','TICKET_096') }
        if($Resume){ $runArgs+='--resume' }
        & $python @runArgs
        if($LASTEXITCODE -ne 0){ throw "$model execution failed" }
    }
    & $python -m analysis.analyze_results (Join-Path $Output 'qwen3_14b') (Join-Path $Output 'gpt_oss_20b') --output (Join-Path $Output 'analysis')
    if($LASTEXITCODE -ne 0){ throw 'Analysis failed.' }
} finally {
    & (Join-Path $PSScriptRoot 'Start-Benchmark-Model.ps1') -Stop
    Pop-Location
}
