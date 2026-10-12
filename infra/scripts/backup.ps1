[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Destination,
    [Parameter(Mandatory)][string]$Manifest,
    [Parameter(Mandatory)][string]$StorageRoot,
    [Parameter(Mandatory)][string]$ReleaseRoot,
    [Parameter(Mandatory)][string]$OwnedRoot,
    [Parameter(Mandatory)][guid]$Owner,
    [Parameter(Mandatory)][string]$Proof,
    [Parameter(Mandatory)][string]$MySqlDump,
    [Parameter(Mandatory)][string]$DefaultsFile,
    [Parameter(Mandatory)][string]$Python
)
$ErrorActionPreference = 'Stop'
if (-not [IO.Path]::IsPathFullyQualified($Python)) { throw 'Absolute Python path required' }
& $Python (Join-Path $PSScriptRoot 'backup_restore.py') backup `
    --destination $Destination --manifest $Manifest --storage-root $StorageRoot `
    --release-root $ReleaseRoot --owned-root $OwnedRoot --owner $Owner.ToString() `
    --proof $Proof --client $MySqlDump --defaults-file $DefaultsFile
if ($LASTEXITCODE -ne 0) { throw 'Backup failed or refused; no complete manifest published' }
