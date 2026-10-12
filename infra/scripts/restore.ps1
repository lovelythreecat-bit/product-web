[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Manifest,
    [Parameter(Mandatory)][string]$Target,
    [Parameter(Mandatory)][string]$ManifestSha256,
    [Parameter(Mandatory)][string]$OwnedRoot,
    [Parameter(Mandatory)][guid]$Owner,
    [Parameter(Mandatory)][string]$Proof,
    [Parameter(Mandatory)][string]$MySql,
    [Parameter(Mandatory)][string]$DefaultsFile,
    [Parameter(Mandatory)][string]$Python
)
$ErrorActionPreference = 'Stop'
if (-not [IO.Path]::IsPathFullyQualified($Python)) { throw 'Absolute Python path required' }
& $Python (Join-Path $PSScriptRoot 'backup_restore.py') restore `
    --manifest $Manifest --target $Target --manifest-sha256 $ManifestSha256 `
    --owned-root $OwnedRoot --owner $Owner.ToString() --proof $Proof `
    --client $MySql --defaults-file $DefaultsFile
if ($LASTEXITCODE -ne 0) { throw 'Restore failed or refused; leave target isolated for diagnosis' }
