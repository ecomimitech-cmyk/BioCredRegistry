# Follow-up on the four probes that came back readable: what exactly does a
# stranger get, and does any of it belong to a profile nobody approved?

$ErrorActionPreference = "Stop"
$base = "https://wmwzqnzyhiyhfzncuxkc.supabase.co"
$anon = "sb_publishable_sWwmE6Hyd_qZAmdHjgWLBg_ZQJAI1ks"
$H = @{ apikey = $anon; Authorization = "Bearer $anon" }
function G { param($p) Invoke-RestMethod -Uri "$base/rest/v1/$p" -Headers $H -Method GET }

Write-Host "=== biologist_profile, as anon sees it ==="
G "biologist_profile?select=registry_id,full_name,verification_status,visibility_status" |
    Format-Table -AutoSize

Write-Host "=== credential_record: status and whether a document path comes with it ==="
$creds = G "credential_record?select=profile_id,title,verification_status,documentation_url"
$creds | Group-Object verification_status | Select-Object Name, Count | Format-Table -AutoSize
Write-Host "rows carrying a document path: $((@($creds | Where-Object { $_.documentation_url })).Count) of $($creds.Count)"
Write-Host "sample paths:"
@($creds | Where-Object { $_.documentation_url } | Select-Object -First 5) |
    ForEach-Object { Write-Host "   $($_.documentation_url)" }

Write-Host ""
Write-Host "=== experience_evidence by status ==="
$ev = G "experience_evidence?select=profile_id,verification_status,species_or_system"
$ev | Group-Object verification_status | Select-Object Name, Count | Format-Table -AutoSize

Write-Host "=== do any readable child rows belong to a profile that is NOT publicly listed? ==="
$publicIds = (G "profile_public_v1?select=id").id
$allProfiles = G "biologist_profile?select=id,registry_id,verification_status"
$hiddenIds = @($allProfiles | Where-Object { $publicIds -notcontains $_.id })
Write-Host "profiles readable but not public: $($hiddenIds.Count)"
$hiddenIds | Format-Table registry_id, verification_status -AutoSize

$leakCreds = @($creds | Where-Object { $hiddenIds.id -contains $_.profile_id })
$leakEv    = @($ev    | Where-Object { $hiddenIds.id -contains $_.profile_id })
Write-Host "credential rows belonging to a non-public profile: $($leakCreds.Count)"
Write-Host "evidence rows belonging to a non-public profile:   $($leakEv.Count)"

Write-Host ""
Write-Host "=== render_payload_cache, as anon sees it ==="
$cache = G "render_payload_cache?select=profile_id,created_at"
Write-Host "rows: $($cache.Count)"
$cacheLeak = @($cache | Where-Object { $publicIds -notcontains $_.profile_id })
Write-Host "cached payloads for a non-public profile: $($cacheLeak.Count)"
