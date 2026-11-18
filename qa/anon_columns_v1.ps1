$ErrorActionPreference = "Stop"
$base = "https://wmwzqnzyhiyhfzncuxkc.supabase.co"
$anon = "sb_publishable_sWwmE6Hyd_qZAmdHjgWLBg_ZQJAI1ks"
$H = @{ apikey = $anon; Authorization = "Bearer $anon" }

function G {
    param($path)
    Invoke-RestMethod -Uri ("{0}/rest/v1/{1}" -f $base, $path) -Headers $H -Method GET
}

$qCache = 'render_payload_cache?select=*' + [char]38 + 'limit=2'
$qCred  = 'credential_public_v1?select=*' + [char]38 + 'limit=1'

Write-Host "render_payload_cache - columns anon can read:"
$c = G $qCache
$c[0].PSObject.Properties.Name | ForEach-Object { Write-Host "  $_" }

$publicIds = (G 'profile_public_v1?select=id').id
$all = G 'render_payload_cache?select=profile_id'
$leak = @($all | Where-Object { $publicIds -notcontains $_.profile_id })
Write-Host ("  cached rows: {0}; belonging to a non-public profile: {1}" -f $all.Count, $leak.Count)

Write-Host ""
Write-Host "credential_public_v1 - columns anon can read:"
$k = G $qCred
$k[0].PSObject.Properties.Name | ForEach-Object { Write-Host "  $_" }
